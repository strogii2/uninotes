"""
Verifică legătura cu contul Moodle, în fereastra reală.

Pornim un Moodle fals care răspunde exact ca cel adevărat — aceleași funcții de
serviciu web, aceleași forme de răspuns, aceleași erori — și urmărim tot lanțul:
conectare cu cheia, aducerea informației pe materii, legarea cursurilor de
materiile din aplicație, temele care devin termene, și faptul că lipsa unei
funcții nu strică restul.

Verificăm și ce nu trebuie să se întâmple: cheia nu are voie să ajungă în
fișierul cu notițe, fiindcă acela pleacă în backup și în sincronizare.
"""

import json
import tempfile
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sys

# Consola Windows nu scrie diacritice implicit, iar rezultatul testului
# s-ar pierde tocmai cand ai nevoie de el.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import webview

import main as app

CHEIE_BUNA = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
# cheia pe care Moodle o dă și n-o mai recunoaște — nu e în nicio listă a lui
CHEIE_UITATA = "9f9f9f9f9f9f9f9f9f9f9f9f9f9f9f9f"
UTILIZATOR = "carp.dragos"
PAROLA = "ParolaMeaSecreta!2026"

VIITOR = int((datetime.now() + timedelta(days=12)).timestamp())
TRECUT = int((datetime.now() - timedelta(days=40)).timestamp())
IERI = int((datetime.now() - timedelta(days=1)).timestamp())

FUNCTII = [
    "core_webservice_get_site_info",
    "core_enrol_get_users_courses",
    "mod_assign_get_assignments",
    "mod_forum_get_forums_by_courses",
    "mod_forum_get_forum_discussions",
    "gradereport_user_get_grade_items",
    "core_course_get_contents",
    "core_course_get_enrolled_courses_by_timeline_classification",
    "core_calendar_get_action_events_by_timesort",
]


REFUZ = {"exception": "webservice_access_exception", "errorcode": "accessexception",
         "message": "Access control exception (webservice_access_exception)"}

# ce rămâne pornit când facultatea dă o cheie cu drepturi tăiate
FUNCTII_TAIATE = [
    "core_webservice_get_site_info",
    "core_course_get_enrolled_courses_by_timeline_classification",
    "core_calendar_get_action_events_by_timesort",
]


def raspunde(functie, camp):
    fel = MOD["fel"]
    # ---- chei cu drepturi tăiate: cheia e bună, dar serviciul ei e mai sărac ----
    if fel == "nimic":
        return REFUZ
    if fel == "doar_calendar" and functie != "core_calendar_get_action_events_by_timesort":
        return REFUZ                       # nici măcar prezentarea nu merge
    if fel == "fara_enrol":
        if functie == "core_enrol_get_users_courses":
            return REFUZ
        if functie == "core_webservice_get_site_info":
            return {"sitename": "Moodle Facultatea de Probă", "username": "student1",
                    "fullname": "Dragoș Carp", "userid": 77,
                    "functions": [{"name": n, "version": "4.4"} for n in FUNCTII_TAIATE]}

    if functie == "core_course_get_enrolled_courses_by_timeline_classification":
        return {"courses": [
            {"id": 101, "shortname": "AM1", "fullname": "Analiză Matematică"},
            {"id": 102, "shortname": "GC", "fullname": "Grafică pe Calculator"},
        ]}

    if functie == "core_calendar_get_action_events_by_timesort":
        return {"events": [
            # aceeași temă ca la mod_assign: nu trebuie să se adauge de două ori
            {"id": 7001, "name": "Tema 2 — integrale este scadentă",
             "activityname": "Tema 2 — integrale", "modulename": "assign",
             "instance": 5001, "timesort": VIITOR, "description": "",
             "course": {"id": 101, "fullname": "Analiză Matematică", "shortname": "AM1"}},
            # și una care vine numai pe drumul ăsta, dintr-o materie numai a lui
            {"id": 7002, "name": "Lucrare de laborator", "activityname": "Lucrare de laborator",
             "modulename": "quiz", "instance": 6001, "timesort": VIITOR,
             "description": "<p>Aduceți <b>caietul</b>.</p>",
             "course": {"id": 103, "fullname": "Chimie Organică", "shortname": "CO"}},
        ]}

    if functie == "core_webservice_get_site_info":
        return {
            "sitename": "Moodle Facultatea de Probă",
            "username": "student1",
            "fullname": "Dragoș Carp",
            "userid": 77,
            "functions": [{"name": n, "version": "4.4"} for n in FUNCTII],
        }

    if functie == "core_enrol_get_users_courses":
        return [
            {"id": 101, "shortname": "AM1", "fullname": "Analiză Matematică"},
            {"id": 102, "shortname": "GC", "fullname": "Grafică pe Calculator"},
        ]

    if functie == "mod_assign_get_assignments":
        return {"courses": [
            {"id": 101, "fullname": "Analiză Matematică", "assignments": [
                {"id": 5001, "name": "Tema 2 — integrale", "duedate": VIITOR,
                 "intro": "<p>Trimiteți <b>PDF</b>.</p>"},
                {"id": 5002, "name": "Tema 1 — derivate", "duedate": TRECUT, "intro": ""},
            ]},
            {"id": 102, "fullname": "Grafică pe Calculator", "assignments": [
                {"id": 5003, "name": "Proiect — raytracer", "duedate": VIITOR, "intro": ""},
            ]},
        ]}

    if functie == "mod_forum_get_forums_by_courses":
        # numai primul curs are forum de anunțuri
        return [
            {"id": 900, "course": 101, "type": "news", "name": "Anunțuri"},
            {"id": 901, "course": 101, "type": "general", "name": "Discuții libere"},
        ]

    if functie == "mod_forum_get_forum_discussions":
        return {"discussions": [
            {"id": 1, "name": "Cursul de joi se mută în A3", "timemodified": IERI,
             "userfullname": "Prof. Ionescu",
             "message": "<p>Sala obișnuită e ocupată.<br>Ne vedem în <b>A3</b>.</p>"},
            {"id": 2, "name": "Bibliografie actualizată", "timemodified": TRECUT,
             "userfullname": "Prof. Ionescu", "message": "Am pus capitolul 4."},
        ]}

    if functie == "gradereport_user_get_grade_items":
        if camp.get("courseid") == "102":
            # facultatea nu dă notele la cursul ăsta: restul trebuie să vină oricum
            return {"exception": "moodle_exception", "errorcode": "nopermissions",
                    "message": "Nu ai voie la notele acestui curs"}
        return {"usergrades": [{"courseid": 101, "userid": 77, "gradeitems": [
            {"itemname": "Tema 1 — derivate", "gradeformatted": "8,50",
             "percentageformatted": "85,00 %"},
            {"itemname": "Test parțial", "gradeformatted": "9,00",
             "percentageformatted": "90,00 %"},
            {"itemname": "Examen final", "gradeformatted": "-",
             "percentageformatted": "-"},
        ]}]}

    if functie == "core_course_get_contents":
        if camp.get("courseid") == "101":
            return [
                {"id": 1, "name": "Săptămâna 1", "modules": [
                    {"id": 11, "name": "Curs 1 — limite", "modname": "resource",
                     "url": "https://moodle.test/mod/resource/view.php?id=11"},
                    {"id": 12, "name": "Anunț important", "modname": "label"},
                    {"id": 13, "name": "Tema 1 — derivate", "modname": "assign"},
                ]},
                {"id": 2, "name": "Săptămâna 2", "modules": [
                    {"id": 14, "name": "Curs 2 — continuitate", "modname": "resource"},
                ]},
            ]
        return [{"id": 3, "name": "Proiecte", "modules": [
            {"id": 21, "name": "Enunț proiect", "modname": "url"},
        ]}]

    return {"exception": "webservice_access_exception", "errorcode": "accessexception",
            "message": "Funcție necunoscută"}


# Facultatea poate avea lucrurile pornite sau oprite; testul le încearcă pe rând.
MOD = {"fel": "normal"}


class Server(BaseHTTPRequestHandler):
    def do_POST(self):                               # noqa: N802
        cale = self.path.split("?")[0]
        lungime = int(self.headers.get("Content-Length") or 0)
        camp = {k: v[0] for k, v in
                urllib.parse.parse_qs(self.rfile.read(lungime).decode("utf-8")).items()}

        fel = MOD["fel"]
        if fel == "nu_e_moodle":
            brut = b"<!doctype html><html><body>Pagina facultatii</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(brut)))
            self.end_headers()
            self.wfile.write(brut)
            return
        if fel == "ws_oprit":
            self.trimite({"exception": "moodle_exception", "errorcode": "enablewsdescription",
                          "error": "Web services are not enabled",
                          "message": "Web services are not enabled"})
            return
        if fel == "xml":
            # unele instalari arunca eroarea in XML, desi am cerut JSON: se
            # intampla inainte sa apuce sa aleaga formatul
            if cale == "/login/token.php":
                self.trimite({"error": "A lipsit un parametru obligatoriu (username)",
                              "errorcode": "missingparam"})
                return
            brut = (b'<?xml version="1.0" encoding="UTF-8" ?>\n'
                    b'<EXCEPTION class="core\\exception\\moodle_exception">\n'
                    b'<ERRORCODE>invalidtoken</ERRORCODE>\n'
                    b'<MESSAGE>Token nu este valid</MESSAGE>\n'
                    b'</EXCEPTION>')
            self.send_response(200)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(brut)))
            self.end_headers()
            self.wfile.write(brut)
            return
        if fel == "mobil_oprit":
            if cale == "/login/token.php":
                self.trimite({"error": "Mobile web service is not enabled",
                              "errorcode": "enablemobilewebservice"})
            else:
                self.trimite({"exception": "moodle_exception", "errorcode": "invalidtoken",
                              "message": "Invalid token - token not found"})
            return

        if cale == "/login/token.php":
            if camp.get("username") == UTILIZATOR and camp.get("password") == PAROLA:
                # „cheie_uitata": exact ce face Moodle-ul USM — dă o cheie, trimite
                # și emailul de rigoare, iar o clipă mai târziu spune că n-o cunoaște
                corp = {"token": CHEIE_UITATA if fel == "cheie_uitata" else CHEIE_BUNA,
                        "privatetoken": None}
            else:
                corp = {"error": "Invalid login, please try again",
                        "errorcode": "invalidlogin", "stacktrace": None}
            self.trimite(corp)
            return

        if cale != "/webservice/rest/server.php":
            self.send_error(404)
            return

        if camp.get("wstoken") != CHEIE_BUNA:
            corp = {"exception": "moodle_exception", "errorcode": "invalidtoken",
                    "message": "Invalid token - token not found"}
        else:
            corp = raspunde(camp.get("wsfunction", ""), camp)
        self.trimite(corp)

    def trimite(self, corp):
        brut = json.dumps(corp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(brut)))
        self.end_headers()
        self.wfile.write(brut)

    def log_message(self, *args):                    # fără zgomot în consolă
        pass


def porneste_moodle_fals():
    srv = HTTPServer(("127.0.0.1", 0), Server)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_port


CONT = r"""
(function () {
  var out = {};
  out.stare = (document.querySelector('#moodleContStare') || {}).textContent || '';
  out.stare_rea = document.querySelector('#moodleContStare').classList.contains('e-rau');
  out.buton_adu = !document.querySelector('#moodleAduTot').hidden;
  out.buton_deconecteaza = !document.querySelector('#moodleDeconecteaza').hidden;
  return JSON.stringify(out);
})()
"""

MATERII = r"""
(function () {
  var out = {};
  var carduri = Array.prototype.slice.call(document.querySelectorAll('.mcurs'));
  out.cate = carduri.length;
  out.materii = carduri.map(function (c) {
    c.open = true;
    var grupuri = Array.prototype.slice.call(c.querySelectorAll('.mgrup')).map(function (g) {
      return {
        cap: (g.querySelector('.mgrup__cap') || {}).textContent || '',
        randuri: Array.prototype.slice.call(g.querySelectorAll('.mgrup__rand')).map(function (r) {
          return {
            titlu: (r.querySelector('.mgrup__titlu') || {}).textContent || '',
            legatura: (r.querySelector('.mgrup__titlu.e-legatura') || {}).href || '',
            jos: (r.querySelector('.mgrup__jos') || {}).textContent || '',
            dreapta: (r.querySelector('.mgrup__dreapta') || {}).textContent || '',
            rau: r.classList.contains('e-rau')
          };
        }),
        gol: (g.querySelector('.mgrup__gol') || {}).textContent || ''
      };
    });
    return {
      nume: (c.querySelector('.mcurs__nume') || {}).textContent || '',
      rezumat: (c.querySelector('.mcurs__rezumat') || {}).textContent || '',
      grupuri: grupuri
    };
  });
  return JSON.stringify(out);
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def asteapta_aplicatia(window, secunde=40):
    for _ in range(int(secunde * 2)):
        try:
            if window.evaluate_js("!!document.querySelector('#moodleBtn')"):
                return True
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


def intra_cu_parola(window, site, utilizator, parola, asteapta=9):
    window.evaluate_js("""
        document.querySelector('#moodleSite').value = %s;
        document.querySelector('#moodleUtilizator').value = %s;
        document.querySelector('#moodleParola').value = %s;
        document.querySelector('#moodleConecteaza').click();
        'ok'
    """ % (json.dumps(site), json.dumps(utilizator), json.dumps(parola)))
    time.sleep(asteapta)


def conecteaza(window, site, cheie):
    window.evaluate_js("""
        document.querySelector('#moodleSite').value = %s;
        document.querySelector('#moodleJeton').value = %s;
        document.querySelector('#moodleConecteazaCheie').click();
        'ok'
    """ % (json.dumps(site), json.dumps(cheie)))
    time.sleep(9)


def date_de_pe_disc():
    if not app.DATA_FILE.exists():
        return {}
    return json.loads(app.DATA_FILE.read_text(encoding="utf-8"))


def probe(window):
    out = {}
    try:
        port = porneste_moodle_fals()
        site = "http://127.0.0.1:%d" % port
        out["aplicatia_a_pornit"] = asteapta_aplicatia(window)

        window.evaluate_js("document.querySelector('#moodleBtn').click(); 'ok'")
        time.sleep(1.2)
        out["nelegat_la_inceput"] = citeste(window.evaluate_js(CONT))

        # butonul care duce la pagina de export a calendarului nu are voie să
        # deschidă nimic dacă adresa nu e o adresă — spune ce lipsește
        out["export_fara_adresa"] = window.evaluate_js("""
            document.querySelector('#moodleCalendarPliant').open = true;
            document.querySelector('#moodleSite').value = 'nu e o adresa';
            document.querySelector('#moodleDeschideExport').click();
            (document.querySelector('#moodleStare') || {}).textContent
        """)

        # ---- „Verifică adresa”: spune ce e pornit, fără cont și fără cheie ----
        def verifica(fel):
            MOD["fel"] = fel
            window.evaluate_js("""
                document.querySelector('#moodleSite').value = %s;
                document.querySelector('#moodleVerifica').click();
                'ok'
            """ % json.dumps(site))
            time.sleep(3)
            return window.evaluate_js(
                "(document.querySelector('#moodleContStare') || {}).textContent")

        out["verifica_normal"] = verifica("normal")
        out["verifica_ws_oprit"] = verifica("ws_oprit")
        out["verifica_mobil_oprit"] = verifica("mobil_oprit")
        out["verifica_nu_e_moodle"] = verifica("nu_e_moodle")
        out["verifica_raspuns_xml"] = verifica("xml")
        MOD["fel"] = "normal"

        # ---- parolă greșită: mesaj pe înțeles, fără să se lege ----
        intra_cu_parola(window, site, UTILIZATOR, "parola-gresita", 4)
        out["parola_gresita"] = citeste(window.evaluate_js(CONT))
        out["campul_parolei_golit_la_esec"] = window.evaluate_js(
            "document.querySelector('#moodleParola').value === ''")

        # ---- parola bună: se leagă ȘI aduce informația, dintr-o singură apăsare ----
        intra_cu_parola(window, site, UTILIZATOR, PAROLA)
        out["dupa_conectare"] = citeste(window.evaluate_js(CONT))
        out["campul_parolei_golit"] = window.evaluate_js(
            "document.querySelector('#moodleParola').value === ''")
        out["a_adus_singur"] = window.evaluate_js(
            "document.querySelectorAll('.mcurs').length")

        # parola n-are voie sa ramana nicaieri
        out["parola_nu_e_in_browser"] = window.evaluate_js("""
            (function () {
              for (var i = 0; i < localStorage.length; i++) {
                if ((localStorage.getItem(localStorage.key(i)) || '').indexOf(%s) >= 0) return false;
              }
              return true;
            })()
        """ % json.dumps(PAROLA))

        out["dupa_aducere"] = citeste(window.evaluate_js(CONT))
        out["pe_materii"] = citeste(window.evaluate_js(MATERII))
        # la a doua materie facultatea refuză notele: restul trebuie să vină oricum
        celelalte = out["pe_materii"].get("materii") or []
        out["materia_fara_note"] = celelalte[1] if len(celelalte) > 1 else {}

        date = date_de_pe_disc()
        out["materii_in_aplicatie"] = [s["name"] for s in date.get("subjects") or []]
        din_moodle = [t for t in date.get("termene") or []
                      if (t.get("sursa") or "").startswith("moodle:tema:")]
        out["termene_din_teme"] = sorted(
            [{"titlu": t["titlu"], "tip": t["tip"], "are_materie": bool(t["subjectId"])}
             for t in din_moodle], key=lambda t: t["titlu"])
        out["cursuri_salvate"] = len((date.get("moodle") or {}).get("cursuri") or [])
        out["numele_meu_salvat"] = (date.get("moodle") or {}).get("nume", "")

        # nici cheia, nici parola n-au ce cauta in fisierul care pleaca
        # in backup si in sincronizare
        brut = app.DATA_FILE.read_text(encoding="utf-8")
        out["cheia_nu_e_in_notite"] = CHEIE_BUNA not in brut
        out["parola_nu_e_in_notite"] = PAROLA not in brut
        out["utilizatorul_tinut_minte"] = (date.get("moodle") or {}).get("utilizator") == UTILIZATOR
        out["cheia_e_in_browser"] = window.evaluate_js(
            "localStorage.getItem('uninotes.moodle-jeton') === %s" % json.dumps(CHEIE_BUNA))

        # ---- a doua aducere nu dublează nimic ----
        window.evaluate_js("document.querySelector('#moodleAduTot').click(); 'ok'")
        time.sleep(6)
        date = date_de_pe_disc()
        out["materii_dupa_a_doua"] = len(date.get("subjects") or [])
        out["termene_dupa_a_doua"] = len([t for t in date.get("termene") or []
                                          if (t.get("sursa") or "").startswith("moodle:tema:")])
        out["cursuri_dupa_a_doua"] = len((date.get("moodle") or {}).get("cursuri") or [])

        # ---- informația trebuie să fie acolo și după redeschidere ----
        window.evaluate_js("document.querySelector('#moodleDlg').close(); 'ok'")
        time.sleep(0.6)
        window.evaluate_js("document.querySelector('#moodleBtn').click(); 'ok'")
        time.sleep(1.5)
        out["la_redeschidere"] = citeste(window.evaluate_js(
            "JSON.stringify({carduri: document.querySelectorAll('.mcurs').length, "
            "stare: (document.querySelector('#moodleContStare')||{}).textContent})"))

        # ---- deconectare: cheia pleacă, informația rămâne ----
        window.evaluate_js("document.querySelector('#moodleDeconecteaza').click(); 'ok'")
        time.sleep(1)
        window.evaluate_js("""
            var b = Array.prototype.slice.call(document.querySelectorAll('dialog[open] button'));
            var d = b.filter(function (x) { return /Deconecteaz/.test(x.textContent); })[0];
            if (d) d.click();
            'ok'
        """)
        time.sleep(1.5)
        out["dupa_deconectare"] = citeste(window.evaluate_js(
            "JSON.stringify({cheie: localStorage.getItem('uninotes.moodle-jeton') || '', "
            "carduri: document.querySelectorAll('.mcurs').length})"))

        # ---- varianta cu cheia pusă de mână trebuie să meargă mai departe ----
        conecteaza(window, site, CHEIE_BUNA)
        out["cu_cheia_de_mana"] = citeste(window.evaluate_js(CONT))
        conecteaza(window, site, "cheiegresita")
        out["cheie_gresita"] = citeste(window.evaluate_js(CONT))

        # ---- chei cu drepturi tăiate: un refuz nu mai oprește totul ----
        def cu_cheie_taiata(fel):
            MOD["fel"] = fel
            conecteaza(window, site, CHEIE_BUNA)
            return citeste(window.evaluate_js(
                "JSON.stringify({stare: (document.querySelector('#moodleContStare')||{}).textContent,"
                " rau: document.querySelector('#moodleContStare').classList.contains('e-rau'),"
                " materii: Array.prototype.slice.call(document.querySelectorAll('.mcurs__nume'))"
                "   .map(function (x) { return x.textContent; })})"))

        # cheia n-are voie la lista de cursuri, dar are la cea din „Cronologie”
        out["fara_enrol"] = cu_cheie_taiata("fara_enrol")

        # nici măcar prezentarea nu merge: rămâne calendarul, și tot iese ceva
        out["doar_calendar"] = cu_cheie_taiata("doar_calendar")
        date = date_de_pe_disc()
        out["materie_din_calendar"] = any(
            s.get("name") == "Chimie Organică" for s in date.get("subjects") or [])
        out["termen_din_calendar"] = [
            t["titlu"] for t in date.get("termene") or []
            if (t.get("sursa") or "").startswith("moodle:tema:ev")]

        # cheia nu are voie nicăieri: se spune limpede ce e de făcut
        out["nimic"] = cu_cheie_taiata("nimic")

        # ---- Moodle dă cheia și o uită pe loc (cazul de la USM) ----
        # Nu e o cheie expirată și nu e vina omului: mesajul trebuie s-o spună,
        # iar drumul care rămâne — calendarul — trebuie deschis, nu căutat.
        MOD["fel"] = "cheie_uitata"
        intra_cu_parola(window, site, UTILIZATOR, PAROLA, 7)
        out["cheie_uitata"] = citeste(window.evaluate_js(
            "JSON.stringify({stare: (document.querySelector('#moodleContStare')||{}).textContent,"
            " rau: document.querySelector('#moodleContStare').classList.contains('e-rau'),"
            " calendarDeschis: !!(document.querySelector('#moodleCalendarPliant')||{}).open})"))
        # aceeași cheie, dar veche, nu are voie să dea aceeași explicație
        MOD["fel"] = "normal"
        conecteaza(window, site, "cheiegresita")
        out["cheie_veche_alt_mesaj"] = window.evaluate_js(
            "(document.querySelector('#moodleContStare')||{}).textContent")
        MOD["fel"] = "normal"

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-moodle-cont-"))
    app.DATA_FILE = app.DATA_DIR / "notite.json"
    api = app.Api()
    window = webview.create_window(
        "UniNotes",
        url="http://127.0.0.1:%d/index.html?desktop=1" % app.start_local_server(),
        js_api=api,
        width=1320,
        height=860,
        background_color="#F5F7FB",
    )
    api._window = window
    webview.start(probe, window, gui="edgechromium", private_mode=False,
                  storage_path=str(app.DATA_DIR / ".fereastra"))


if __name__ == "__main__":
    run()
