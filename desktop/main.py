"""
UniNotes — gazda desktop.

Deschide interfața (index.html / styles.css / app.js) într-o fereastră nativă Windows,
folosind motorul Edge WebView2. Notițele NU mai stau în browser: se salvează într-un
fișier JSON de pe disc, lângă aplicație.
"""

import http.server
import json
import os
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

import webview

APP_NAME = "UniNotes"


def asset_dir() -> Path:
    """Folderul cu index.html / styles.css / app.js."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "web"          # noqa: SLF001 (pus de PyInstaller)
    return Path(__file__).resolve().parent.parent


def app_dir() -> Path:
    """Folderul în care stă executabilul (sau proiectul, în timpul dezvoltării)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_data_dir() -> Path:
    """
    Notițele stau lângă .exe, ca să le poți copia/sincroniza ușor.
    Dacă acolo nu se poate scrie (ex. aplicația e în Program Files), folosim %APPDATA%.
    """
    candidate = app_dir() / "Notite UniNotes"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".test-scriere"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return candidate
    except Exception:
        fallback = Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = resolve_data_dir()
DATA_FILE = DATA_DIR / "notite.json"


def start_local_server() -> int:
    """
    Servim interfața pe 127.0.0.1, nu din file://, din două motive:
    WebView2 refuză „?parametru” la URL-urile file://, iar puntea pywebview
    apare abia după window.load — așa aplicația știe din prima că e desktop.
    Portul e ales de sistem și ascultă doar local.
    """
    root = str(asset_dir())

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root, **kwargs)

        def log_message(self, *args):        # fără zgomot în consolă
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1]


class Api:
    """Puntea dintre interfața web și fișierele de pe disc."""

    def __init__(self) -> None:
        self.window = None

    # ---------- date ----------
    def load_data(self):
        if not DATA_FILE.exists():
            return None
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            # nu pierdem fișierul stricat — îl punem deoparte și pornim curat
            try:
                shutil.copy2(DATA_FILE, DATA_FILE.with_suffix(".json.stricat"))
            except Exception:
                pass
            return None

    def save_data(self, data):
        """Scriere atomică: întâi într-un fișier temporar, apoi îl mutăm peste cel real."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, DATA_FILE)
            return {"ok": True, "path": str(DATA_FILE)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ---------- fișiere ----------
    def save_file(self, suggested_name, content):
        downloads = Path.home() / "Downloads"
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=str(downloads if downloads.is_dir() else Path.home()),
            save_filename=suggested_name,
        )
        if not result:
            return None
        path = result if isinstance(result, str) else result[0]
        try:
            Path(path).write_text(content, encoding="utf-8")
            return str(path)
        except Exception:
            return None

    def open_file(self):
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Backup UniNotes (*.json)", "Toate fișierele (*.*)"),
        )
        if not result:
            return None
        path = result if isinstance(result, str) else result[0]
        try:
            return {"name": os.path.basename(path), "content": Path(path).read_text(encoding="utf-8")}
        except Exception:
            return None

    # ---------- diverse ----------
    def data_folder(self):
        return str(DATA_DIR)

    def open_data_folder(self):
        try:
            os.startfile(str(DATA_DIR))  # noqa: S606
            return True
        except Exception:
            return False

    def print_ui(self):
        """
        Deschide dialogul de printare al ferestrei.

        WebView2 ignoră window.print() din JavaScript, dar expune ShowPrintUI în API-ul
        nativ. Trebuie chemat pe firul de interfață, altfel COM-ul refuză accesul.
        """
        try:
            from System import Action                       # oferit de pythonnet

            control = self.window.native.browser.webview
            rezultat = []

            def arata():
                try:
                    # ShowPrintUI cere tipul enum al WebView2, nu un întreg
                    from Microsoft.Web.WebView2.Core import CoreWebView2PrintDialogKind
                    control.CoreWebView2.ShowPrintUI(CoreWebView2PrintDialogKind.Browser)
                    rezultat.append(True)
                except Exception:
                    rezultat.append(False)

            control.Invoke(Action(arata))
            return bool(rezultat) and rezultat[0]
        except Exception:
            return False

    def print_note(self, title, body_html, css):
        """
        WebView2 nu deschide dialogul de printare din JS, așa că scriem notița
        într-un HTML temporar și îl deschidem în browserul implicit, unde Ctrl+P merge.
        """
        try:
            tmp_dir = Path(tempfile.gettempdir()) / "UniNotes-print"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            page = tmp_dir / "notita.html"
            page.write_text(
                "<!DOCTYPE html><html lang='ro'><head><meta charset='utf-8'>"
                f"<title>{title}</title><style>{css}</style></head>"
                f"<body><article class='doc'><h1>{title}</h1>{body_html}</article>"
                "<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),350))</script>"
                "</body></html>",
                encoding="utf-8",
            )
            os.startfile(str(page))  # noqa: S606
            return True
        except Exception:
            return False


def main() -> None:
    api = Api()
    start_url = "http://127.0.0.1:%d/index.html?desktop=1" % start_local_server()

    window = webview.create_window(
        APP_NAME,
        url=start_url,
        js_api=api,
        width=1320,
        height=860,
        min_size=(420, 560),
        background_color="#F5F7FB",
        text_select=True,
    )
    api.window = window

    webview.start(
        gui="edgechromium",
        private_mode=False,
        storage_path=str(DATA_DIR / ".fereastra"),
    )


if __name__ == "__main__":
    main()
