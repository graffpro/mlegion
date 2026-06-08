"""
Phase 1 — Protocol extractor.

Parses Il2CppDumper's dump.cs and extracts the full cb_net protocol:
  * every `: base_message` subclass  -> name, MSG_ID, ordered fields, direction
  * every custom struct used as a field type (recursively) -> its fields
  * relevant enums (LoginType, etc.)

Output: protocol/messages.json  (machine-readable schema for the codec + server)
"""
import re, json, os, collections

ROOT = r"C:\Users\NoteBook\Documents\magic-legion"
DUMP = os.path.join(ROOT, "analysis", "dump", "dump.cs")
OUTDIR = os.path.join(ROOT, "protocol")
os.makedirs(OUTDIR, exist_ok=True)

PRIMITIVES = {
    "bool", "byte", "sbyte", "char", "short", "ushort", "int", "uint",
    "long", "ulong", "float", "double", "string", "object",
}

# class declaration:  [modifiers] class NAME [: BASE1, BASE2]  // TypeDefIndex: N
RE_CLASS = re.compile(
    r"^(?P<mods>(?:public |private |protected |internal |sealed |abstract |static )*)"
    r"(?P<kind>class|struct|enum)\s+(?P<name>[\w.<>`]+)"
    r"(?:\s*:\s*(?P<bases>[^/]+?))?\s*//\s*TypeDefIndex"
)
# field:  [attr] modifiers TYPE NAME [= VALUE];   // 0xNN  (offset comment optional)
RE_FIELD = re.compile(
    r"^\s+(?:\[[^\]]*\]\s*)*"
    r"(?P<mods>(?:public|private|protected|internal)\s+(?:const\s+|static\s+|readonly\s+)*)"
    r"(?P<type>[\w.<>\[\],`]+)\s+(?P<name>[\w<>$.]+)\s*(?:=\s*(?P<value>[^;]+?))?\s*;"
)


def parse_dump(path):
    classes = {}            # name -> dict
    cur_ns = ""
    cur = None
    section = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("// Namespace:"):
                cur_ns = line[len("// Namespace:"):].strip()
                continue
            m = RE_CLASS.match(line)
            if m:
                # close previous (defensive)
                if cur:
                    classes[cur["name"]] = cur
                bases = []
                if m.group("bases"):
                    bases = [b.strip() for b in m.group("bases").split(",")]
                cur = {
                    "name": m.group("name"),
                    "namespace": cur_ns,
                    "kind": m.group("kind"),
                    "bases": bases,
                    "fields": [],      # [(type, name)]
                    "consts": {},      # name -> value
                }
                section = None
                continue
            if cur is None:
                continue
            if line == "}":            # column-0 brace closes the type
                classes[cur["name"]] = cur
                cur = None
                section = None
                continue
            if "// Fields" in line:
                section = "fields"; continue
            if "// Methods" in line or "// Properties" in line:
                section = None; continue
            if section == "fields":
                fm = RE_FIELD.match(line)
                if not fm:
                    continue
                name = fm.group("name")
                if name.startswith("<") or "$" in name:   # compiler-generated
                    continue
                mods = fm.group("mods")
                typ = fm.group("type")
                if "const" in mods:
                    cur["consts"][name] = (fm.group("value") or "").strip()
                elif "static" in mods:
                    continue   # statics aren't part of wire layout
                else:
                    cur["fields"].append((typ, name))
    if cur:
        classes[cur["name"]] = cur
    return classes


def base_type(t):
    """strip [] and generic wrappers to the underlying named type(s)."""
    out = []
    t = t.strip()
    arr = t.endswith("[]")
    core = t[:-2] if arr else t
    gen = re.match(r"^([\w.`]+)<(.+)>$", core)
    if gen:
        out.append(gen.group(1).split("`")[0])
        # generic args may themselves be custom
        depth = 0; cur = ""
        for ch in gen.group(2):
            if ch == "<": depth += 1
            if ch == ">": depth -= 1
            if ch == "," and depth == 0:
                out.append(cur); cur = ""
            else:
                cur += ch
        if cur: out.append(cur)
    else:
        out.append(core)
    return [x.strip().split("`")[0] for x in out]


def main():
    classes = parse_dump(DUMP)
    print(f"parsed {len(classes)} types from dump.cs")

    messages = {n: c for n, c in classes.items() if "base_message" in c["bases"]}
    print(f"found {len(messages)} base_message subclasses")

    # collect custom (non-primitive) types referenced by messages, recursively
    needed = set()
    def collect(typename):
        for bt in base_type(typename):
            if bt in PRIMITIVES or bt in needed:
                continue
            if bt in classes and "base_message" not in classes[bt]["bases"]:
                needed.add(bt)
                for ft, fn in classes[bt]["fields"]:
                    collect(ft)
    for c in messages.values():
        for ft, fn in c["fields"]:
            collect(ft)

    def direction(name):
        if name.endswith("_c2s"): return "c2s"
        if name.endswith("_s2c"): return "s2c"
        return "other"

    msg_out = []
    bad_id = 0
    for n, c in sorted(messages.items()):
        mid = c["consts"].get("MSG_ID")
        try:
            mid_int = int(mid)
        except (TypeError, ValueError):
            mid_int = None; bad_id += 1
        msg_out.append({
            "name": n,
            "msg_id": mid_int,
            "direction": direction(n),
            "fields": [{"type": t, "name": fn} for t, fn in c["fields"]],
        })

    struct_out = []
    for n in sorted(needed):
        c = classes[n]
        struct_out.append({
            "name": n,
            "fields": [{"type": t, "name": fn} for t, fn in c["fields"]],
        })

    # stats
    by_dir = collections.Counter(m["direction"] for m in msg_out)
    ids = [m["msg_id"] for m in msg_out if m["msg_id"] is not None]
    dup_ids = [i for i, c in collections.Counter(ids).items() if c > 1]

    result = {
        "meta": {
            "messages": len(msg_out),
            "structs": len(struct_out),
            "by_direction": dict(by_dir),
            "msg_id_missing": bad_id,
            "msg_id_min": min(ids) if ids else None,
            "msg_id_max": max(ids) if ids else None,
            "msg_id_duplicates": dup_ids[:20],
        },
        "messages": msg_out,
        "structs": struct_out,
    }
    outp = os.path.join(OUTDIR, "messages.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    print(json.dumps(result["meta"], indent=2))
    print("wrote", outp)

    # also dump the set of distinct field types (to validate codec coverage)
    typeset = collections.Counter()
    for m in msg_out:
        for fld in m["fields"]:
            typeset[fld["type"]] += 1
    for s in struct_out:
        for fld in s["fields"]:
            typeset[fld["type"]] += 1
    with open(os.path.join(OUTDIR, "fieldtypes.json"), "w", encoding="utf-8") as f:
        json.dump(typeset.most_common(), f, indent=1, ensure_ascii=False)
    print(f"distinct field types: {len(typeset)} -> protocol/fieldtypes.json")


if __name__ == "__main__":
    main()
