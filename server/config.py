"""Shared config for the Magic Legion private server (portal + gate)."""
import os, json

# IP the Android emulator uses to reach THIS machine.
# LDPlayer (VirtualBox NAT) -> the host is reachable at 10.0.2.2.
HOST_IP = os.environ.get("ML_HOST_IP", "10.0.2.2")

# Ports the client dials. With the repackaged APK we point it at plain HTTP (no TLS/CA).
TLS_PORTS   = []            # (TLS unused in the repackage approach)
# GATE_PORT is the ADVERTISED (guest-side) port — it appears in svrip/svrport and is what
# the client dials inside the emulator. The APK config URLs likewise hardcode :9004.
GATE_PORT   = 9100
# Host BIND ports. Normally identical to the advertised/guest ports, but when a stale
# *elevated* portal/gate from a previous session squats 9004/9100 (and our non-admin
# context can't kill it), we bind elsewhere and `adb reverse tcp:9004 tcp:<bind>` so the
# guest's advertised port still tunnels into THIS (fresh-config) server.
PORTAL_BIND = int(os.environ.get("ML_PORTAL_BIND", "9004"))
GATE_BIND   = int(os.environ.get("ML_GATE_BIND", str(GATE_PORT)))
PLAIN_PORTS = [PORTAL_BIND]

CERT_DIR   = os.path.join(os.path.dirname(__file__), "certs")
SERVER_CRT = os.path.join(CERT_DIR, "server.crt")
SERVER_KEY = os.path.join(CERT_DIR, "server.key")

CLIENT_VERSION = "2.0.1.4"

# One server entry we advertise to the client.
# The Java publisher SDK reads svrip/svrport (confirmed in classes.dex); the Unity
# ServerZoneVO maps serverID/serverName/serverPort/serverState/serverDomain/
# uniqueServerid/serverPlatform. We provide the full superset so both layers populate.
SERVER = {
    # --- Java SDK keys (it threw "No value for svrip" without these) ---
    "svrip": HOST_IP,
    "svrport": GATE_PORT,
    "svrid": 1,
    "svrname": "Revival S1",
    "svrstate": 1,
    # --- Unity ServerZoneVO field-mapped keys ---
    "serverPlatform": "googleplay",
    "serverDomain": HOST_IP,
    "serverDomain1": HOST_IP,
    "serverDomain2": HOST_IP,
    "serverID": "1",
    "serverName": "Revival S1",
    "serverPort": str(GATE_PORT),
    "serverState": 1,
    "serverInfo": "",
    "uniqueServerid": "ml_s1",
    "maintained_str": "",
    # --- generic aliases (harmless if unread) ---
    "id": 1, "sid": 1, "name": "Revival S1", "state": 1, "status": 1,
    "ip": HOST_IP, "port": GATE_PORT,
    "serverid": "1", "uniqueserverid": "ml_s1", "servername": "Revival S1",
    "game_ip": HOST_IP, "game_port": GATE_PORT,
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
