#!/usr/bin/env python3
"""
Server production cho Monitor Dashboard (port 8001).

- Phục vụ file tĩnh từ frontend/monitor/build (bản build CRA).
- Đường dẫn không phải file tĩnh (API: /api/, /backtest/, /public/plot/...)
  được proxy sang Django backend tại 127.0.0.1:8002 — thay thế vai trò
  "proxy" của CRA dev server trong môi trường production.
- Nhẹ (~25MB RAM, stdlib thuần), thay cho `python -m http.server`.
"""
import http.client
import mimetypes
import os
import posixpath
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "monitor", "build")
# Dải port 18xxx: tránh tranh chấp với dịch vụ khác trên server dùng chung
BACKEND = ("127.0.0.1", 18002)
PORT = 18001

HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def resolve_static(self, path):
        # Chuẩn hóa, chặn path traversal; symlink build/public -> . đã xử lý tiền tố /public
        path = posixpath.normpath(unquote(urlsplit(path).path))
        if path.startswith("/public/"):
            path = path[len("/public"):]
        parts = [p for p in path.split("/") if p and p not in (".", "..")]
        full = os.path.join(BUILD_DIR, *parts)
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        return full if os.path.isfile(full) else None

    def serve_static(self, full):
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if "/static/" in full or "/assets/" in full:
            self.send_header("Cache-Control", "public, max-age=3600")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def proxy(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            conn = http.client.HTTPConnection(*BACKEND, timeout=120)
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in HOP_HEADERS}
            # Giữ nguyên Host gốc của client: Django cần nó để xác thực
            # ALLOWED_HOSTS và kiểm tra an toàn của tham số ?next= (redirect
            # sau đăng nhập). Ghi đè thành 127.0.0.1 sẽ làm next= bị coi là
            # cross-host -> rơi về /accounts/profile/ (404).
            headers["Host"] = self.headers.get("Host", "127.0.0.1:18002")
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in HOP_HEADERS and k.lower() != "content-length":
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            conn.close()
        except (ConnectionError, OSError) as e:
            msg = ('{"result": false, "message": "Backend %s:%s unreachable: %s"}'
                   % (BACKEND[0], BACKEND[1], type(e).__name__)).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def route(self):
        if self.command in ("GET", "HEAD"):
            full = self.resolve_static(self.path)
            if full:
                return self.serve_static(full)
        self.proxy()

    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = route


if __name__ == "__main__":
    if not os.path.isdir(BUILD_DIR):
        sys.exit(f"Không thấy thư mục build: {BUILD_DIR} — chạy build_frontend.sh trước.")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Monitor UI: http://localhost:{PORT} (static: {BUILD_DIR}, proxy API -> {BACKEND[0]}:{BACKEND[1]})")
    server.serve_forever()
