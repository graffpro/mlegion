"""
Magic Legion — END-TO-END SERVER PROOF  (login -> enter the game world).

The original client can't render its UI (its CDN art died with the publisher), so we prove
the *revived server* works the way the real client would have driven it: a test client opens
a real TCP socket to the gate brain and walks the full cb_net handshake from
protocol/LOGIN_FLOW.md —

    tcp_connect -> version -> auth -> character list -> join character ->
    init flood -> init finish -> join world -> role_join_map  (= standing in the world)

Both ends speak the exact 1630-message wire codec (server/codec.py) and the server replies
with the very same logic the live gate uses (server/handshake.py — gate.py calls handshake.handle).
If the client reaches role_join_map_s2c, the server is functional end to end.

Run:  python server/test_login.py
"""
import asyncio
import os
import codec
import handshake

SCHEMA = codec.Schema()
HOST, PORT = "127.0.0.1", 9300
# Set ML_GATE=host:port to drive the REAL gate.py instead of the inline brain.
EXT_GATE = os.environ.get("ML_GATE")


# ─────────────────── SERVER: the revived gate brain on a socket ───────────────────
async def serve_client(reader, writer):
    sess = handshake.Session()
    buf = b""
    while True:
        data = await reader.read(4096)
        if not data:
            break
        buf += data
        frames, consumed = SCHEMA.read_frames(buf)
        buf = buf[consumed:]
        for mid, name, body in frames:
            _, fields = SCHEMA.decode_body(mid, body)
            tag = fields if len(str(fields)) < 64 else f"<{len(body)}B>"
            print(f"        server  <= C2S  {name:<26}({mid}) {tag}")
            resps = handshake.handle(name, fields, sess)
            for rn, rv in resps:
                writer.write(SCHEMA.frame(rn, rv))
                print(f"        server  => S2C  {rn}")
            await writer.drain()


# ─────────────────── CLIENT: stands in for the (lost-UI) game client ───────────────────
def c2s(name, **overrides):
    """Build a schema-correct c2s body (zeroed) and override the fields we care about."""
    vals = handshake.default_values(name)
    vals.update({k: v for k, v in overrides.items() if k in vals})
    return name, vals


async def run_client(seen):
    reader, writer = await asyncio.open_connection(HOST, PORT)
    roleid = handshake.DEMO_ROLE["roleid"]
    flow = [
        c2s("tcp_connect_c2s", conn_type=1, account="revival_hero", key="k", sign="s", sn=1),
        c2s("server_version_c2s"),
        c2s("user_auth_c2s"),
        c2s("role_join_game_c2s", roleid=roleid, mac_address="00:11:22:33:44:55"),
        c2s("init_module_c2s"),
        c2s("role_join_world_c2s"),
        # ── Phase 4: in-world play session ──
        c2s("role_move_c2s", time=100, posx=10, posy=10, targetx=24, targety=31),
        c2s("chat_check_rolename_c2s", rolename="RevivalHero"),
        c2s("user_request_info_c2s", sn=7),
        c2s("heart_beat_c2s", time=12345),
    ]
    for name, vals in flow:
        writer.write(SCHEMA.frame(name, vals))
        print(f"client  -> {name}")
    await writer.drain()

    buf = b""
    try:
        while "heart_beat_s2c" not in seen:
            data = await asyncio.wait_for(reader.read(4096), timeout=4)
            if not data:
                break
            buf += data
            frames, consumed = SCHEMA.read_frames(buf)
            buf = buf[consumed:]
            for mid, name, body in frames:
                _, fields = SCHEMA.decode_body(mid, body)
                seen[name] = fields
                print(f"client  <-                                   {name}")
    except asyncio.TimeoutError:
        pass
    writer.close()


async def main():
    print("=" * 74)
    print("  MAGIC LEGION — END-TO-END SERVER PROOF  (login -> enter the world)")
    print("=" * 74)
    global HOST, PORT
    server = None
    if EXT_GATE:
        HOST, PORT = EXT_GATE.rsplit(":", 1)[0], int(EXT_GATE.rsplit(":", 1)[1])
        print(f"  driving the REAL gate.py at {HOST}:{PORT}\n")
    else:
        server = await asyncio.start_server(serve_client, HOST, PORT)
        asyncio.ensure_future(server.serve_forever())
        await asyncio.sleep(0.2)
        print(f"  revived gate (inline brain) listening on {HOST}:{PORT}\n")

    seen = {}
    await run_client(seen)

    checkpoints = [
        ("tcp_connect_success_s2c",    "TCP gate accepted the connection"),
        ("server_version_s2c",         "server version negotiated"),
        ("user_auth_succese_s2c",      "account authenticated"),
        ("player_role_list_s2c",       "character list delivered"),
        ("role_join_game_success_s2c", "character joined the game"),
        ("init_role_info_s2c",         "role attributes streamed"),
        ("init_role_finish_s2c",       "world-state init finished"),
        ("role_join_map_s2c",          "standing in the game world"),
        ("role_move_s2c",              "moved in the world (Phase 4)"),
        ("chat_check_rolename_res_s2c","name-check answered (Phase 4)"),
        ("user_request_info_s2c",      "reliability re-request answered (Phase 4)"),
        ("heart_beat_s2c",             "heartbeat / keepalive answered"),
    ]
    print("\n" + "=" * 74)
    print("  RESULT")
    print("=" * 74)
    ok = 0
    for name, desc in checkpoints:
        hit = name in seen
        ok += hit
        print(f"   [{'OK' if hit else '!!'}]  {desc:<40} ({name})")
    inits = sorted(n for n in seen if n.endswith("_init_s2c"))
    print(f"   [{'OK' if len(inits) >= 20 else '..'}]  full init flood: "
          f"{len(inits)} module-init messages streamed")
    world = "role_join_map_s2c" in seen
    played = world and "role_move_s2c" in seen
    print("-" * 74)
    if played:
        m = seen["role_join_map_s2c"]
        print(f"   {ok}/{len(checkpoints)} checkpoints passed, {len(inits)} modules initialised.")
        print(f"   *** SERVER PROVEN — login -> world -> in-world play: "
              f"map={m.get('mapid')}, moved to ({seen['role_move_s2c'].get('targetx')},"
              f"{seen['role_move_s2c'].get('targety')}) ***")
    elif world:
        print(f"   {ok}/{len(checkpoints)} — reached the world but a Phase-4 step failed.")
    else:
        print(f"   {ok}/{len(checkpoints)} — did not reach the world (see log above).")
    if server is not None:
        server.close()


if __name__ == "__main__":
    asyncio.run(main())
