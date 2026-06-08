"""Stage 2: dump the small text config files — likely hold server URLs."""
import zipfile, sys, io

OUT = open(r"C:\Users\NoteBook\Documents\magic-legion\analysis\02_configs.out.txt",
           "w", encoding="utf-8")
def out(*a):
    print(*a, file=OUT)

APK = r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
z = zipfile.ZipFile(APK)

targets = [
    "assets/config.ini",
    "assets/config_extend.ini",
    "assets/config_extend_en.ini",
    "assets/debug_config.ini",
    "assets/version.txt",
    "assets/bin/Data/boot.config",
]
for t in targets:
    out("=" * 80)
    out(f"### {t}")
    out("=" * 80)
    try:
        data = z.read(t)
        try:
            out(data.decode("utf-8"))
        except UnicodeDecodeError:
            out(data.decode("latin-1"))
    except KeyError:
        out("  (not present)")
    out()
OUT.close()
print("written 02_configs.out.txt")
