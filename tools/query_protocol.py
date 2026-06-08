"""Explore the extracted protocol: system range + critical-path (login/role/enter)."""
import json, os, re

ROOT = r"C:\Users\NoteBook\Documents\magic-legion"
data = json.load(open(os.path.join(ROOT, "protocol", "messages.json"), encoding="utf-8"))
msgs = data["messages"]
structs = {s["name"]: s for s in data["structs"]}
by_id = {m["msg_id"]: m for m in msgs}
OUT = open(os.path.join(ROOT, "protocol", "critical_path.txt"), "w", encoding="utf-8")
def out(*a): print(*a, file=OUT)

def fmt(m):
    fields = ", ".join(f"{f['type']} {f['name']}" for f in m["fields"]) or "(empty)"
    return f"  [{m['msg_id']:>4}] {m['name']:<42} {m['direction']:<4} {{ {fields} }}"

out("=" * 100)
out("SYSTEM / HANDSHAKE RANGE  (msg_id < 40)")
out("=" * 100)
for mid in sorted(k for k in by_id if k is not None and k < 40):
    out(fmt(by_id[mid]))

KEYS = ["login", "role", "server", "enter", "create", "account", "gate",
        "connect", "heart", "serial", "reconnect", "user_request", "init",
        "select", "guest", "register", "token", "session", "auth", "verify"]
out("\n" + "=" * 100)
out("CRITICAL-PATH MESSAGES  (name matches login/role/enter/etc.)")
out("=" * 100)
seen = set()
for k in KEYS:
    hits = [m for m in msgs if k in m["name"].lower() and m["name"] not in seen]
    if not hits:
        continue
    out(f"\n### '{k}'  ({len(hits)})")
    for m in sorted(hits, key=lambda x: (x["msg_id"] or 0)):
        out(fmt(m)); seen.add(m["name"])

# show the structs most relevant to login/role
out("\n" + "=" * 100)
out("KEY STRUCTS")
out("=" * 100)
for sn in ["display_role", "rw", "kvobject", "sitem"]:
    if sn in structs:
        fields = ", ".join(f"{f['type']} {f['name']}" for f in structs[sn]["fields"])
        out(f"  {sn:<16} {{ {fields} }}")

OUT.close()
print("wrote protocol/critical_path.txt")
