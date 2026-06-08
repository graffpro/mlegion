"""Stage 1: structural fingerprint of the APK (no full extraction)."""
import zipfile, collections, os, sys

APK = r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"

z = zipfile.ZipFile(APK)
names = z.namelist()
print(f"TOTAL ENTRIES: {len(names)}\n")

# breakdown by extension
ext = collections.Counter()
sizebyext = collections.Counter()
for i in z.infolist():
    e = os.path.splitext(i.filename)[1].lower() or "(noext)"
    ext[e] += 1
    sizebyext[e] += i.file_size
print("=== BY EXTENSION (count / uncompressed MB) ===")
for e, c in ext.most_common(40):
    print(f"  {e:14} {c:6}   {sizebyext[e]/1e6:8.1f} MB")

# top-level dirs
top = collections.Counter()
for n in names:
    top[n.split('/')[0] if '/' in n else '(root)'] += 1
print("\n=== TOP-LEVEL ===")
for t, c in top.most_common():
    print(f"  {t:30} {c}")

# native libs reveal the engine
print("\n=== NATIVE LIBS (lib/) ===")
for n in sorted(names):
    if n.startswith('lib/'):
        info = z.getinfo(n)
        print(f"  {n:55} {info.file_size/1e6:7.2f} MB")

# engine marker detection
print("\n=== ENGINE MARKERS ===")
markers = {
    "Unity IL2CPP": ["libil2cpp.so", "global-metadata.dat"],
    "Unity Mono":   ["libmono", "/Managed/"],
    "Cocos2d-x":    ["libcocos2d", "libcocos"],
    "Cocos Lua/JS": [".luac", ".lua", ".jsc", "src/"],
    "Unreal":       ["libUE4", "libUnreal"],
    "Godot":        ["libgodot", ".pck"],
    "Flutter":      ["libflutter", "libapp.so"],
    "React Native": ["libreactnative", "index.android.bundle"],
}
joined = "\n".join(names)
for engine, keys in markers.items():
    hits = [k for k in keys if k in joined]
    if hits:
        print(f"  [HIT] {engine:16} via {hits}")

# config/asset files that often hold server URLs
print("\n=== CANDIDATE CONFIG/DATA FILES (root + assets, small) ===")
for n in sorted(names):
    low = n.lower()
    if any(k in low for k in ['config','setting','server','host','url','.json','.xml','.txt','.ini','.cfg','.plist','version']):
        try:
            sz = z.getinfo(n).file_size
        except KeyError:
            sz = -1
        if sz < 200000:  # skip big stuff
            print(f"  {n:60} {sz:>9}")
