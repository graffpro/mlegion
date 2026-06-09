"""
Magic Legion — HTTP portal (Phase 2).

Emulates android.ml.fragon.com (:9004) + account.ml.fragon.com (:443/:80) so the client
passes version/serverlist/login and is handed our TCP gate. Verbose request logging; the
JSON response shapes are best-guess (typical Chinese-game errno/status envelopes) and get
refined from the client's real parse behavior (watch logcat + the UNHANDLED lines here).

Run:  python server/portal.py     (TLS comes later once we know if the client needs it)
"""
import json, threading, datetime, ssl, os, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import config


def log(*a):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][portal]", *a)


# --- CDN asset recovery -----------------------------------------------------
# The original CDN (op-cdn.prishen.com / *.akamaized.net) is permanently dead, and
# this thin APK ships only SOME bundles — the heavily-shared atlases (e.g.
# uiatlas_497bea7e, 75 refs) were CDN-only and are lost. When the client asks our
# portal for one, serve the exact bundled copy if the APK happens to contain it,
# otherwise a same-prefix bundle as a structurally-valid (wrong-texture) stand-in so
# the pre-load coroutine doesn't stall waiting on a bundle that will never arrive.
_APK = os.environ.get("ML_APK",
    r"C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk")
_CDN_FALLBACK = os.environ.get("ML_CDN_FALLBACK", "1") == "1"
try:
    _apk_zip = zipfile.ZipFile(_APK)
    _apk_names = _apk_zip.namelist()
    _apk_set = set(_apk_names)
    _fallback = {}
    for _n in _apk_names:
        _b = _n.rsplit("/", 1)[-1]
        if _b.startswith(("ui_", "uiatlas_", "fx_", "fxatlas_", "unit_", "scene_")):
            _pref = _b.split("_", 1)[0] + "_"
            _fallback.setdefault(_pref, _n)
    log(f"APK loaded: {len(_apk_names)} entries, fallbacks for {list(_fallback)}")
except Exception as _e:
    _apk_zip, _apk_names, _apk_set, _fallback = None, [], set(), {}
    log(f"!! could not open APK for CDN assets: {_e}")


def _cdn_asset(name):
    if not _apk_zip:
        return None
    exact = "assets/" + name
    if exact in _apk_set:
        return _apk_zip.read(exact)
    if not _CDN_FALLBACK:
        return None
    pref = name.split("_", 1)[0] + "_"
    src = _fallback.get(pref)
    return _apk_zip.read(src) if src else None


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200, ctype="application/json; charset=utf-8"):
        # Shotgun: the Java publisher SDK reads svrip/svrport off *some* response object
        # ("No value for svrip"); we don't yet know which endpoint, so inject the gate
        # coordinates at the top level of every JSON envelope. Harmless extra keys.
        if isinstance(obj, dict):
            obj.setdefault("svrip", config.HOST_IP)
            obj.setdefault("svrport", config.GATE_PORT)
            obj.setdefault("svrid", 1)
            obj.setdefault("svrname", "Revival S1")
            obj.setdefault("svrstate", 1)
        body = obj if isinstance(obj, (bytes,)) else \
               obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if getattr(self, "command", "GET") != "HEAD":
            self.wfile.write(body)

    def _route(self, method):
        u = urlparse(self.path)
        path = u.path
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        log(method, self.path, "from", self.client_address[0],
            ("\n    body=" + body.decode("utf-8", "replace")) if body else "")

        # CDN asset download -> serve a real bundle (exact bundled copy or same-prefix
        # stand-in) so the client's pre-load completes instead of choking on JSON.
        if "/cdn/" in path and "/gameswitch/" not in path:
            name = path.rstrip("/").rsplit("/", 1)[-1]
            rng = self.headers.get("Range")
            log("CDN-REQ", method, name, "Range=" + str(rng),
                "UA=" + str(self.headers.get("User-Agent")))
            data = _cdn_asset(name)
            if data is None:
                log("CDN-404", name)
                return self._send({"errno": 0}, 404)
            tag = "(exact)" if ("assets/" + name) in _apk_set else "(fallback)"
            if rng and rng.startswith("bytes="):  # honor resume/range downloaders
                try:
                    s, _, e = rng[6:].partition("-")
                    start = int(s) if s else 0
                    end = int(e) if e else len(data) - 1
                    chunk = data[start:end + 1]
                    self.send_response(206)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                    self.send_header("Content-Length", str(len(chunk)))
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    if method != "HEAD":
                        self.wfile.write(chunk)
                    log("CDN", name, f"-> 206 {len(chunk)}B [{start}-{end}/{len(data)}]", tag)
                    return
                except Exception as ex:
                    log("CDN range err", ex)
            log("CDN", name, f"-> {len(data)}B", tag)
            return self._send(data, ctype="application/octet-stream")

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
            return self._send({"errno": 0, "status": 1,
                               "svrip": config.HOST_IP, "svrport": config.GATE_PORT,
                               "ip": config.HOST_IP, "port": config.GATE_PORT,
                               "gate": [config.HOST_IP], "domains": [config.HOST_IP]})
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
    def do_HEAD(self): self._route("HEAD")
    def log_message(self, *a):  # silence stdlib logging; we use our own
        pass


def serve(port, tls):
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as e:
        log(f"!! could not bind port {port}: {e} (skipping)")
        return
    scheme = "http"
    if tls:
        if os.path.exists(config.SERVER_CRT) and os.path.exists(config.SERVER_KEY):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(config.SERVER_CRT, config.SERVER_KEY)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            scheme = "https"
        else:
            log(f"!! no certs ({config.SERVER_CRT}); run gen_certs.py. Serving :{port} as plain http")
    log(f"listening on {scheme}://0.0.0.0:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    jobs = [(p, True) for p in config.TLS_PORTS] + [(p, False) for p in config.PLAIN_PORTS]
    threads = [threading.Thread(target=serve, args=(p, tls), daemon=True) for p, tls in jobs]
    for t in threads:
        t.start()
    log(f"portal up on {[p for p,_ in jobs]}; advertising gate at {config.HOST_IP}:{config.GATE_PORT}")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        log("stopped")
