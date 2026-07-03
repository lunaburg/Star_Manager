from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import pefile  # type: ignore
except ImportError:  # pragma: no cover - exercised only on incomplete dev envs.
    pefile = None


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_DIR = APP_ROOT / "release" / "win-unpacked"
DEFAULT_WARN_FILE = APP_ROOT / "build" / "pyinstaller" / "star_manager_backend" / "warn-star_manager_backend.txt"
RUNTIME_MODULES = ("PIL", "UnityPy", "texture2ddecoder", "etcpak", "astc_encoder", "fmod_toolkit")
REQUIRED_RUNTIME_DATA = (
    ("archspec", ("json", "cpu", "microarchitectures.json")),
    ("archspec", ("json", "cpu", "cpuid.json")),
)
PE_EXTENSIONS = {".exe", ".dll", ".pyd"}

WINDOWS_SYSTEM_DLLS = {
    "advapi32.dll",
    "bcrypt.dll",
    "bcryptprimitives.dll",
    "cfgmgr32.dll",
    "comctl32.dll",
    "comdlg32.dll",
    "crypt32.dll",
    "d3d11.dll",
    "d3dcompiler_47.dll",
    "dbghelp.dll",
    "dhcpcsvc.dll",
    "dnsapi.dll",
    "dwmapi.dll",
    "dwrite.dll",
    "dxgi.dll",
    "gdi32.dll",
    "imm32.dll",
    "iphlpapi.dll",
    "kernel32.dll",
    "msvcp_win.dll",
    "netapi32.dll",
    "nsi.dll",
    "ntdll.dll",
    "ole32.dll",
    "oleacc.dll",
    "oleaut32.dll",
    "powrprof.dll",
    "propsys.dll",
    "rpcrt4.dll",
    "secur32.dll",
    "setupapi.dll",
    "shell32.dll",
    "shlwapi.dll",
    "user32.dll",
    "userenv.dll",
    "usp10.dll",
    "uxtheme.dll",
    "version.dll",
    "win32u.dll",
    "winhttp.dll",
    "wininet.dll",
    "winmm.dll",
    "winspool.drv",
    "wintrust.dll",
    "ws2_32.dll",
    "wtsapi32.dll",
}

WINDOWS_DLL_PATTERNS = (
    re.compile(r"^api-ms-win-", re.I),
    re.compile(r"^ext-ms-win-", re.I),
    re.compile(r"^msvcrt\.dll$", re.I),
    re.compile(r"^ucrtbase\.dll$", re.I),
    re.compile(r"^vcruntime\d+(_\d+)?\.dll$", re.I),
    re.compile(r"^msvcp\d+\.dll$", re.I),
)

WARN_IGNORE_EXACT = {
    "_frozen_importlib",
    "_frozen_importlib_external",
    "_manylinux",
    "_posixshmem",
    "_posixsubprocess",
    "_scproxy",
    "_typeshed",
    "_winreg",
    "fcntl",
    "grp",
    "java",
    "org",
    "posix",
    "pwd",
    "readline",
    "resource",
    "sitecustomize",
    "termios",
    "usercustomize",
    "vms_lib",
}

WARN_IGNORE_PREFIXES = (
    "java.",
    "org.",
    "distutils.",
    "setuptools.",
    "pyimod",
    "UnityPy.classes.",
)

WARN_OPTIONAL_PREFIXES = (
    "aiohttp",
    "annotationlib",
    "astc_encoder.",
    "asyncio.",
    "compression",
    "Crypto",
    "dask",
    "defusedxml",
    "distributed",
    "fastparquet",
    "fuse",
    "importlib_resources",
    "jinja2",
    "isal",
    "js",
    "kerchunk",
    "libarchive",
    "lzmaffi",
    "multiprocessing.",
    "numpy",
    "olefile",
    "pandas",
    "panel",
    "paramiko",
    "pyarrow",
    "pygit2",
    "pytest",
    "requests",
    "requests_kerberos",
    "smbclient",
    "smbprotocol",
    "snappy",
    "tqdm",
    "trove_classifiers",
    "TypeTreeGeneratorAPI",
    "typing_extensions",
    "ujson",
    "yarl",
    "zstandard",
    "etcpak.",
)


@dataclass(frozen=True)
class ImportRecord:
    source: Path
    dll: str


def is_windows_provided_dll(name: str) -> bool:
    lowered = name.lower()
    return lowered in WINDOWS_SYSTEM_DLLS or any(pattern.match(lowered) for pattern in WINDOWS_DLL_PATTERNS)


def build_available_dll_index(package_dir: Path, extra_search_paths: list[Path]) -> dict[str, list[Path]]:
    search_roots = [package_dir, *extra_search_paths]
    index: dict[str, list[Path]] = {}
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in PE_EXTENSIONS:
                index.setdefault(path.name.lower(), []).append(path)
    return index


def read_pe_imports(path: Path) -> list[str]:
    if pefile is None:
        return []
    try:
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    except Exception:
        return []
    imports = []
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        try:
            imports.append(entry.dll.decode("utf-8", errors="replace"))
        except Exception:
            imports.append(str(entry.dll))
    pe.close()
    return imports


def scan_pe_dependencies(package_dir: Path, extra_search_paths: list[Path]) -> tuple[list[ImportRecord], list[ImportRecord]]:
    available = build_available_dll_index(package_dir, extra_search_paths)
    missing: list[ImportRecord] = []
    satisfied: list[ImportRecord] = []
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in PE_EXTENSIONS:
            continue
        for dll in read_pe_imports(path):
            record = ImportRecord(path, dll)
            lowered = dll.lower()
            if lowered in available or is_windows_provided_dll(dll):
                satisfied.append(record)
            else:
                missing.append(record)
    return missing, satisfied


def warn_module_bucket(module: str) -> str:
    if module in WARN_IGNORE_EXACT or module.startswith(WARN_IGNORE_PREFIXES):
        return "ignored"
    if module.startswith(WARN_OPTIONAL_PREFIXES):
        return "optional"
    return "review"


def parse_pyinstaller_warn(path: Path) -> dict[str, list[str]]:
    buckets = {"review": [], "optional": [], "ignored": []}
    if not path.exists():
        return buckets
    pattern = re.compile(r"^missing module named ['\"]?([^'\" ]+)['\"]?")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        module = match.group(1)
        bucket = warn_module_bucket(module)
        if module not in buckets[bucket]:
            buckets[bucket].append(module)
    for values in buckets.values():
        values.sort(key=str.lower)
    return buckets


def check_runtime_modules() -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in RUNTIME_MODULES}


def check_runtime_data_files() -> list[tuple[str, Path, bool]]:
    results: list[tuple[str, Path, bool]] = []
    for module_name, relative_parts in REQUIRED_RUNTIME_DATA:
        spec = importlib.util.find_spec(module_name)
        if spec is None or not spec.origin:
            results.append((module_name, Path(*relative_parts), False))
            continue
        module_dir = Path(spec.origin).resolve().parent
        path = module_dir.joinpath(*relative_parts)
        results.append((module_name, path, path.is_file()))
    return results


def package_runtime_paths(package_dir: Path) -> list[Path]:
    roots = [
        package_dir,
        package_dir / "resources",
        package_dir / "resources" / "backend",
        package_dir / "resources" / "app.asar.unpacked",
    ]
    return [path for path in roots if path.exists()]


def print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit packaged Star_Manager runtime dependencies.")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--warn-file", type=Path, default=DEFAULT_WARN_FILE)
    parser.add_argument(
        "--extra-search-path",
        type=Path,
        action="append",
        default=[],
        help="Additional directory to search when resolving PE DLL imports.",
    )
    args = parser.parse_args()

    package_dir = args.package_dir.resolve()
    warn_file = args.warn_file.resolve()

    if pefile is None:
        print("ERROR: Python package 'pefile' is required for PE dependency scanning.")
        print("Install it in the packaging Python environment, then run this command again.")
        return 2

    print(f"Package directory: {package_dir}")
    print(f"PyInstaller warn file: {warn_file}")

    print_section("Python runtime modules")
    module_status = check_runtime_modules()
    for name, ok in module_status.items():
        print(f"[{'OK' if ok else 'MISSING'}] {name}")
    data_status = check_runtime_data_files()
    for module_name, path, ok in data_status:
        print(f"[{'OK' if ok else 'MISSING'}] {module_name} data: {path}")

    missing, satisfied = scan_pe_dependencies(package_dir, package_runtime_paths(package_dir) + args.extra_search_path)
    grouped_missing: dict[str, list[Path]] = {}
    for record in missing:
        grouped_missing.setdefault(record.dll, []).append(record.source)

    print_section("PE dynamic libraries")
    if grouped_missing:
        print("Missing DLL imports:")
        for dll, sources in sorted(grouped_missing.items(), key=lambda item: item[0].lower()):
            print(f"[MISSING] {dll}")
            for source in sources[:5]:
                print(f"  used by {source.relative_to(package_dir)}")
            if len(sources) > 5:
                print(f"  ... and {len(sources) - 5} more")
    else:
        print(f"[OK] No unresolved PE DLL imports found in {package_dir}.")
    print(f"Scanned {len({record.source for record in satisfied + missing})} PE files.")

    warn_buckets = parse_pyinstaller_warn(warn_file)
    print_section("PyInstaller missing-module warnings")
    if warn_buckets["review"]:
        print("Review these module warnings first:")
        for module in warn_buckets["review"]:
            print(f"[REVIEW] {module}")
    else:
        print("[OK] No high-priority missing-module warnings after filtering common optional noise.")
    print(f"Optional warnings: {len(warn_buckets['optional'])}")
    print(f"Ignored platform/package noise: {len(warn_buckets['ignored'])}")

    static_libs = sorted(package_dir.rglob("*.lib")) + sorted(package_dir.rglob("*.a"))
    print_section("Static libraries")
    if static_libs:
        for lib in static_libs:
            print(f"[REVIEW] Static library present in package: {lib.relative_to(package_dir)}")
    else:
        print("[OK] No static libraries found in the packaged app. Static libraries are build-time inputs and normally are not shipped.")

    failed_modules = [name for name, ok in module_status.items() if not ok]
    failed_data = [path for _module_name, path, ok in data_status if not ok]
    failed = bool(grouped_missing or warn_buckets["review"] or failed_modules or failed_data)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
