"""
Repackage the Magic Legion APK so it talks to OUR server instead of the dead fragon hosts.
Edits assets/config.ini (and debug_config.ini): rewrites the fragon hostnames to our host
(10.0.2.2 = the VirtualBox-NAT host alias LDPlayer's Android sees) and downgrades our URLs
to plain http (so no TLS/CA/root needed). Drops the old signature; re-signing is done by
uber-apk-signer afterwards (which also zip-aligns).

Usage: python tools/repackage_apk.py   (ML_HOST_IP overrides the host)
"""
import zipfile, os

HOST = os.environ.get("ML_HOST_IP", "10.0.2.2")
SRC = r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
OUTDIR = r"C:\Users\NoteBook\Documents\magic-legion\build"
OUT = os.path.join(OUTDIR, "ml_repacked_unsigned.apk")
os.makedirs(OUTDIR, exist_ok=True)

HOSTS = ["android.ml.fragon.com", "android1.ml.fragon.com",
         "account.ml.fragon.com", "account1.ml.fragon.com",
         "push.ml.fragon.com", "gmip.ml.fragon.com", "translate.ml.fragon.com"]


def patch(text):
    for h in HOSTS:
        text = text.replace(h, HOST)
    text = text.replace(f"https://{HOST}", f"http://{HOST}")  # downgrade OUR host to http
    return text


zin = zipfile.ZipFile(SRC, "r")
zout = zipfile.ZipFile(OUT, "w")
patched = []
for item in zin.infolist():
    name = item.filename
    if name.startswith("META-INF/"):          # remove old signature
        continue
    data = zin.read(name)
    if name in ("assets/config.ini", "assets/debug_config.ini"):
        new = patch(data.decode("utf-8", "replace"))
        if new != data.decode("utf-8", "replace"):
            patched.append(name)
        data = new.encode("utf-8")
    zi = zipfile.ZipInfo(name, date_time=item.date_time)
    zi.compress_type = item.compress_type      # preserve STORED vs DEFLATED (native libs!)
    zi.external_attr = item.external_attr
    zout.writestr(zi, data)
zin.close()
zout.close()

print("patched:", patched)
print(f"wrote {OUT}  ({os.path.getsize(OUT)//1024//1024} MB)")
print(f"\n--- new config.ini lines mentioning our host / fragon ---")
cfg = zipfile.ZipFile(OUT).read("assets/config.ini").decode("utf-8", "replace")
for line in cfg.splitlines():
    s = line.strip()
    if (HOST in s or "fragon" in s.lower()) and s and not s.startswith("#"):
        print("  " + s)
