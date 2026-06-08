"""
Magic Legion — HTTP portal (Phase 2).

Emulates android.ml.fragon.com (:9004) + account.ml.fragon.com (:443/:80) so the client
passes version/serverlist/login and is handed our TCP gate. Verbose request logging; the
JSON response shapes are best-guess (typical Chinese-game errno/status envelopes) and get
refined from the client's real parse behavior (watch logcat + the UNHANDLED lines here).

Run:  python server/portal.py     (TLS comes later once we know if the client needs it)
"""
import json, threading, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import config


def log(*a):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][portal]", *a)


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = obj if isinstance(obj, (bytes,)) else \
               obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self, method):
        u = urlparse(self.path)
        path = u.path
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        log(method, self.path, "from", self.client_address[0],
            ("\n    body=" + body.decode("utf-8", "replace")) if body else "")

        # version / update check
        if path.endswith("/version/show"):
            return self._send({"errno": 0, "version": config.CLIENT_VERSION,
                               "url": "", "force": 0, "status": 1})
        # server list
        if path.endswith("/serverlist/show") or path.endswith("/serverlistwithrole/show"):
            return self._send({"errno": 0, "status": 1, "serverlist": [config.SERVER]})
        if path.endswith("/get_last_server"):
            return self._send({"errno": 0, "server": config.SERVER})
        if path.endswith("/update-account-last-info"):
            return self._send({"errno": 0})
        # gate discovery -> hand the client OUR gate
        if path.endswith("/getgatev2") or path.endswith("/getgate") or path.endswith("/cdn"):
            return self._send({"errno": 0, "status": 1, "ip": config.HOST_IP,
                               "gate": [config.HOST_IP], "domains": [config.HOST_IP],
                               "port": config.GATE_PORT})
        # notices
        if path.endswith("/notice/show"):
            return self._send({"errno": 0, "notices": [], "list": []})
        # misc feature switches / gates -> closed/ok
        if any(s in path for s in ("/gameswitch/", "/checklan/", "/checkaccountswitch/",
                                   "/invit/", "/advise/")):
            return self._send({"errno": 0, "status": 1, "open": 0})
        # account / auth (guest)
        if any(s in path for s in ("login", "account", "auth", "register")):
            return self._send({"errno": 0, "code": 0, "account": "guest_1",
                               "token": "devtoken", "session": "devsession",
                               "key": "devkey", "sign": "devsign"})

        log("UNHANDLED", path, "-> default ok envelope")
        return self._send({"errno": 0, "status": 1})

    def do_GET(self):  self._route("GET")
    def do_POST(self): self._route("POST")
    def log_message(self, *a):  # silence stdlib logging; we use our own
        pass


def serve(port):
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as e:
        log(f"!! could not bind port {port}: {e} (skipping)")
        return
    log(f"listening on 0.0.0.0:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    ports = sorted(set(config.PORTAL_PORTS + config.ACCOUNT_PORTS))
    threads = [threading.Thread(target=serve, args=(p,), daemon=True) for p in ports]
    for t in threads:
        t.start()
    log(f"portal up on {ports}; advertising gate at {config.HOST_IP}:{config.GATE_PORT}")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        log("stopped")
