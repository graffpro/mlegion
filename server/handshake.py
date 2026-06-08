"""
Phase 3 (DRAFT) — login-handshake responder.

Pure logic: given an incoming (name, fields), return the list of (response_name, values)
the server should send to drive the client from TCP-connect into the game world, per
protocol/LOGIN_FLOW.md. No sockets here, so it's unit-testable and reusable by gate.py
once the wire framing is confirmed from a live capture.

Confidence:
  * version / connect / auth / role-list / create / join / heartbeat  -> simple types, solid.
  * init flood (role attributes via kvobject's polymorphic `object` value) -> CONFIRMED from
    the client's real user_auth_c2s packet; until then we send an attribute-light role.
"""
import config, codec

SCHEMA = codec.Schema()

# A demo character so we can log straight in (single-player revival to start).
DEMO_ROLE = {"roleid": 10001, "name": "Hero", "protoid": 1, "level": 1, "vip": 0}


class Session:
    def __init__(self):
        self.account = None
        self.roleid = None
        self.joined = False


def default_values(msg_name):
    """Build a zeroed value dict for a message/struct from the schema (for empty inits)."""
    def dv(typ):
        if typ.endswith("[]"):
            return []
        if typ.startswith("Pair<") or typ.startswith("Ternary<"):
            base = typ[typ.index("<") + 1:-1]
            return [dv(base)] * (2 if typ.startswith("Pair") else 3)
        if typ in codec.PRIM:
            return 0
        if typ == "string":
            return ""
        if typ in SCHEMA.structs:
            return {f["name"]: dv(f["type"]) for f in SCHEMA.structs[typ]}
        return 0  # 'object' etc. — only reached if the message carries kvobject (skip those)
    m = SCHEMA.by_name[msg_name]
    return {f["name"]: dv(f["type"]) for f in m["fields"]}


def _role_attr(roleid):
    # o { long objectid, kvobject[] attrs } — attrs left empty until the kvobject wire
    # encoding is confirmed from the real user_auth_c2s capture (count=0 needs no `object`).
    return {"objectid": roleid, "attrs": []}


def _init_flood():
    """Minimal init set the client gets on init_module_c2s. Empty/default contents; the real
    required set + values come from capture iteration. Only includes inits with no kvobject."""
    names = ["hero_init_s2c", "init_onhands_item_s2c", "skill_init_s2c",
             "field_init_s2c", "quest_list_init_s2c", "vip_init_s2c",
             "mail_info_init_s2c", "init_friend_s2c", "arena_init_s2c"]
    flood = []
    for n in names:
        if n not in SCHEMA.by_name:
            continue
        if _has_object(n):
            continue  # skip kvobject-bearing inits until the scheme is confirmed
        flood.append((n, default_values(n)))
    return flood


def _has_object(msg_name, _seen=None):
    _seen = _seen or set()
    for f in SCHEMA.by_name.get(msg_name, SCHEMA.structs.get(msg_name, {"fields": []}))["fields"] \
            if msg_name in SCHEMA.by_name else SCHEMA.structs.get(msg_name, []):
        t = f["type"].rstrip("[]")
        if t == "object" or t == "kvobject":
            return True
        if t in SCHEMA.structs and t not in _seen:
            _seen.add(t)
            if _has_object(t, _seen):
                return True
    return False


def handle(name, fields, sess):
    """Return [(response_name, values), ...] for an incoming message."""
    f = fields or {}
    if name == "server_version_c2s":
        return [("server_version_s2c", {"v": config.CLIENT_VERSION})]
    if name == "tcp_connect_c2s":
        sess.account = f.get("account")
        return [("tcp_connect_success_s2c", {"conn_type": f.get("conn_type", 0)})]
    if name == "user_auth_c2s":
        sess.account = sess.account or "guest_1"
        return [("user_auth_succese_s2c",
                 {"authkey": "devauth", "account": sess.account, "session": "devsess"}),
                ("player_role_list_s2c", {"roles": [DEMO_ROLE]})]
    if name in ("create_role_request_c2s", "random_create_role_c2s"):
        sess.roleid = DEMO_ROLE["roleid"]
        return [("create_role_succese_s2c", {"roleid": DEMO_ROLE["roleid"]})]
    if name == "role_join_game_c2s":
        sess.roleid = f.get("roleid", DEMO_ROLE["roleid"]); sess.joined = True
        return [("role_join_game_success_s2c", {}),
                ("init_role_info_s2c", {"role_attr": _role_attr(sess.roleid)})]
    if name == "init_module_c2s":
        return _init_flood() + [("init_role_finish_s2c",
                                 {"is_new_role": 1, "is_plot_script": 0})]
    if name == "role_join_world_c2s":
        return [("role_join_map_s2c", {"mapid": 1, "battle_faction": 0})]
    if name == "heart_beat_c2s":
        t = f.get("time", 0)
        return [("heart_beat_s2c", {"time": t, "stime": t})]
    return []  # unhandled -> caller logs it (drives Phase 4)


if __name__ == "__main__":
    # Drive the canonical flow and assert every response actually encodes via the codec.
    sess = Session()
    flow = [
        ("server_version_c2s", {}),
        ("tcp_connect_c2s", {"conn_type": 1, "roleid": 0, "account": "g", "key": "k",
                             "sign": "s", "sn": 1}),
        ("user_auth_c2s", {"elems": []}),
        ("role_join_game_c2s", {"roleid": 10001, "mac_address": "aa"}),
        ("init_module_c2s", {}),
        ("role_join_world_c2s", {}),
        ("heart_beat_c2s", {"time": 123}),
    ]
    total = 0
    for name, fields in flow:
        resps = handle(name, fields, sess)
        for rn, rv in resps:
            frame = SCHEMA.frame(rn, rv)   # raises if not encodable
            total += 1
            print(f"  {name:<24} -> {rn:<26} {len(frame):>3}B  {rv if len(str(rv))<60 else '…'}")
    print(f"HANDSHAKE-SELFTEST: {total} responses, all encodable  OK")
