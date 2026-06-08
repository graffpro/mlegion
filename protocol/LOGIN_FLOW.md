# Magic Legion — reconstructed login / enter-world flow

Recovered entirely from the `cb_net` message catalog (msg_id < 40 = system range).
This is the exact sequence the server must drive for Phase 3.

## A. HTTP portal (before any TCP)
1. `version/show` → client checks it's up to date.
2. `serverlist/show` / `serverlistwithrole/show` → client shows server picker.
3. `gameswitch/getgatev2` → **returns the TCP game-gate `ip:port`** the client dials next.
4. (`account.ml.fragon.com` issues the account/`key`/`sign` used below.)

## B. TCP gate handshake (CBNetLib binary protocol)
Frame (to confirm empirically): `[ushort length][uint msgid][body…]`, little-endian,
`readUTF` = length-prefixed string, lists = count-prefixed. Heartbeat every 30 s.

| # | msg_id | name | dir | body |
|---|--------|------|-----|------|
| 1 | 42 | `tcp_connect_c2s` | C→S | `byte conn_type, long roleid, string account, string key, string sign, uint sn` |
| 2 | 43 | `tcp_connect_success_s2c` | S→C | `byte conn_type` |
|   | 40 | `tcp_connect_s2c` (redirect) | S→C | `string server_ip, ushort server_port, byte conn_type` |
| 3 | 2 | `server_version_c2s` | C→S | *(empty)* |
| 4 | 3 | `server_version_s2c` | S→C | `string v` |
| 5 | 4 | `user_auth_c2s` | C→S | `kvobject[] elems` (account, token, device…) |
| 6 | 15 | `user_auth_succese_s2c` | S→C | `string authkey, string account, string session` |
|   | 5 | `user_auth_fail_s2c` | S→C | `int reasonid` |
| 7 | 14 | `player_role_list_s2c` | S→C | `r[] roles` (the account's characters) |
| 8a | 8 | `create_role_request_c2s` | C→S | `string name, int classtype` |
| 8b | 6 | `random_create_role_c2s` | C→S | `int classtype` → `random_create_role_s2c{classtype,name}` |
| 9 | 17 | `create_role_succese_s2c` | S→C | `long roleid` |
|   | 9 | `create_role_failed_s2c` | S→C | `int errno` |
| 10 | 12 | `role_join_game_c2s` | C→S | `long roleid, string mac_address` |
| 11 | 32 | `role_join_game_success_s2c` | S→C | *(empty)* |
|   | 13 | `role_join_game_failed_s2c` | S→C | `int errno` |
| 12 | 16 | `init_role_info_s2c` | S→C | `o role_attr` (the role's attribute blob) |
| 13 | 18 | `init_module_c2s` | C→S | *(empty)* — "send me everything" |
| 14 | — | **~171 `*_init_s2c` messages** | S→C | full state: `hero_init`(701), `init_onhands_item`(152), `vip_init`(482), `mail_info_init`(502), `init_friend`(542), `arena_init`(1232), `guild_init`(1402), `quest_list_init`(354)… |
| 15 | 33 | `init_role_finish_s2c` | S→C | `byte is_new_role, byte is_plot_script` — handshake done |
| 16 | 306 | `role_join_world_c2s` | C→S | *(empty)* |
| 17 | 81 | `role_join_map_s2c` | S→C | `int mapid, byte battle_faction` — **in the world** |

### Reliability / keepalive layer
- `heart_beat_c2s`(46)`{uint time}` ↔ `heart_beat_s2c`(47)`{uint time, uint stime}` every 30 s.
- `tcp_serial_number_s2c`(22)/`_ack_c2s`(23); `user_request_info_c2s`(19)`{account,key,sign,sn}`.
- `user_reconnect_c2s`(25)`{long roleid, string key}` for drops.

### Anti-tamper note
`account / key / sign / sn` appear in connect + request messages. `sign` is a request
signature. **We own the server → we can accept any `sign`** (skip verification) for a private
server; only need to replicate it if a check is server-mandated. Confirm during Phase 3.

## C. Minimum server to reach the world (Phase 3 MVP)
Implement handlers for: 42→43, 2→3, 4→15, send 14, accept 8/6→17, 12→32, send 16,
18→(minimal init set)→33, 306→81. Everything else can be stubbed/empty until Phase 4.
