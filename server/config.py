"""Shared config for the Magic Legion private server (portal + gate)."""
import os, json

# IP the Android emulator uses to reach THIS machine.
# LDPlayer (VirtualBox NAT) -> the host is reachable at 10.0.2.2.
HOST_IP = os.environ.get("ML_HOST_IP", "10.0.2.2")

# Ports the client dials. With the repackaged APK we point it at plain HTTP (no TLS/CA),
# so portal serves http on the portal (9004) + account (80) ports.
TLS_PORTS   = []            # (TLS unused in the repackage approach)
PLAIN_PORTS = [9004, 80]    # android.*:9004 + account.* :80, served as http
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
