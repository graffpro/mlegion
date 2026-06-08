"""Stage 4: is global-metadata.dat dumpable? check magic + version. Peek at ELF + dex."""
import struct, os

base = r"C:\Users\NoteBook\Documents\magic-legion\apk"
meta = os.path.join(base, "assets/bin/Data/Managed/Metadata/global-metadata.dat")

with open(meta, "rb") as f:
    head = f.read(16)
magic, version = struct.unpack_from("<II", head, 0)
print(f"global-metadata.dat size: {os.path.getsize(meta):,} bytes")
print(f"  magic   = 0x{magic:08X}   (expected 0xFAB11BAF for un-encrypted)")
print(f"  version = {version}        (Unity metadata version)")
print(f"  -> {'OK, standard & dumpable' if magic==0xFAB11BAF else 'ENCRYPTED/OBFUSCATED - needs extra work'}")

# map metadata version -> approx Unity version
ver_map = {21:"5.3.2-5.3.6", 22:"5.3.7", 23:"5.4-5.5", 24:"5.6/2017-2018",
           "24.1":"2018", "24.2":"2019", "24.3":"2019.3-2020.1", "24.4":"2020.2",
           "24.5":"2021", "27":"2020.2+", 29:"2021.2+", 31:"2022.3+"}
print(f"  approx Unity: {ver_map.get(version, 'see 24.x sub-versions')}")

# ELF arch check on libil2cpp.so
so = os.path.join(base, "lib/arm64-v8a/libil2cpp.so")
with open(so, "rb") as f:
    e = f.read(20)
print(f"\nlibil2cpp.so (arm64): ELF magic={e[:4]!r} class={'64-bit' if e[4]==2 else '32-bit'} "
      f"machine=0x{struct.unpack_from('<H', e, 18)[0]:X} (0xB7=AArch64)")

# quick string scan of classes.dex for package + SDKs
import re
dex = os.path.join(base, "classes.dex")
data = open(dex, "rb").read()
strings = re.findall(rb"[\x20-\x7e]{6,}", data)
keys = ["fragon", "chunbai", "prishen", "MainActivity", "UnityPlayer", "facebook",
        "bugly", "protobuf", "protocol", "Socket", "gateway", "/api/", "com.", "google"]
seen = {}
for s in strings:
    t = s.decode("ascii", "ignore")
    for k in keys:
        if k.lower() in t.lower() and k not in seen:
            seen[k] = t
print("\nclasses.dex notable strings:")
for k in keys:
    if k in seen:
        print(f"  [{k:10}] {seen[k][:90]}")
