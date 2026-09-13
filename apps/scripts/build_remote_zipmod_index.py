#!/usr/bin/env python3
"""Build a standalone remote ZIPMOD index without downloading ZIPMOD files.

The scanner only reads:

* directory listing HTML pages;
* ZIP end-of-central-directory data and the central directory via HTTP Range;
* the local ZIP entry header and compressed bytes for ``manifest.xml``.

It never falls back to a full-file GET when a server does not support Range.
The resulting SQLite file is independent from Star Manager's application
database and can be queried by GUID with ``--query-guid``.
"""

from __future__ import annotations

import argparse
import html.parser
import posixpath
import re
import sqlite3
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET


DEFAULT_SOURCE_URL = "https://sideload.betterrepack.com/download/AISHS2/"
DEFAULT_OUTPUT = "remote_zipmod_index.sqlite"
DEFAULT_TAIL_BYTES = 65_557
DEFAULT_MAX_CENTRAL_DIRECTORY = 64 * 1024 * 1024
DEFAULT_MAX_MANIFEST_COMPRESSED = 8 * 1024 * 1024
DEFAULT_MAX_MANIFEST_UNCOMPRESSED = 16 * 1024 * 1024
DEFAULT_MAX_DIRECTORY_BYTES = 8 * 1024 * 1024
USER_AGENT = "Star-Manager-remote-index/1.0"

EOCD_SIGNATURE = b"PK\x05\x06"
ZIP64_EOCD_SIGNATURE = b"PK\x06\x06"
ZIP64_LOCATOR_SIGNATURE = b"PK\x06\x07"
CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
LOCAL_FILE_SIGNATURE = b"PK\x03\x04"


class RemoteReadError(RuntimeError):
    """An HTTP or remote ZIP read failed without downloading a full archive."""


class RangeUnsupportedError(RemoteReadError):
    """The origin returned a normal response instead of HTTP 206."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, path, parsed.query, "")
    )


def directory_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(clean_url(url))
    path = parsed.path or "/"
    if not path.endswith("/"):
        path += "/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, path, "", "")
    )


def parse_content_range(value: str) -> tuple[int, int, int | None] | None:
    match = re.fullmatch(r"\s*bytes\s+(\d+)-(\d+)/(\d+|\*)\s*", value or "")
    if not match:
        return None
    total = None if match.group(3) == "*" else int(match.group(3))
    return int(match.group(1)), int(match.group(2)), total


def parse_content_length(headers) -> int | None:
    raw = headers.get("Content-Length")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class HttpClient:
    def __init__(self, timeout: float, retries: int, allowed_url) -> None:
        self.timeout = timeout
        self.retries = max(0, retries)
        self.allowed_url = allowed_url
        self.opener = urllib.request.build_opener(NoRedirectHandler())

    def _request(
        self,
        url: str,
        method: str,
        headers: dict[str, str] | None = None,
        read_limit: int | None = None,
    ) -> tuple[bytes, object]:
        current = clean_url(url)
        request_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        request_headers.update(headers or {})
        for redirect_count in range(4):
            if not self.allowed_url(current):
                raise RemoteReadError(f"redirect escaped allowed source: {current}")
            request = urllib.request.Request(
                current, headers=request_headers, method=method
            )
            for attempt in range(self.retries + 1):
                try:
                    response = self.opener.open(request, timeout=self.timeout)
                    status = int(getattr(response, "status", 200) or 200)
                    if status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        response.close()
                        if not location:
                            raise RemoteReadError(f"redirect without Location: {current}")
                        current = clean_url(urllib.parse.urljoin(current, location))
                        break
                    if read_limit is None:
                        body = response.read()
                    elif read_limit == 0:
                        body = b""
                    else:
                        body = response.read(read_limit)
                    return body, response
                except urllib.error.HTTPError as error:
                    if error.code in {301, 302, 303, 307, 308}:
                        location = error.headers.get("Location")
                        error.close()
                        if not location:
                            raise RemoteReadError(
                                f"redirect without Location: {current}"
                            ) from error
                        current = clean_url(urllib.parse.urljoin(current, location))
                        break
                    if error.code in {408, 425, 429} or error.code >= 500:
                        if attempt < self.retries:
                            time.sleep(0.25 * (attempt + 1))
                            continue
                    raise RemoteReadError(f"HTTP {error.code} for {current}") from error
                except (OSError, urllib.error.URLError, TimeoutError) as error:
                    if attempt < self.retries:
                        time.sleep(0.25 * (attempt + 1))
                        continue
                    raise RemoteReadError(f"request failed for {current}: {error}") from error
            else:
                raise RemoteReadError(f"request failed for {current}")
            continue
        raise RemoteReadError(f"too many redirects for {url}")

    def head(self, url: str) -> dict[str, str | int]:
        try:
            _body, response = self._request(url, "HEAD", read_limit=0)
        except RemoteReadError:
            return {}
        try:
            return {
                "file_size": parse_content_length(response.headers),
                "last_modified": response.headers.get("Last-Modified", ""),
                "etag": response.headers.get("ETag", ""),
            }
        finally:
            response.close()

    def range_bytes(self, url: str, start: int | None, end: int | None) -> tuple[bytes, object]:
        if start is None and end is None:
            raise ValueError("a range must have a start or end")
        if start is None:
            range_value = f"bytes=-{end}"
        else:
            range_value = f"bytes={start}-{'' if end is None else end}"
        body, response = self._request(
            url,
            "GET",
            headers={"Range": range_value},
            read_limit=(
                end - start + 1
                if start is not None and end is not None
                else end
            ),
        )
        status = int(getattr(response, "status", 200) or 200)
        if status != 206:
            response.close()
            raise RangeUnsupportedError(
                f"server returned HTTP {status} for {range_value}; full download refused"
            )
        return body, response


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def _record(self, attrs) -> None:
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value.strip())

    def handle_starttag(self, tag: str, attrs) -> None:
        self._record(attrs)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self._record(attrs)


class DirectoryCrawler:
    def __init__(
        self,
        client: HttpClient,
        root_url: str,
        max_depth: int,
        max_files: int,
        directory_bytes: int,
    ) -> None:
        self.client = client
        self.root_url = directory_url(root_url)
        self.root = urllib.parse.urlsplit(self.root_url)
        self.max_depth = max_depth
        self.max_files = max_files
        self.directory_bytes = directory_bytes
        self.had_errors = False
        self.truncated = False

    def allowed(self, url: str) -> bool:
        parsed = urllib.parse.urlsplit(clean_url(url))
        if parsed.scheme not in {"https", "http"}:
            return False
        if parsed.netloc.lower() != self.root.netloc.lower():
            return False
        root_path = self.root.path.rstrip("/") + "/"
        return parsed.path == root_path[:-1] or parsed.path.startswith(root_path)

    def canonical_child(self, base: str, href: str) -> str | None:
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            return None
        candidate = clean_url(urllib.parse.urljoin(base, href))
        return candidate if self.allowed(candidate) else None

    def crawl(self) -> tuple[list[str], list[str]]:
        pending = deque([(self.root_url, 0)])
        visited: set[str] = set()
        directories: list[str] = []
        files: set[str] = set()
        while pending:
            current, depth = pending.popleft()
            current = directory_url(current)
            if current in visited or depth > self.max_depth:
                continue
            visited.add(current)
            directories.append(current)
            print(f"[directory {len(directories)}] {current}", flush=True)
            try:
                body, response = self.client._request(
                    current, "GET", read_limit=self.directory_bytes
                )
                response.close()
                parser = LinkParser()
                parser.feed(body.decode("utf-8", errors="replace"))
            except (RemoteReadError, UnicodeError) as error:
                self.had_errors = True
                print(f"  directory error: {error}", file=sys.stderr, flush=True)
                continue
            for href in parser.hrefs:
                child = self.canonical_child(current, href)
                if not child:
                    continue
                path = urllib.parse.urlsplit(child).path
                if path.endswith("/"):
                    if depth < self.max_depth:
                        pending.append((child, depth + 1))
                elif path.lower().endswith(".zipmod"):
                    files.add(child)
                    if self.max_files and len(files) >= self.max_files:
                        self.truncated = True
                        return directories, sorted(files)
        return directories, sorted(files)


@dataclass(frozen=True)
class CentralEntry:
    name: str
    flags: int
    compression: int
    compressed_size: int
    uncompressed_size: int
    local_offset: int
    encrypted: bool


@dataclass(frozen=True)
class Manifest:
    guid: str
    name: str
    version: str
    author: str
    status: str
    error: str


def find_last(data: bytes, signature: bytes) -> int:
    position = data.rfind(signature)
    if position < 0:
        raise RemoteReadError(f"ZIP signature not found: {signature!r}")
    return position


def parse_zip64_extra(
    extra: bytes,
    compressed_size: int,
    uncompressed_size: int,
    local_offset: int,
) -> tuple[int, int, int]:
    position = 0
    while position + 4 <= len(extra):
        field_id, field_size = struct.unpack_from("<HH", extra, position)
        value_start = position + 4
        value_end = value_start + field_size
        if value_end > len(extra):
            break
        if field_id == 0x0001:
            cursor = value_start
            if uncompressed_size == 0xFFFFFFFF:
                if cursor + 8 > value_end:
                    raise RemoteReadError("truncated ZIP64 uncompressed size")
                uncompressed_size = struct.unpack_from("<Q", extra, cursor)[0]
                cursor += 8
            if compressed_size == 0xFFFFFFFF:
                if cursor + 8 > value_end:
                    raise RemoteReadError("truncated ZIP64 compressed size")
                compressed_size = struct.unpack_from("<Q", extra, cursor)[0]
                cursor += 8
            if local_offset == 0xFFFFFFFF:
                if cursor + 8 > value_end:
                    raise RemoteReadError("truncated ZIP64 local offset")
                local_offset = struct.unpack_from("<Q", extra, cursor)[0]
            break
        position = value_end
    return compressed_size, uncompressed_size, local_offset


def parse_eocd(tail: bytes, read_range, file_size: int | None) -> tuple[int, int, int]:
    position = find_last(tail, EOCD_SIGNATURE)
    if position + 22 > len(tail):
        raise RemoteReadError("truncated ZIP end record")
    (
        _signature,
        _disk,
        _central_disk,
        entries_on_disk,
        entries_total,
        central_size,
        central_offset,
        comment_size,
    ) = struct.unpack_from("<4s4H2IH", tail, position)
    if position + 22 + comment_size > len(tail):
        raise RemoteReadError("ZIP comment extends beyond the requested tail")
    if (
        entries_on_disk != 0xFFFF
        and entries_total != 0xFFFF
        and central_size != 0xFFFFFFFF
        and central_offset != 0xFFFFFFFF
    ):
        return central_offset, central_size, entries_total

    locator_position = tail.rfind(ZIP64_LOCATOR_SIGNATURE, 0, position)
    if locator_position < 0 or locator_position + 20 > len(tail):
        raise RemoteReadError("ZIP64 locator not found")
    _signature, _disk_with_record, zip64_offset, _disk_count = struct.unpack_from(
        "<4sIQI", tail, locator_position
    )
    if file_size is not None and zip64_offset + 56 > file_size:
        raise RemoteReadError("ZIP64 end record is outside the remote file")
    record = read_range(zip64_offset, zip64_offset + 55)
    if len(record) < 56 or record[:4] != ZIP64_EOCD_SIGNATURE:
        raise RemoteReadError("invalid ZIP64 end record")
    record_size = struct.unpack_from("<Q", record, 4)[0]
    if record_size < 44 or record_size > 1024 * 1024:
        raise RemoteReadError("invalid ZIP64 end record size")
    entries_total = struct.unpack_from("<Q", record, 32)[0]
    central_size = struct.unpack_from("<Q", record, 40)[0]
    central_offset = struct.unpack_from("<Q", record, 48)[0]
    return central_offset, central_size, entries_total


def decode_zip_name(raw: bytes, flags: int) -> str:
    encoding = "utf-8" if flags & 0x800 else "cp437"
    return raw.decode(encoding, errors="replace")


def parse_central_directory(data: bytes, expected_entries: int) -> list[CentralEntry]:
    entries: list[CentralEntry] = []
    position = 0
    while position + 46 <= len(data) and (
        expected_entries == 0 or len(entries) < expected_entries
    ):
        if data[position : position + 4] != CENTRAL_DIRECTORY_SIGNATURE:
            if not entries:
                raise RemoteReadError("central directory signature not found")
            break
        (
            _signature,
            _made_by,
            _needed,
            flags,
            compression,
            _modified_time,
            _modified_date,
            _crc,
            compressed_size,
            uncompressed_size,
            name_length,
            extra_length,
            comment_length,
            _disk_start,
            _internal_attributes,
            _external_attributes,
            local_offset,
        ) = struct.unpack_from("<4s6H3I5H2I", data, position)
        end = position + 46 + name_length + extra_length + comment_length
        if end > len(data):
            raise RemoteReadError("truncated central directory entry")
        name_start = position + 46
        name = decode_zip_name(data[name_start : name_start + name_length], flags)
        extra_start = name_start + name_length
        extra = data[extra_start : extra_start + extra_length]
        compressed_size, uncompressed_size, local_offset = parse_zip64_extra(
            extra, compressed_size, uncompressed_size, local_offset
        )
        entries.append(
            CentralEntry(
                name=name,
                flags=flags,
                compression=compression,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                local_offset=local_offset,
                encrypted=bool(flags & 1),
            )
        )
        position = end
    if expected_entries and len(entries) != expected_entries:
        raise RemoteReadError(
            f"central directory entry count mismatch: expected {expected_entries}, got {len(entries)}"
        )
    return entries


def normalized_zip_name(name: str) -> str:
    value = name.replace("\\", "/").lstrip("/")
    while value.startswith("./"):
        value = value[2:]
    return value


def read_manifest_from_remote(
    client: HttpClient,
    url: str,
    tail_bytes: int,
    max_central_directory: int,
    max_manifest_compressed: int,
    max_manifest_uncompressed: int,
) -> tuple[Manifest, int | None]:
    metadata = client.head(url)
    remote_size = metadata.get("file_size")
    if not isinstance(remote_size, int) or remote_size <= 0:
        remote_size = None

    if remote_size is None:
        tail, response = client.range_bytes(url, None, tail_bytes)
    else:
        start = max(0, remote_size - tail_bytes)
        tail, response = client.range_bytes(url, start, remote_size - 1)
    try:
        content_range = parse_content_range(response.headers.get("Content-Range", ""))
        if content_range:
            _start, _end, total = content_range
            if total is not None:
                remote_size = total
    finally:
        response.close()

    def read_range(start: int, end: int) -> bytes:
        if start < 0 or end < start:
            raise RemoteReadError(f"invalid ZIP range {start}-{end}")
        data, range_response = client.range_bytes(url, start, end)
        try:
            content_range = parse_content_range(
                range_response.headers.get("Content-Range", "")
            )
            if content_range and content_range[0] != start:
                raise RemoteReadError("server returned a different Range start")
            if len(data) != end - start + 1:
                raise RemoteReadError(
                    f"short Range response: expected {end - start + 1}, got {len(data)}"
                )
            return data
        finally:
            range_response.close()

    central_offset, central_size, expected_entries = parse_eocd(
        tail, read_range, remote_size
    )
    if central_size > max_central_directory:
        raise RemoteReadError(
            f"central directory is too large ({central_size} bytes; limit {max_central_directory})"
        )
    if central_size == 0:
        entries: list[CentralEntry] = []
    else:
        central = read_range(central_offset, central_offset + central_size - 1)
        entries = parse_central_directory(central, expected_entries)
    manifest_entry = next(
        (
            entry
            for entry in entries
            if normalized_zip_name(entry.name).casefold() == "manifest.xml"
        ),
        None,
    )
    if manifest_entry is None:
        return Manifest("", "", "", "", "missing_manifest", "manifest.xml not found"), remote_size
    if manifest_entry.encrypted:
        return Manifest("", "", "", "", "encrypted_manifest", "manifest.xml is encrypted"), remote_size
    if manifest_entry.compressed_size > max_manifest_compressed:
        raise RemoteReadError(
            f"manifest compressed data is too large ({manifest_entry.compressed_size} bytes)"
        )
    if manifest_entry.uncompressed_size > max_manifest_uncompressed:
        raise RemoteReadError(
            f"manifest is too large ({manifest_entry.uncompressed_size} bytes)"
        )

    local_header = read_range(manifest_entry.local_offset, manifest_entry.local_offset + 29)
    if local_header[:4] != LOCAL_FILE_SIGNATURE:
        raise RemoteReadError("invalid manifest local file header")
    (
        _signature,
        _version,
        _flags,
        _compression,
        _modified_time,
        _modified_date,
        _crc,
        _local_compressed_size,
        _local_uncompressed_size,
        name_length,
        extra_length,
    ) = struct.unpack("<4s5H3I2H", local_header)
    data_start = manifest_entry.local_offset + 30 + name_length + extra_length
    if manifest_entry.compressed_size:
        compressed = read_range(
            data_start, data_start + manifest_entry.compressed_size - 1
        )
    else:
        compressed = b""
    if manifest_entry.compression == 0:
        manifest_bytes = compressed
    elif manifest_entry.compression == 8:
        try:
            manifest_bytes = zlib.decompress(compressed, -15)
        except zlib.error as error:
            raise RemoteReadError(f"manifest deflate data is invalid: {error}") from error
    else:
        return Manifest(
            "", "", "", "", "unsupported_compression",
            f"manifest compression method {manifest_entry.compression} is unsupported",
        ), remote_size
    if len(manifest_bytes) > max_manifest_uncompressed:
        raise RemoteReadError("decompressed manifest is too large")
    try:
        root = ET.fromstring(manifest_bytes)
    except ET.ParseError as error:
        return Manifest("", "", "", "", "invalid_manifest", str(error)), remote_size

    def field(name: str) -> str:
        wanted = name.casefold()
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1].casefold() if isinstance(element.tag, str) else ""
            if tag == wanted:
                value = (element.text or "").strip()
                if value:
                    return value
        return ""

    guid = field("guid")
    if not guid:
        return Manifest("", field("name"), field("version"), field("author"), "invalid_manifest", "guid missing"), remote_size
    return Manifest(guid, field("name"), field("version"), field("author"), "ok", ""), remote_size


SCHEMA = """
CREATE TABLE IF NOT EXISTS remote_zipmods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL,
    download_url TEXT NOT NULL,
    directory_url TEXT NOT NULL DEFAULT '',
    relative_path TEXT NOT NULL DEFAULT '',
    file_name TEXT NOT NULL DEFAULT '',
    guid TEXT NOT NULL DEFAULT '',
    guid_norm TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '',
    file_size INTEGER,
    last_modified TEXT NOT NULL DEFAULT '',
    etag TEXT NOT NULL DEFAULT '',
    manifest_status TEXT NOT NULL DEFAULT '',
    scan_error TEXT NOT NULL DEFAULT '',
    indexed_at TEXT NOT NULL DEFAULT '',
    last_seen_at TEXT NOT NULL DEFAULT '',
    present INTEGER NOT NULL DEFAULT 1,
    UNIQUE(source_url, download_url)
);
CREATE INDEX IF NOT EXISTS idx_remote_zipmods_guid ON remote_zipmods(guid_norm);
CREATE INDEX IF NOT EXISTS idx_remote_zipmods_name ON remote_zipmods(name);
CREATE INDEX IF NOT EXISTS idx_remote_zipmods_author ON remote_zipmods(author);
CREATE INDEX IF NOT EXISTS idx_remote_zipmods_present ON remote_zipmods(source_url, present);
CREATE TABLE IF NOT EXISTS remote_index_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    discovered_files INTEGER NOT NULL DEFAULT 0,
    indexed_files INTEGER NOT NULL DEFAULT 0,
    reused_files INTEGER NOT NULL DEFAULT 0,
    failed_files INTEGER NOT NULL DEFAULT 0,
    directory_count INTEGER NOT NULL DEFAULT 0
);
"""


def relative_path(root_url: str, file_url: str) -> str:
    root_path = urllib.parse.unquote(urllib.parse.urlsplit(root_url).path).rstrip("/") + "/"
    file_path = urllib.parse.unquote(urllib.parse.urlsplit(file_url).path)
    if file_path.startswith(root_path):
        return file_path[len(root_path) :]
    return posixpath.basename(file_path)


def inspect_one(
    client: HttpClient,
    source_url: str,
    url: str,
    existing: dict[str, object] | None,
    force: bool,
    tail_bytes: int,
    max_central_directory: int,
    max_manifest_compressed: int,
    max_manifest_uncompressed: int,
) -> dict[str, object]:
    parsed = urllib.parse.urlsplit(url)
    file_name = urllib.parse.unquote(posixpath.basename(parsed.path))
    directory = url.rsplit("/", 1)[0] + "/"
    metadata = client.head(url)
    file_size = metadata.get("file_size")
    last_modified = str(metadata.get("last_modified") or "")
    etag = str(metadata.get("etag") or "")
    same_remote = bool(
        existing
        and not force
        and str(existing.get("manifest_status") or "") == "ok"
        and isinstance(file_size, int)
        and int(existing.get("file_size") or -1) == file_size
        and (
            (etag and etag == str(existing.get("etag") or ""))
            or (last_modified and last_modified == str(existing.get("last_modified") or ""))
        )
    )
    if same_remote:
        return {
            **existing,
            "download_url": url,
            "directory_url": directory,
            "relative_path": relative_path(source_url, url),
            "file_name": file_name,
            "last_seen_at": utc_now(),
            "present": 1,
            "reused": True,
        }

    try:
        manifest, discovered_size = read_manifest_from_remote(
            client,
            url,
            tail_bytes,
            max_central_directory,
            max_manifest_compressed,
            max_manifest_uncompressed,
        )
        if not isinstance(file_size, int):
            file_size = discovered_size
        return {
            "source_url": source_url,
            "download_url": url,
            "directory_url": directory,
            "relative_path": relative_path(source_url, url),
            "file_name": file_name,
            "guid": manifest.guid,
            "guid_norm": manifest.guid.casefold(),
            "name": manifest.name,
            "version": manifest.version,
            "author": manifest.author,
            "file_size": file_size,
            "last_modified": last_modified,
            "etag": etag,
            "manifest_status": manifest.status,
            "scan_error": manifest.error,
            "indexed_at": utc_now(),
            "last_seen_at": utc_now(),
            "present": 1,
            "reused": False,
        }
    except RemoteReadError as error:
        return {
            "source_url": source_url,
            "download_url": url,
            "directory_url": directory,
            "relative_path": relative_path(source_url, url),
            "file_name": file_name,
            "guid": "",
            "guid_norm": "",
            "name": "",
            "version": "",
            "author": "",
            "file_size": file_size,
            "last_modified": last_modified,
            "etag": etag,
            "manifest_status": "read_error",
            "scan_error": str(error),
            "indexed_at": utc_now(),
            "last_seen_at": utc_now(),
            "present": 1,
            "reused": False,
        }


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


DB_COLUMNS = (
    "source_url", "download_url", "directory_url", "relative_path", "file_name",
    "guid", "guid_norm", "name", "version", "author", "file_size", "last_modified",
    "etag", "manifest_status", "scan_error", "indexed_at", "last_seen_at", "present",
)


def save_result(conn: sqlite3.Connection, result: dict[str, object]) -> None:
    values = [result.get(column) for column in DB_COLUMNS]
    placeholders = ", ".join("?" for _ in DB_COLUMNS)
    assignments = ", ".join(
        f"{column}=excluded.{column}"
        for column in DB_COLUMNS
        if column not in {"source_url", "download_url"}
    )
    conn.execute(
        f"""
        INSERT INTO remote_zipmods ({', '.join(DB_COLUMNS)})
        VALUES ({placeholders})
        ON CONFLICT(source_url, download_url) DO UPDATE SET {assignments}
        """,
        values,
    )


def build_index(args: argparse.Namespace) -> int:
    source_url = directory_url(args.source_url)
    output = Path(args.output).expanduser().resolve()
    crawler_holder: dict[str, DirectoryCrawler] = {}

    def allowed(url: str) -> bool:
        crawler = crawler_holder.get("crawler")
        return crawler.allowed(url) if crawler else False

    client = HttpClient(args.timeout, args.retries, allowed)
    crawler = DirectoryCrawler(
        client,
        source_url,
        args.max_depth,
        args.max_files,
        args.max_directory_bytes,
    )
    crawler_holder["crawler"] = crawler
    directories, files = crawler.crawl()
    complete_scan = not crawler.had_errors and not crawler.truncated
    print(f"[discovered] {len(files)} ZIPMOD files in {len(directories)} directories")

    conn = connect_database(output)
    started_at = utc_now()
    existing_rows = {
        str(row["download_url"]): dict(row)
        for row in conn.execute(
            "SELECT * FROM remote_zipmods WHERE source_url = ?", (source_url,)
        )
    }
    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                inspect_one,
                client,
                source_url,
                url,
                existing_rows.get(url),
                args.force,
                args.tail_bytes,
                args.max_central_directory,
                args.max_manifest_compressed,
                args.max_manifest_uncompressed,
            ): url
            for url in files
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            status = str(result.get("manifest_status") or "")
            label = "reused" if result.get("reused") else status
            print(f"[file {completed}/{len(files)}] {label}: {result['relative_path']}", flush=True)

    with conn:
        # Do not prune an empty result: an unavailable directory listing must
        # not make a previously valid index look as if every file vanished.
        if complete_scan:
            conn.execute(
                "UPDATE remote_zipmods SET present = 0 WHERE source_url = ?",
                (source_url,),
            )
        for result in results:
            save_result(conn, result)
        finished_at = utc_now()
        indexed = sum(1 for result in results if result.get("manifest_status") == "ok")
        reused = sum(1 for result in results if result.get("reused"))
        failed = sum(1 for result in results if result.get("manifest_status") == "read_error")
        conn.execute(
            """
            INSERT INTO remote_index_runs (
                source_url, started_at, finished_at, discovered_files,
                indexed_files, reused_files, failed_files, directory_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_url, started_at, finished_at, len(files), indexed, reused, failed, len(directories)),
        )
    conn.close()
    summary = {
        "ok": failed == 0,
        "source_url": source_url,
        "database": str(output),
        "directory_count": len(directories),
        "discovered_files": len(files),
        "indexed_files": indexed,
        "reused_files": reused,
        "failed_files": failed,
    }
    print(summary)
    return 0 if failed == 0 else 2


def query_index(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    if not output.is_file():
        print(f"index not found: {output}", file=sys.stderr)
        return 2
    conn = connect_database(output)
    source_url = directory_url(args.source_url) if args.source_url else None
    clauses = ["present = 1"]
    parameters: list[object] = []
    if source_url:
        clauses.append("source_url = ?")
        parameters.append(source_url)
    if args.query_guid:
        clauses.append("guid_norm = ?")
        parameters.append(args.query_guid.strip().casefold())
    if args.search:
        clauses.append("(name LIKE ? OR author LIKE ? OR file_name LIKE ? OR guid LIKE ?)")
        pattern = f"%{args.search}%"
        parameters.extend([pattern] * 4)
    rows = conn.execute(
        f"""
        SELECT guid, name, version, author, file_name, relative_path,
               file_size, manifest_status, scan_error, download_url
        FROM remote_zipmods
        WHERE {' AND '.join(clauses)}
        ORDER BY name COLLATE NOCASE, file_name COLLATE NOCASE
        """,
        parameters,
    ).fetchall()
    for row in rows:
        print(dict(row))
    print(f"matches: {len(rows)}")
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--max-depth", type=int, default=32)
    parser.add_argument("--max-files", type=int, default=0, help="0 means no limit")
    parser.add_argument("--max-directory-bytes", type=int, default=DEFAULT_MAX_DIRECTORY_BYTES)
    parser.add_argument("--tail-bytes", type=int, default=DEFAULT_TAIL_BYTES)
    parser.add_argument("--max-central-directory", type=int, default=DEFAULT_MAX_CENTRAL_DIRECTORY)
    parser.add_argument("--max-manifest-compressed", type=int, default=DEFAULT_MAX_MANIFEST_COMPRESSED)
    parser.add_argument("--max-manifest-uncompressed", type=int, default=DEFAULT_MAX_MANIFEST_UNCOMPRESSED)
    parser.add_argument("--force", action="store_true", help="re-read manifests even when validators match")
    parser.add_argument("--query-guid", help="query an existing index instead of building it")
    parser.add_argument("--search", help="query an existing index by name, author, file name, or GUID")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.query_guid or args.search:
        return query_index(args)
    return build_index(args)


if __name__ == "__main__":
    raise SystemExit(main())
