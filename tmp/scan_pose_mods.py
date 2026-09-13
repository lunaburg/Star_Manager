from pathlib import Path
import re
import sys
import zipfile

root = Path(sys.argv[1])
files = list(root.rglob("*.zipmod"))
print("zipmods", len(files), flush=True)
out = []
for index, path in enumerate(files, 1):
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.lower().endswith(".csv") and "characustom" in name.lower():
                    data = archive.read(name)
                    if re.search(rb"(?m)^501\s*$", data):
                        out.append((str(path), name, len(data)))
                        break
    except Exception:
        continue
    if index % 1000 == 0:
        print("checked", index, flush=True)
print("matches", len(out), flush=True)
for item in out[:100]:
    print(*item, sep="\t")
