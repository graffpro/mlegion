#!/usr/bin/env python3
"""
One-click demo of the revived *Magic Legion: Hero Legend* server.

Starts the deployable TCP game gate and drives a test client across a real socket through a
full session:  login -> enter world -> walk -> battle (+level) -> walk -> heartbeat.

    python run.py

No client, APK, or assets required — the recovered protocol (protocol/messages.json) and the
server logic (server/) are all that's needed to prove the revived server works end to end.
"""
import os
import sys
import time
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(ROOT, "server")
PORT = "9300"
LOG = os.path.join(SERVER, "_gate_demo.log")


def main():
    print("=" * 70)
    print("  MAGIC LEGION — revived private server : live demo")
    print("=" * 70)
    print("  starting the deployable TCP gate on 127.0.0.1:%s (ML_RESPOND=1) ...\n" % PORT)
    env = dict(os.environ, ML_RESPOND="1", ML_GATE_BIND=PORT, ML_HOST_IP="127.0.0.1")
    with open(LOG, "w") as logf:
        gate = subprocess.Popen([sys.executable, "-u", "gate.py"], cwd=SERVER, env=env,
                                stdout=logf, stderr=subprocess.STDOUT, text=True)
        try:
            time.sleep(1.5)
            env2 = dict(os.environ, ML_GATE="127.0.0.1:" + PORT)
            rc = subprocess.call([sys.executable, "test_login.py"], cwd=SERVER, env=env2)
        finally:
            gate.terminate()
            try:
                gate.wait(timeout=3)
            except Exception:
                gate.kill()

    try:
        lines = open(LOG, encoding="utf-8", errors="replace").read().splitlines()
        framing = next((ln for ln in lines if "DETECTED FRAMING" in ln), None)
        s2c = sum(1 for ln in lines if ln.strip().startswith("<<"))
        print("\n  gate side: " + (framing.strip() if framing else "(framing not captured)"))
        print("  the live gate sent %d s2c messages to drive that whole session." % s2c)
    except Exception:
        pass
    print("=" * 70)
    return rc


if __name__ == "__main__":
    sys.exit(main())
