"""Shared config for the Magic Legion private server (portal + gate)."""
import os, json

# IP the Android emulator/device uses to reach THIS machine.
# LDPlayer/real device on same LAN -> your Windows LAN IP (confirm with ipconfig).
HOST_IP = os.environ.get("ML_HOST_IP", "192.168.50.180")

# Ports the client dials (per assets/config.ini). The client uses https:// for the
# portal + account hosts, so those are served over TLS (cert from gen_certs.py).
TLS_PORTS   = [9004, 443]   # android.ml.fragon.com:9004 + account.ml.fragon.com:443
PLAIN_PORTS = [80]          # plain-http fallback
GATE_PORT   = 9100          # our realtime TCP game gate (we advertise this)

CERT_DIR   = os.path.join(os.path.dirname(__file__), "certs")
SERVER_CRT = os.path.join(CERT_DIR, "server.crt")
SERVER_KEY = os.path.join(CERT_DIR, "server.key")

CLIENT_VERSION = "2.0.1.4"

# One server entry we advertise to the client.
SERVER = {
    "serverid": "1",
    "uniqueserverid": "ml_s1",
    "servername": "Revival S1",
    "game_ip": HOST_IP,
    "game_port": GATE_PORT,
    "status": 1,   # online
    "state": 1,
}

# Load the extracted protocol so the gate can label packets by msgid.
_PROTO = os.path.join(os.path.dirname(__file__), "..", "protocol", "messages.json")

def load_msgid_names():
    try:
        data = json.load(open(_PROTO, encoding="utf-8"))
        return {m["msg_id"]: m["name"] for m in data["messages"] if m["msg_id"] is not None}
    except Exception as e:
        print("warn: could not load protocol/messages.json:", e)
        return {}
