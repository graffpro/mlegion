import zipfile, re
apk=r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
z=zipfile.ZipFile(apk)
S=set()
for d in ["classes.dex","classes2.dex"]:
    data=z.read(d)
    for m in re.finditer(rb"[\x20-\x7e]{2,70}", data):
        S.add(m.group().decode("ascii","ignore"))
svr=sorted(s for s in S if s.startswith("svr") or s.lower().startswith("gateip") or s.lower().startswith("gateport") or s.lower().startswith("gate_") or s in ("svrip","svrport","svrId","svrName","svrState","loginGate"))
print("=== svr*/gate* keys ===")
for s in svr: print(repr(s))
url=sorted(s for s in S if len(s)<80 and (".php" in s.lower() or s.startswith("/api") or s.startswith("/sdk") or s.startswith("/center") or "getserver" in s.lower() or "serverinfo" in s.lower() or "getgate" in s.lower()))
print("\n=== endpoints/urls ===")
for s in url[:60]: print(repr(s))
