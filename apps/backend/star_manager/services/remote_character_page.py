from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from star_manager.core.runtime_paths import runtime_root


REMOTE_CHARACTER_PAGE_CACHE_ROOT = runtime_root() / "remote_character_pages"
REMOTE_CHARACTER_PAGE_HOST = "db.bepis.moe"
REMOTE_CHARACTER_PAGE_TTL_SECONDS = 15 * 60
REMOTE_CHARACTER_PAGE_SIZE = 24
REMOTE_CHARACTER_CACHE_VERSION = 4
MAX_SEARCH_BYTES = 2 * 1024 * 1024
SAFE_CACHE_KEY = re.compile(r"^[a-f0-9]{32}$")
REMOTE_CARD_TYPES = {"aishoujo": "AI", "aiscenes": "AISCENE"}


class RemoteCharacterPageError(ValueError):
    """Raised when a remote character-card page cannot be read safely."""


def _validate_page_url(page_url: str) -> tuple[str, int, str]:
    try:
        parsed = urlsplit(str(page_url or "").strip())
        port = parsed.port
    except ValueError as error:
        raise RemoteCharacterPageError("网站卡片列表页面 URL 无效") from error
    if parsed.scheme != "https" or parsed.hostname != REMOTE_CHARACTER_PAGE_HOST or port not in (None, 443) or parsed.username or parsed.password:
        raise RemoteCharacterPageError("只支持 https://db.bepis.moe 的卡片列表页面")
    page_path = parsed.path.strip("/")
    if page_path not in REMOTE_CARD_TYPES or parsed.fragment:
        raise RemoteCharacterPageError("请输入人物卡或场景卡列表页面 URL")
    query = parse_qs(parsed.query, keep_blank_values=True)
    page_values = query.get("page", ["1"])
    if set(query) - {"page"} or len(page_values) != 1 or not re.fullmatch(r"[1-9]\d{0,5}", page_values[0]):
        raise RemoteCharacterPageError("网站卡片页码无效")
    page = int(page_values[0])
    return f"https://{REMOTE_CHARACTER_PAGE_HOST}/{page_path}?page={page}", page, REMOTE_CARD_TYPES[page_path]


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RemoteCharacterPageError("远程页面发生跳转，已停止读取")


def _open_remote(url: str, timeout: float = 30.0):
    request = Request(
        url,
        headers={
            "User-Agent": "Star_Manager/1.0 (+local character-card browser)",
            "Accept": "application/json",
        },
    )
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _read_limited(response, limit: int) -> bytes:
    body = response.read(limit + 1)
    if len(body) > limit:
        raise RemoteCharacterPageError("远程卡片列表数据过大")
    return body


def _parse_search_response(body: bytes, card_type: str = "AI") -> tuple[list[dict[str, object]], int]:
    if card_type not in REMOTE_CARD_TYPES.values():
        raise RemoteCharacterPageError("不支持的网站卡片类型")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RemoteCharacterPageError("远程卡片接口返回无效 JSON") from error
    if not isinstance(payload, dict) or payload.get("type") != "success":
        raise RemoteCharacterPageError("远程卡片接口未返回成功结果")
    data = payload.get("data")
    if not isinstance(data, dict) or type(data.get("searchHitCount")) is not int or data["searchHitCount"] < 0:
        raise RemoteCharacterPageError("远程卡片接口缺少分页信息")
    raw_cards = data.get("cards")
    if not isinstance(raw_cards, list) or len(raw_cards) > REMOTE_CHARACTER_PAGE_SIZE:
        raise RemoteCharacterPageError("远程卡片接口返回无效卡片列表")

    cards: list[dict[str, object]] = []
    for raw in raw_cards:
        if not isinstance(raw, dict) or raw.get("cardType") != card_type or type(raw.get("id")) is not int or raw["id"] <= 0:
            raise RemoteCharacterPageError("远程卡片接口返回无效卡片")
        card_id = raw["id"]
        card_data = raw.get("cardData")
        if not isinstance(card_data, dict):
            raise RemoteCharacterPageError("远程卡片接口返回无效卡片资料")
        tags = raw.get("tags")
        if not isinstance(tags, list):
            raise RemoteCharacterPageError("远程卡片接口返回无效标签")
        uploader = raw.get("uploader")
        uploader_name = raw.get("uploaderName") or raw.get("cardAuthor")
        if not uploader_name and isinstance(uploader, dict):
            uploader_name = uploader.get("displayName") or uploader.get("username") or uploader.get("name")
        thumbnail_url = f"https://{REMOTE_CHARACTER_PAGE_HOST}/card/thumb/{card_type}_{card_id:06d}_thumb.webp"
        page_path = "aiscenes" if card_type == "AISCENE" else "aishoujo"
        cards.append(
            {
                "id": card_id,
                "name": str((raw.get("customName") if card_type == "AISCENE" else card_data.get("name")) or f"{'场景卡' if card_type == 'AISCENE' else '人物卡'} {card_id}"),
                "card_type": card_type,
                "gender": str(card_data.get("gender") or ""),
                "personality": card_data.get("personality"),
                "male_count": card_data.get("maleCount"),
                "female_count": card_data.get("femaleCount"),
                "object_count": card_data.get("objectCount"),
                "file_size": raw.get("fileSize"),
                "download_count": raw.get("downloadCount"),
                "votes": raw.get("votes"),
                "tags": tags,
                "uploader": str(uploader_name or "Anonymous"),
                "date_created_utc": str(raw.get("dateCreatedUtc") or ""),
                "detail_url": f"https://{REMOTE_CHARACTER_PAGE_HOST}/{page_path}/view/{card_id}",
                "thumbnail_url": thumbnail_url,
                "cover_url": thumbnail_url,
            }
        )
    page_count = max(1, (data["searchHitCount"] + REMOTE_CHARACTER_PAGE_SIZE - 1) // REMOTE_CHARACTER_PAGE_SIZE)
    return cards, page_count


def _cache_key(page_url: str) -> str:
    return hashlib.md5(page_url.encode("utf-8"), usedforsecurity=False).hexdigest()


def _manifest_path(cache_key: str) -> Path:
    if not SAFE_CACHE_KEY.fullmatch(cache_key):
        raise RemoteCharacterPageError("远程页面缓存标识无效")
    return REMOTE_CHARACTER_PAGE_CACHE_ROOT / cache_key / "manifest.json"


def resolve_remote_cover(cache_key: str, file_name: str) -> Path | None:
    if not SAFE_CACHE_KEY.fullmatch(cache_key) or not re.fullmatch(r"cover_\d+\.(?:webp|png|jpe?g|gif)", file_name, re.I):
        return None
    root = (REMOTE_CHARACTER_PAGE_CACHE_ROOT / cache_key).resolve()
    candidate = (root / file_name).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def _load_cached(cache_key: str, page_url: str, card_type: str) -> dict[str, object] | None:
    manifest_path = _manifest_path(cache_key)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("version") != REMOTE_CHARACTER_CACHE_VERSION or manifest.get("source_url") != page_url:
            return None
        if time.time() - float(manifest.get("fetched_at") or 0) > REMOTE_CHARACTER_PAGE_TTL_SECONDS:
            return None
        cards = manifest.get("cards")
        page_count = manifest.get("page_count")
        if not isinstance(cards, list) or type(page_count) is not int or page_count < 1:
            return None
        for card in cards:
            if not isinstance(card, dict) or type(card.get("id")) is not int or card["id"] <= 0:
                return None
            expected_url = f"https://{REMOTE_CHARACTER_PAGE_HOST}/card/thumb/{card_type}_{card['id']:06d}_thumb.webp"
            if card.get("card_type") != card_type or card.get("cover_url") != expected_url or card.get("thumbnail_url") != expected_url:
                return None
        return manifest
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def fetch_character_page(page_url: str) -> dict[str, object]:
    normalized_url, page, card_type = _validate_page_url(page_url)
    cache_key = _cache_key(normalized_url)
    cached = _load_cached(cache_key, normalized_url, card_type)
    if cached:
        return {"ok": True, "source_url": normalized_url, "cards": cached["cards"], "page_count": cached["page_count"], "cached": True}

    try:
        api_url = f"https://{REMOTE_CHARACTER_PAGE_HOST}/api/frontend/search?cardType={card_type}"
        if page > 1:
            api_url += f"&page={page}"
        with _open_remote(api_url, timeout=12.0) as response:
            cards, page_count = _parse_search_response(_read_limited(response, MAX_SEARCH_BYTES), card_type)
    except (HTTPError, URLError, OSError) as error:
        raise RemoteCharacterPageError(f"远程卡片列表读取失败：{error}") from error

    manifest = {
        "version": REMOTE_CHARACTER_CACHE_VERSION,
        "source_url": normalized_url,
        "fetched_at": time.time(),
        "page_count": page_count,
        "cards": cards,
    }
    try:
        cache_dir = REMOTE_CHARACTER_PAGE_CACHE_ROOT / cache_key
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    except OSError:
        # A cache write failure must not delay or prevent the current page from loading.
        pass
    return {"ok": True, "source_url": normalized_url, "cards": cards, "page_count": page_count, "cached": False}
