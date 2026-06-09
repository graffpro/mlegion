"""Consistently strip the 3 permanently-lost CDN bundles from bundle.xml so the
client's dependency preprocessing (ResourceManager.preprocMultiDepends) doesn't hit a
dangling reference (NullReferenceException) and the pre-load completes.

bundle.xml has TWO sections we must keep consistent:
  1. dependency tree:  <file f="BUNDLE"> <d p="DEP" /> ... </file>
  2. prefab->bundle map: <file p="Some.prefab" b="BUNDLE" />
For each lost BUNDLE we drop: its <file f="BUNDLE"> block, every <d p="BUNDLE"> dep,
and every <file ... b="BUNDLE"> prefab mapping. Reads the pristine copy from the APK so
re-runs are idempotent.
"""
import zipfile
APK = r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
DST = r"C:\Users\NoteBook\Documents\magic-legion\build\ml_decoded\assets\bundle.xml"
LOST = ["497bea7e487302c3bc0c60749f7a2967",
        "62e3f575cad1ba9f607aebb2c30483e9",
        "0f9dc23c401cf8f28ade427f96f1d3d8"]
SELFCLOSE = "/" + ">"
ENDFILE = "</file" + ">"

raw = zipfile.ZipFile(APK).read("assets/bundle.xml").decode("utf-8")
lines = raw.splitlines(keepends=True)
out, skip, rf, rd, rb = [], False, 0, 0, 0
for line in lines:
    if skip:
        if ENDFILE in line:
            skip = False
        continue
    hit = any(h in line for h in LOST)
    if "<file f=" in line and hit:                 # section-1 bundle definition block
        rf += 1
        if not line.rstrip().endswith(SELFCLOSE):
            skip = True
        continue
    if "<file " in line and " b=" in line and hit:  # section-2 prefab->bundle mapping
        rb += 1
        continue
    if "<d p=" in line and hit:                     # section-1 dependency edge
        rd += 1
        continue
    out.append(line)
open(DST, "w", encoding="utf-8").write("".join(out))
print("removed", rf, "<file> def-blocks,", rd, "<d> deps,", rb, "prefab maps; now", len(out), "lines")
