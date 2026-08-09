"""
Servește DOAR fișierele interfeței, pentru instalarea pe telefon.

Important: folderul UniNotes mai conține executabilul, notițele tale și codul sursă.
Serverul de aici merge pe listă albă — orice altceva primește 404, ca nimic personal
să nu poată fi cerut din exterior.
"""

import http.server
import socket
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PERMISE = {
    "/": "index.html",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
    "/app.js": "app.js",
    "/sw.js": "sw.js",
    "/manifest.webmanifest": "manifest.webmanifest",
    "/icons/icon-192.png": "icons/icon-192.png",
    "/icons/icon-512.png": "icons/icon-512.png",
    "/icons/icon-maskable-512.png": "icons/icon-maskable-512.png",
    "/icons/apple-touch-icon.png": "icons/apple-touch-icon.png",
    "/favicon.ico": "icons/apple-touch-icon.png",
}

TIPURI = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/png",
}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "UniNotes"

    def do_GET(self):                       # noqa: N802
        cale = self.path.split("?", 1)[0].split("#", 1)[0]
        tinta = PERMISE.get(cale)
        if not tinta:
            self.send_error(404, "Not found")
            return

        fisier = ROOT / tinta
        if not fisier.is_file():
            self.send_error(404, "Not found")
            return

        date = fisier.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TIPURI.get(fisier.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(date)))
        # fără cache la nivel de rețea: service worker-ul se ocupă de asta
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(date)

    def do_HEAD(self):                      # noqa: N802
        self.do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


def ip_local() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8767
    gazda = "0.0.0.0" if "--retea" in sys.argv else "127.0.0.1"

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((gazda, port), Handler) as httpd:
        print(f"Servesc {len(PERMISE)} fisiere permise din {ROOT}")
        print(f"  local : http://127.0.0.1:{port}/")
        if gazda == "0.0.0.0":
            print(f"  retea : http://{ip_local()}:{port}/")
        print("Ctrl+C pentru oprire.")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
