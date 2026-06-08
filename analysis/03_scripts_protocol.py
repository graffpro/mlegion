"""Stage 3: find scripting (Lua) + protocol (protobuf) + data tables; map asset tree."""
import zipfile, collections, os, re

APK = r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
OUT = open(r"C:\Users\NoteBook\Documents\magic-legion\analysis\03_scripts_protocol.out.txt",
           "w", encoding="utf-8")
def out(*a): print(*a, file=OUT)

z = zipfile.ZipFile(APK)
names = z.namelist()

# --- full assets/ listing grouped by 2nd-level dir ---
out("=== assets/ SUBDIRECTORIES (count, MB) ===")
byd = collections.Counter(); szd = collections.Counter()
for i in z.infolist():
    n = i.filename
    if n.startswith("assets/") and not n.endswith("/"):
        parts = n.split("/")
        key = "/".join(parts[:3]) if len(parts) > 3 else "/".join(parts[:2])
        byd[key] += 1; szd[key] += i.file_size
for k, c in sorted(byd.items()):
    out(f"  {k:45} {c:5}  {szd[k]/1e6:7.2f} MB")

# --- hunt for script / protocol / data file types anywhere ---
out("\n=== SCRIPT / PROTOCOL / DATA candidates (anywhere in APK) ===")
patterns = ['lua', 'proto', '.pb', 'protobuf', 'json', 'msgpack', 'res_scripts',
            'script', '.bytes', 'table', 'lang', 'i18n', 'locale', 'cfg', '.zip', '.dat']
hits = collections.defaultdict(list)
for n in names:
    low = n.lower()
    for p in patterns:
        if p in low:
            hits[p].append(n)
for p in patterns:
    lst = hits[p]
    if lst:
        out(f"\n  [{p}]  ({len(lst)} files)")
        for n in lst[:25]:
            out(f"      {n}")
        if len(lst) > 25:
            out(f"      ... +{len(lst)-25} more")

# --- the 'noext' big files: where are they ---
out("\n=== LARGEST FILES (top 30) ===")
big = sorted(z.infolist(), key=lambda i: -i.file_size)[:30]
for i in big:
    out(f"  {i.file_size/1e6:7.2f} MB  {i.filename}")

OUT.close()
print("written 03_scripts_protocol.out.txt")
