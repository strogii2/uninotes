"""
UniNotes — gazda desktop.

Deschide interfața (index.html / styles.css / app.js) într-o fereastră nativă Windows,
folosind motorul Edge WebView2. Notițele NU mai stau în browser: se salvează într-un
fișier JSON de pe disc, lângă aplicație.
"""

import base64
import hashlib
import html
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

import webview

APP_NAME = "UniNotes"
MAX_CALENDAR = 5 * 1024 * 1024          # un calendar de facultate are sub 1 MB
MAX_RASPUNS = 8 * 1024 * 1024           # un răspuns Moodle e de ordinul zecilor de KB
ORE_INTRE_COPII = 6                     # cât de des se pune deoparte o copie
MAX_COPII = 12                          # câte copii ținem (vreo trei zile în urmă)
MUTARI = (301, 302, 303, 307, 308)      # felurile în care un server spune „m-am mutat"
MAX_MUTARI = 4                          # de câte ori mergem după o adresă mutată

LOCALE = ("localhost", "127.0.0.1", "::1")


class _NuUrma(urllib.request.HTTPRedirectHandler):
    """Oprește urmărirea automată a mutărilor: hotărâm noi ce facem cu ele."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _postare(url, camp, timeout, limita):
    """
    Trimite un formular prin POST și întoarce (cod, corp, adresa nouă).
    Nu urmează mutările — le dă mai departe, ca să hotărască cine a chemat.
    """
    cerere = urllib.request.Request(
        url, data=urllib.parse.urlencode(camp).encode("utf-8"),
        headers={"User-Agent": "UniNotes",
                 "Content-Type": "application/x-www-form-urlencoded"})
    deschizator = urllib.request.build_opener(_NuUrma)
    try:
        with deschizator.open(cerere, timeout=timeout) as r:
            return r.getcode(), r.read(limita + 1), None
    except urllib.error.HTTPError as e:
        try:
            corp = e.read(limita + 1)
        except Exception:                                         # noqa: BLE001
            corp = b""
        loc = e.headers.get("Location") if e.code in MUTARI else None
        return e.code, corp, loc


def trimite_la_moodle(site, cale, camp, timeout=30, limita=MAX_RASPUNS):
    """
    Trimite o cerere la Moodle și, dacă serverul răspunde „adresa s-a mutat",
    o trimite din nou — cu tot cu date — la adresa nouă.

    Python urmează mutările singur, dar pe drum preface POST-ul în GET și lasă
    datele acasă. Moodle primea o cerere goală și se plângea că lipsește
    „username", deși noi îl trimisesem. Exact asta pățea moodle.usm.md, care e
    mutat la elearning.usm.md: omul scria utilizatorul, iar aplicația îi spunea
    că nu l-a scris.

    Întoarce {"corp":…, "site":…} — unde „site" e adresa adevărată, cea de la
    capătul mutărilor — sau {"eroare":…}.
    """
    site = str(site or "").strip().rstrip("/")
    for _ in range(MAX_MUTARI):
        cod, corp, loc = _postare(site + cale, camp, timeout, limita)
        if not loc:
            return {"cod": cod, "corp": corp, "site": site}

        nou = urllib.parse.urljoin(site + cale, loc)
        parte = urllib.parse.urlparse(nou)
        if parte.scheme != "https" and (parte.hostname or "") not in LOCALE:
            # datele noastre n-au ce căuta pe o legătură necriptată
            return {"eroare": "Moodle-ul trimite mai departe la o adresă necriptată "
                              "(%s). Nu trimit datele acolo." % nou}
        if not parte.path.endswith(cale):
            # mutat spre pagina de întâmpinare, nu spre serviciu: nu e Moodle acolo
            return {"eroare": "Adresa e mutată la %s, care nu pare a fi un Moodle. "
                              "Întreabă la facultate care e adresa bună." % nou}
        site = nou[: nou.rindex(cale)].rstrip("/")
    return {"eroare": "Adresa se tot mută de la un server la altul. "
                      "Verifică adresa Moodle."}


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

    Un lansator care pornește aplicația din alt folder decât al tău spune
    explicit unde stau notițele, prin UNINOTES_NOTITE. Fără asta, aplicația
    și-ar face un folder nou, gol, lângă locul de unde a fost pornită — și ai
    crede că ți-ai pierdut notițele.
    """
    ales = os.environ.get("UNINOTES_NOTITE")
    if ales:
        try:
            p = Path(ales)
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:                                         # noqa: BLE001
            pass                                                  # cădem pe drumul obișnuit

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


def port_statornic() -> int:
    """
    Același port la fiecare pornire, ales din calea notițelor.

    Browserul dinăuntru leagă tot ce ține minte singur — cheia de Moodle, între
    altele — de adresa paginii, iar adresa cuprinde și portul. Cu port ales de
    sistem, fiecare pornire deschidea alt sertar, gol: cheia părea pierdută și
    trebuia luată din nou de fiecare dată. Portul iese din calea notițelor, deci
    două copii ale aplicației, cu notițe diferite, nu se calcă pe picioare.

    Stă sub 49152, ca să nu se bată cu porturile pe care Windows le împarte
    singur programelor care ies în lume.
    """
    amprenta = hashlib.sha256(str(DATA_DIR).lower().encode("utf-8")).digest()
    return 40000 + int.from_bytes(amprenta[:2], "big") % 9000


def start_local_server() -> int:
    """
    Servim interfața pe 127.0.0.1, nu din file://, din două motive:
    WebView2 refuză „?parametru” la URL-urile file://, iar puntea pywebview
    apare abia după window.load — așa aplicația știe din prima că e desktop.
    Ascultă doar local, pe portul statornic de mai sus.
    """
    root = str(asset_dir())

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root, **kwargs)

        def log_message(self, *args):        # fără zgomot în consolă
            pass

    httpd = None
    dorit = port_statornic()
    for pas in range(8):                     # dacă e ocupat, încercăm vecinii
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", dorit + pas), Handler)
            break
        except OSError:
            continue
    if httpd is None:                        # ultima soluție: orice port liber
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
            self._fa_copie()
            fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, DATA_FILE)
            return {"ok": True, "path": str(DATA_FILE)}
        except Exception as exc:                                  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ---------- copii de siguranță ----------
    # Notițele se salvează singure la fiecare tastă, deci o ștergere din greșeală
    # devine definitivă în câteva secunde: nu mai există nicăieri versiunea de
    # dinainte. Punem deoparte, din când în când, fișierul așa cum era.

    def _copii_dir(self) -> Path:
        d = DATA_DIR / "copii"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _copiile(self):
        """
        Copiile, de la cea mai nouă. Ne luăm după ora fișierului, nu după nume:
        numele se aseamănă prea mult între ele, iar „-2” pus la coadă pentru un
        nume ocupat sortează înaintea punctului și răstoarnă ordinea.
        """
        try:
            return sorted(self._copii_dir().glob("notite-*.json"),
                          key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        except Exception:                                         # noqa: BLE001
            return []

    def _nume_copie(self) -> Path:
        """
        Un nume liber. Ceasul nu e de ajuns nici cu secunde: două copii cerute
        una după alta ar primi același nume și a doua ar ștearge-o pe prima —
        tocmai pe cea de dinaintea unei restaurări, când conta cel mai mult.
        """
        baza = "notite-" + time.strftime("%Y-%m-%d_%H-%M-%S")
        cale = self._copii_dir() / (baza + ".json")
        i = 2
        while cale.exists() and i < 100:
            cale = self._copii_dir() / (baza + "-" + str(i) + ".json")
            i += 1
        return cale

    def _fa_copie(self):
        """
        O copie la fiecare ORE_INTRE_COPII, nu la fiecare salvare: altfel am
        umple discul cu mii de fișiere aproape identice. Ținem ultimele
        MAX_COPII — destul cât să prinzi o greșeală după câteva zile.
        """
        try:
            if not DATA_FILE.exists() or DATA_FILE.stat().st_size < 2:
                return
            copii = self._copiile()
            if copii:
                varsta = time.time() - copii[0].stat().st_mtime
                if varsta < ORE_INTRE_COPII * 3600:
                    return
            shutil.copyfile(DATA_FILE, self._nume_copie())
            for veche in self._copiile()[MAX_COPII:]:
                try:
                    veche.unlink()
                except Exception:                                 # noqa: BLE001
                    pass
        except Exception:                                         # noqa: BLE001
            pass                                                  # o copie ratată nu oprește salvarea

    def list_backups(self):
        """Copiile de pe disc, de la cea mai nouă, cu câte notițe are fiecare."""
        out = []
        for p in self._copiile():
            rand = {"nume": p.name, "marime": p.stat().st_size,
                    "cand": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)),
                    "notite": None, "materii": None}
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                rand["notite"] = len(d.get("notes") or [])
                rand["materii"] = len(d.get("subjects") or [])
            except Exception:                                     # noqa: BLE001
                pass
            out.append(rand)
        return out

    def read_backup(self, nume):
        """Conținutul unei copii. Numele e verificat, ca să nu iasă din folder."""
        nume = str(nume or "")
        if not re.fullmatch(r"notite-[0-9_\-]{1,40}\.json", nume):
            return None
        p = self._copii_dir() / nume
        try:
            if p.parent.resolve() != self._copii_dir().resolve() or not p.exists():
                return None
            return p.read_text(encoding="utf-8")
        except Exception:                                         # noqa: BLE001
            return None

    def copie_acum(self):
        """Copie cerută anume, fără să aștepte trecerea orelor (înainte de a restaura)."""
        try:
            if not DATA_FILE.exists():
                return False
            shutil.copyfile(DATA_FILE, self._nume_copie())
            for veche in self._copiile()[MAX_COPII:]:
                try:
                    veche.unlink()
                except Exception:                                 # noqa: BLE001
                    pass
            return True
        except Exception:                                         # noqa: BLE001
            return False

    def notifica(self, titlu, corp):
        """
        O notificare adevărată de Windows.

        În fereastra aplicației, motorul de browser refuză din start
        notificările paginii — nu întreabă pe nimeni, răspunde „nu” și gata.
        Așa că amintirile pentru termene nu ajungeau nicăieri, tăcut. Aici
        ieșim din browser și o cerem chiar sistemului.
        """
        if os.name != "nt":
            return False

        def sq(s):
            # ghilimelele simple se dublează: așa se scapă textul în PowerShell
            return "'" + str(s or "").replace("'", "''")[:180] + "'"

        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications,"
            " ContentType=WindowsRuntime] | Out-Null;"
            "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
            "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
            "$n=$x.GetElementsByTagName('text');"
            "$n.Item(0).AppendChild($x.CreateTextNode(%s))|Out-Null;"
            "$n.Item(1).AppendChild($x.CreateTextNode(%s))|Out-Null;"
            "$t=[Windows.UI.Notifications.ToastNotification]::new($x);"
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
            "'Microsoft.Windows.Computer').Show($t)" % (sq(titlu), sq(corp))
        )
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", ps],
                creationflags=0x08000000,          # fără fereastră neagră de consolă
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:                                     # noqa: BLE001
            return False

    def open_link(self, url):
        """
        Deschide o legătură în browserul tău, nu în fereastra aplicației.
        Fără asta, o apăsare pe un material din Moodle ar înlocui aplicația cu
        pagina aceea și n-ai mai avea cum să te întorci.
        """
        url = str(url or "").strip()
        if not url.lower().startswith(("http://", "https://")):
            return False
        try:
            webbrowser.open(url)
            return True
        except Exception:                                         # noqa: BLE001
            return False

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
            # newline="" ca să nu traducă Windows capetele de rând: un fișier de
            # calendar vine deja cu \r\n, iar traducerea l-ar face \r\r\n și
            # unele calendare l-ar refuza
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            return str(path)
        except Exception:                                         # noqa: BLE001
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

    # ---------- calendarul de la facultate ----------
    def fetch_calendar(self, url):
        """
        Aduce un calendar (.ics) de pe internet — de la Moodle, de obicei.
        Pagina n-o poate face singură: browserul refuză citirea de pe alt site
        decât cel al aplicației, iar Moodle-ul facultății nu dă voie nimănui.

        Puntea rămâne îngustă înadins: numai http/https și numai dacă răspunsul
        chiar e un calendar. Nu e un cititor de internet de uz general.
        """
        url = str(url or "").strip()
        if not url.lower().startswith(("http://", "https://")):
            return {"ok": False, "eroare": "Adresa trebuie să înceapă cu http:// sau https://"}
        try:
            cerere = urllib.request.Request(url, headers={"User-Agent": "UniNotes"})
            with urllib.request.urlopen(cerere, timeout=25) as r:
                brut = r.read(MAX_CALENDAR + 1)
        except urllib.error.HTTPError as e:
            return {"ok": False, "eroare": "Serverul a răspuns cu eroarea %s." % e.code}
        except Exception as e:                                    # noqa: BLE001
            return {"ok": False, "eroare": "Nu am putut ajunge la adresă: %s" % e}

        if len(brut) > MAX_CALENDAR:
            return {"ok": False, "eroare": "Calendarul e prea mare (peste 5 MB)."}
        text = brut.decode("utf-8", errors="replace").lstrip("﻿")
        if "BEGIN:VCALENDAR" not in text[:2000]:
            return {"ok": False,
                    "eroare": "Adresa nu întoarce un calendar. Verifică dacă e "
                              "chiar legătura de export din Moodle."}
        return {"ok": True, "text": text}

    @staticmethod
    def _citeste_raspuns(text):
        """
        Moodle nu răspunde mereu în JSON. Când cheia e greșită, unele instalări
        aruncă eroarea în XML, chiar dacă am cerut anume JSON — se întâmplă
        înainte să apuce să aleagă formatul. Dacă n-o citim și pe aceea, am
        spune că adresa „nu e un Moodle”, ceea ce e neadevărat și trimite omul
        pe un drum greșit.
        """
        try:
            return json.loads(text)
        except Exception:                                         # noqa: BLE001
            pass
        if "<EXCEPTION" in text[:400]:
            def scoate(eticheta):
                m = re.search(r"<%s>(.*?)</%s>" % (eticheta, eticheta), text, re.S)
                return html.unescape(m.group(1)).strip() if m else ""
            return {"exception": "moodle_exception",
                    "errorcode": scoate("ERRORCODE"),
                    "message": scoate("MESSAGE")}
        return None

    def moodle_verifica(self, site):
        """
        Spune ce se poate face la adresa asta — fără cont, fără cheie, fără
        parolă. Moodle răspunde cu erori care se deosebesc între ele, iar din
        ele se vede dacă serviciile web sunt pornite și dacă merge conectarea
        cu parola. Așa afli de ce nu merge, în loc să ghicești.
        """
        site = str(site or "").strip().rstrip("/")
        if not site.lower().startswith(("http://", "https://")):
            return {"ok": False, "eroare": "Adresa trebuie să înceapă cu https://"}

        mutat = {"la": ""}

        def intreaba(cale, camp):
            try:
                r = trimite_la_moodle(site, cale, camp, timeout=25)
            except Exception as e:                                # noqa: BLE001
                return {"retea": str(e)}
            if r.get("eroare"):
                return {"retea": r["eroare"]}
            if r["site"] != site:
                mutat["la"] = r["site"]
            if r["cod"] >= 400:
                return {"http": r["cod"]}
            text = r["corp"].decode("utf-8", errors="replace")
            citit = self._citeste_raspuns(text)
            if citit is not None:
                return {"json": citit}
            return {"nu_e_json": True, "inceput": text[:120]}

        raspuns = {
            "ok": True,
            "servicii": intreaba("/webservice/rest/server.php", {
                "wstoken": "verificare", "wsfunction": "core_webservice_get_site_info",
                "moodlewsrestformat": "json"}),
            "parola": intreaba("/login/token.php", {
                "username": "", "password": "", "service": "moodle_mobile_app"}),
        }
        raspuns["mutat"] = mutat["la"]
        return raspuns

    def moodle_login(self, site, utilizator, parola):
        """
        Cere Moodle-ului o cheie pentru contul tău, dând utilizatorul și parola
        — exact drumul pe care merge și aplicația oficială Moodle.

        Parola trece o singură dată, direct către serverul facultății, și nu se
        păstrează nicăieri: nici pe disc, nici în mesajele de eroare de mai jos.
        Înapoi vine o cheie, și numai ea se ține minte.
        """
        site = str(site or "").strip().rstrip("/")
        if not site.lower().startswith(("http://", "https://")):
            return {"ok": False, "eroare": "Adresa Moodle trebuie să înceapă cu https://"}

        gazda = urllib.parse.urlparse(site).hostname or ""
        local = gazda in ("localhost", "127.0.0.1", "::1")
        if site.lower().startswith("http://") and not local:
            # o parolă pe http s-ar citi pe drum de oricine
            return {"ok": False,
                    "eroare": "Adresa e http://, nu https://. Nu trimit parola pe o "
                              "legătură necriptată."}
        if not str(utilizator or "").strip() or not str(parola or ""):
            return {"ok": False, "eroare": "Pune și utilizatorul, și parola."}

        date = {
            "username": str(utilizator).strip(),
            "password": str(parola),
            "service": "moodle_mobile_app",
        }
        try:
            r = trimite_la_moodle(site, "/login/token.php", date, timeout=30)
        except Exception as e:                                    # noqa: BLE001
            return {"ok": False, "eroare": "Nu am putut ajunge la Moodle: %s" % e}
        finally:
            date = None                                           # nu mai ținem parola în memorie

        if r.get("eroare"):
            return {"ok": False, "eroare": r["eroare"]}
        if r["cod"] >= 400:
            return {"ok": False, "eroare": "Serverul a răspuns cu eroarea %s." % r["cod"]}

        try:
            raspuns = json.loads(r["corp"].decode("utf-8", errors="replace"))
        except Exception:                                         # noqa: BLE001
            return {"ok": False,
                    "eroare": "Adresa nu pare a fi un Moodle. Pune doar adresa de "
                              "pornire, fără /my sau /login."}

        if raspuns.get("token"):
            # „site" e adresa adevărată: dacă a fost o mutare, de acum ținem minte
            # unde a ajuns Moodle-ul, ca să nu mai treacă nimeni pe la vechea adresă
            return {"ok": True, "token": raspuns["token"], "site": r["site"]}
        return {"ok": False, "cod": str(raspuns.get("errorcode") or ""),
                "eroare": str(raspuns.get("error") or "Moodle n-a dat cheia.")}

    def moodle_api(self, site, token, functie, parametri):
        """
        Vorbește cu serviciile web ale unui Moodle, cu jetonul tău.

        Pagina n-o poate face singură: browserul nu are voie să ceară nimic de
        pe alt site decât al ei. Puntea rămâne îngustă: numai adresa de serviciu
        a unui Moodle și numai prin POST — așa jetonul nu ajunge scris în
        jurnalele serverului, cum s-ar întâmpla dacă ar sta într-o adresă.
        """
        site = str(site or "").strip().rstrip("/")
        if not site.lower().startswith(("http://", "https://")):
            return {"ok": False, "eroare": "Adresa Moodle trebuie să înceapă cu https://"}
        if not str(token or "").strip():
            return {"ok": False, "eroare": "Lipsește jetonul."}

        camp = {
            "wstoken": str(token).strip(),
            "wsfunction": str(functie or ""),
            "moodlewsrestformat": "json",
        }
        if isinstance(parametri, dict):
            for k, v in parametri.items():
                camp[str(k)] = "" if v is None else str(v)

        try:
            r = trimite_la_moodle(site, "/webservice/rest/server.php", camp, timeout=30)
        except Exception as e:                                    # noqa: BLE001
            return {"ok": False, "eroare": "Nu am putut ajunge la Moodle: %s" % e}

        if r.get("eroare"):
            return {"ok": False, "eroare": r["eroare"]}
        if r["cod"] >= 400:
            return {"ok": False, "eroare": "Serverul a răspuns cu eroarea %s." % r["cod"]}

        brut = r["corp"]
        if len(brut) > MAX_RASPUNS:
            return {"ok": False, "eroare": "Răspuns prea mare de la Moodle."}
        citit = self._citeste_raspuns(brut.decode("utf-8", errors="replace"))
        if citit is None:
            return {"ok": False,
                    "eroare": "Moodle n-a răspuns cu date. Verifică adresa — trebuie "
                              "să fie doar adresa de pornire, fără /my sau /login."}
        return {"ok": True, "raspuns": citit, "site": r["site"]}

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
