# Magic Legion – Hero Legend — Reverse Engineering Findings

_Workspace: `C:\Users\NoteBook\Documents\magic-legion`_
_APK analyzed: `Magic Legion - Hero Legend_2.0.1.4_APKPure.apk` (102 MB)_

## 1. Game identity (confirmed)

| Field | Value |
|-------|-------|
| Package ID | `com.xgg.ml` (studio "XGG") |
| Title | Magic Legion – Hero Legend (a.k.a. "Age of Heroes", JP: マジック・リージャン－巨竜戦争) |
| Genre | Online **hero-collector RPG** (heroes, skills, PvP arena, guild wars, dungeons) — **server-authoritative** |
| Original dev infra | `chunbaigame.com`, `xy8` platform, `prishen.com` CDN → studio prefix **CB / cb_net = ChunBai (春百)** |
| Int'l publisher | **Fragon Game** (`*.ml.fragon.com`) |
| Released | ~2017; final update **v2.0.1.4** (Sept 2020); servers now **dead/delisted** |
| Prior art | **NONE.** No private server, emulator, packet capture, or protocol docs exist anywhere (verified). We build from zero. |

## 2. Backend topology (from `assets/config.ini`)

**Hosts:**
- `android.ml.fragon.com:9004` — main HTTP API (channel/center)
- `account.ml.fragon.com` — account/auth server
- `push.ml.fragon.com`, `translate.ml.fragon.com` — aux
- `op-cdn.prishen.com` / akamai — resource CDN

**HTTP API endpoints (port 9004 https):**
```
/api/channel/version/show                         version check
/api/center/serverlist/show?platform=googleplay   server list
/api/channel/notice/show                           announcements
/api/channel/serverlistwithrole/show               servers where you have a role
/api/center/server/get_last_server                 last selected server
/api/center/server/update-account-last-info        record server selection
/api/channel/gameswitch/getgatev2   *** returns the realtime GAME GATEWAY (ip:port) ***
/api/channel/gameswitch/cdn                        cdn switch
/api/channel/gameswitch/market | /bundle           feature switches
/api/channel/checklan/do | /checkaccountswitch/do  misc gates
/api/channel/invit/get                             invite codes
/api/center/advise/show                            GM mailbox
```
The HTTP layer is the **portal**: it gates updates/login and hands the client the TCP game-server address via `getgatev2`.

## 3. Engine & how we recovered the code

- **Unity + IL2CPP**, native `libil2cpp.so` (arm64 47.8 MB / armv7 39 MB) + `libunity.so`.
- `global-metadata.dat`: **magic `0xFAB11BAF`, version 24 — UNENCRYPTED** (Unity 5.6/2017 era).
- Dumped with **Il2CppDumper** → `analysis/dump/`:
  - `dump.cs` (14 MB) — **all classes/methods/fields, original names intact**
  - `il2cpp.h`, `script.json` (for Ghidra/IDA), `stringliteral.json`
- No Lua: game logic is entirely in IL2CPP C#. Assets are Unity AssetBundles (`ui_*`, `fx_*`, `unit_*` = hero models w/ pinyin names: `damofashi`=archmage, `jiqiren`=robot, `kapai`=card…).

## 4. Network protocol (namespace `cb_net`, lib `CBNetLib`)

**Transport:** custom **TCP binary protocol**, two connections:
- **NorTcp** — normal game server (main gameplay)
- **PvpTcp** — separate PvP server

**`NetWorkManager : BaseManager<NetWorkManager>`** (`dump.cs:239439`):
- `NorTcpConnect(ip, port)` / `PvpTcpConnect(ip, port)`
- `SendMsg(base_message msg, bool isLock, bool needKey=true)` — **`needKey` ⇒ encryption** (likely RC4; `ARC4Managed:RC4` present in binary)
- dispatch by opcode: `AddHandler(uint msgId, NetMsgHandler, uint[] msgIdList)`
- `m_tcpSn` serial numbers; `HEART_BEAT_TIME = 30000` (30 s heartbeat)
- handshake primitives: `recv_tcp_connect_success_s2c`, `recv_tcp_serial_number_s2c`, `recv_heart_beat_s2c`, `recv_tcp_server_disconnect_s2c`

**`base_message`** (`dump.cs:242914`):
```csharp
public class base_message {
    public uint msgid;
    public virtual bool encode(PacketStream pack);   // serialize fields in declaration order
    public virtual bool decode(PacketStream pack);   // deserialize
    public PacketStream toPacket();  public byte[] toByteArray();
}
```
- **1,630 subclasses** = the full protocol catalog. Each has `const uint MSG_ID = N` + typed fields, e.g.:
  - `batch_item_c2s` MSG_ID=163 `{ sitem[] itmes; long heroid; }`
  - `batch_delete_item_s2c` MSG_ID=167 `{ long[] itemids; int reason; }`
- `_c2s` = client→server, `_s2c` = server→client.

**`PacketStream`** (`dump.cs:288812`) — the codec, over .NET `BinaryReader/Writer` (little-endian):
- scalars: `readByte/Boolean`, `readShort/UnsignedShort`, `readInt/UnsignedInt`, `readInt64/UnsignedInt64`, `readFloat`, `readDouble`
- `readUTF()` length-prefixed string; `readUTFBytes(len)` fixed
- **count-prefixed lists**: `readInt8/16/32/64List`, `readUint16/32List`, `readStringList`, `readBooleanList`
- tuples: `Pair<T>` (readPair8/16/32/64), `Ternary<T>`
- framing: `wirteAtHeader(ushort packsize)` ⇒ **packet = `[ushort length][...]`**

## 5. Open questions (to confirm in Phase 1)

1. **Exact frame header**: byte order of length; placement of `msgid` and serial number `sn` (in frame header vs. body). → read `CSocket`/`SocketBase` encode path + a couple of `encode()` bodies in Ghidra using `script.json`.
2. **Encryption (`needKey`)**: cipher (RC4?), key source, which messages are keyed, whether a key-exchange happens at connect.
3. **Login path**: `account.ml.fragon.com` token/signature scheme + the first `*_c2s` login message + role/server selection flow.
4. **`readUTF` endianness** (Java-style BE length vs .NET LE) — verify against binary.

## 6. Toolchain present
Python 3.13, Node.js, .NET 8 + .NET Framework 4.8, git, Il2CppDumper. (Ghidra/jadx optional, add if needed.)
