"""
UniNotes — gazda desktop.

Deschide interfața (index.html / styles.css / app.js) într-o fereastră nativă Windows,
folosind motorul Edge WebView2. Notițele NU mai stau în browser: se salvează într-un
fișier JSON de pe disc, lângă aplicație.
"""

import base64
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
        # Numele începe cu „_" intenționat: pywebview parcurge atributele publice ale
        # acestui obiect ca să construiască puntea din JavaScript și, dacă găsește un
        # atribut care nu e funcție, intră recursiv în el. Cu fereastra expusă public,
        # cobora prin tot obiectul .NET al ferestrei, umplea puntea cu mii de intrări
        # și, în varianta compilată, obiectul injectat ajungea trunchiat — dispăreau
        # metode reale (save_data), iar aplicația nu mai pornea.
        self._window = None

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

    # ---------- poze din notițe ----------
    # Stau ca fișiere lângă notite.json, nu într-o bază de date a browserului:
    # așa rămâne adevărat că notițele se pot copia pe un stick cu tot cu poze.
    def _images_dir(self) -> Path:
        d = DATA_DIR / "imagini"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # Fotografiile vin ca JPEG, desenele ca PNG (liniile ies curate, fișierul e mic).
    FORMATE = {"image/jpeg": ".jpg", "image/png": ".png"}

    @staticmethod
    def _safe_id(image_id) -> str:
        """Numele vine din interfață; nu lăsăm din el decât ce e sigur într-o cale."""
        text = str(image_id or "")
        curat = "".join(c for c in text if c.isalnum() or c in "-_")
        return curat[:64]

    def _find_image(self, name: str):
        for ext in self.FORMATE.values():
            path = self._images_dir() / (name + ext)
            if path.exists():
                return path
        return None

    def save_image(self, image_id, data_url):
        try:
            name = self._safe_id(image_id)
            if not name:
                return {"ok": False, "error": "nume invalid"}
            head, _, payload = str(data_url).partition(",")
            if "base64" not in head:
                return {"ok": False, "error": "format neasteptat"}
            tip = head[5:head.find(";")] if head.startswith("data:") and ";" in head else "image/jpeg"
            ext = self.FORMATE.get(tip)
            if ext is None:
                return {"ok": False, "error": "format de imagine neacceptat"}
            vechi = self._find_image(name)          # la reînlocuire, nu lăsăm două fișiere
            if vechi is not None and vechi.suffix != ext:
                vechi.unlink(missing_ok=True)
            (self._images_dir() / (name + ext)).write_bytes(base64.b64decode(payload))
            return {"ok": True}
        except Exception as exc:                                  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def load_image(self, image_id):
        try:
            name = self._safe_id(image_id)
            if not name:
                return None
            path = self._find_image(name)
            if path is None:
                return None
            tip = "image/png" if path.suffix == ".png" else "image/jpeg"
            return "data:" + tip + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        except Exception:                                         # noqa: BLE001
            return None

    def delete_image(self, image_id):
        try:
            name = self._safe_id(image_id)
            if name:
                for ext in self.FORMATE.values():
                    (self._images_dir() / (name + ext)).unlink(missing_ok=True)
            return True
        except Exception:                                         # noqa: BLE001
            return False

    def list_images(self):
        try:
            nume = []
            for ext in self.FORMATE.values():
                nume += [p.stem for p in self._images_dir().glob("*" + ext)]
            return sorted(set(nume))
        except Exception:                                         # noqa: BLE001
            return []

    # ---------- fișiere ----------
    def save_file(self, suggested_name, content):
        downloads = Path.home() / "Downloads"
        result = self._window.create_file_dialog(
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
        result = self._window.create_file_dialog(
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

            control = self._window.native.browser.webview
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
    api._window = window

    webview.start(
        gui="edgechromium",
        private_mode=False,
        storage_path=str(DATA_DIR / ".fereastra"),
    )


if __name__ == "__main__":
    main()
