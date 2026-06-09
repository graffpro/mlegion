"""
Fill EVERY lost CDN asset with a valid same-type placeholder bundled straight into the APK,
so the client never has to reach the dead CDN — it takes everything from our build.

Why bundling (not serving): the client does NOT md5-verify assets it extracts from the APK
(proven: present assets have md5(content) != files_full `v`, yet load fine), whereas it DOES
verify CDN downloads. So a placeholder placed in the APK loads with no verification fight.

For each lost asset we drop in the smallest present bundle OF THE SAME TYPE (uiatlas->uiatlas,
ui->ui, fx->fx, ...) so the prefab/atlas loader gets a structurally valid UnityFS bundle. The
art is wrong/blank, but present UI prefabs (Login, MainUI, ...) still lay out and the client
proceeds to connect to our server. files_full.xml + files.xml are restored to the originals
and each placeholdered entry's v/s/z is rewritten to the placeholder's so any size/hash gate
the loader applies still passes.
"""
import zipfile, re, hashlib, os

APK = r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
DEC = r"C:\Users\NoteBook\Documents\magic-legion\build\ml_decoded"
ASSETS = os.path.join(DEC, "assets")

z = zipfile.ZipFile(APK)
have = {n.split("/")[-1]: n for n in z.namelist() if n.startswith("assets/")}

# 1) restore the pristine manifests (undo the earlier surgery / files_full=files.xml)
for mf in ("bundle.xml", "files.xml", "files_full.xml"):
    with open(os.path.join(ASSETS, mf), "wb") as f:
        f.write(z.read("assets/" + mf))

# 2) every asset the game knows about
ff = z.read("assets/files_full.xml").decode("utf-8", "replace")
entries = re.findall(r'<d u="([^"]+)" v="([^"]+)" s="(\d+)" z="(\d+)"', ff)
present = set(have)


def typ(n):
    return n.split("_", 1)[0] if "_" in n else n


# 3) smallest donor per type (+ a global tiny fallback for typeless/donor-less kinds)
donors, gmin = {}, None
for n in present:
    sz = z.getinfo(have[n]).file_size
    if gmin is None or sz < gmin[1]:
        gmin = (n, sz)
    if "_" in n:
        t = typ(n)
        if t not in donors or sz < donors[t][1]:
            donors[t] = (n, sz)

# 4) write a placeholder for every lost asset
patches, cache = {}, {}
added = total = 0
by_type = {}
for name, v, s, zz in entries:
    if name in present:
        continue
    dn = donors.get(typ(name), gmin)[0]
    if dn not in cache:
        cache[dn] = z.read(have[dn])
    data = cache[dn]
    with open(os.path.join(ASSETS, name), "wb") as f:
        f.write(data)
    patches[name] = (hashlib.md5(data).hexdigest(), len(data))
    by_type[typ(name)] = by_type.get(typ(name), 0) + 1
    added += 1
    total += len(data)

print(f"placeholdered {added} lost assets  (+{total/1024/1024:.0f} MB)")
print("by type:", dict(sorted(by_type.items(), key=lambda x: -x[1])))


# 5) rewrite v/s/z of placeholdered entries to match the donor content
def patch_manifest(path):
    txt = open(path, encoding="utf-8").read()

    def repl(m):
        nm = m.group(1)
        if nm in patches:
            md5, sz = patches[nm]
            return f'<d u="{nm}" v="{md5}" s="{sz}" z="{sz}" />'
        return m.group(0)

    txt = re.sub(r'<d u="([^"]+)" v="[^"]+" s="\d+" z="\d+"\s*/>', repl, txt)
    open(path, "w", encoding="utf-8").write(txt)


patch_manifest(os.path.join(ASSETS, "files_full.xml"))
# CRITICAL: the client downloads exactly (files_full.xml MINUS files.xml) — everything in
# files_full but not in files.xml is fetched as a .zip from the CDN. Make files.xml IDENTICAL
# to the patched files_full so EVERY asset (incl. our placeholders) is treated as bundled and
# extracted straight from the APK — nothing is ever downloaded.
import shutil
shutil.copy(os.path.join(ASSETS, "files_full.xml"), os.path.join(ASSETS, "files.xml"))
print("manifests: files.xml := patched files_full (all 1799 bundled, zero downloads)")
