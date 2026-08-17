"""
Verifică aducerea cursurilor și a termenelor din Moodle, în fereastra reală.

Servim local un calendar scris exact ca cele exportate de Moodle — cu rânduri
rupte în două, virgule scrise „\\,”, evenimente pe toată ziua și ore în UTC —
și urmărim tot drumul: citire, previzualizare, adăugare, apoi o a doua aducere
care nu trebuie să dubleze nimic.
"""

import json
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sys

# Consola Windows nu scrie diacritice implicit, iar rezultatul testului
# s-ar pierde tocmai cand ai nevoie de el.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import webview

import main as app


def calendar_moodle(data_temei: str) -> str:
    """
    Un export Moodle adevărat: rândul lung se rupe și se continuă cu spațiu,
    virgula din numele cursului e scrisă „\\,”, iar orele vin în UTC.
    """
    return (
        "BEGIN:VCALENDAR\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Moodle Pty Ltd//NONSGML Moodle Version 2024042200//EN\r\n"
        "METHOD:PUBLISH\r\n"
        # 1. temă la o materie care există deja în aplicație
        "BEGIN:VEVENT\r\n"
        "UID:tema1@moodle.test\r\n"
        "SUMMARY:Tema 1 — derivate is due\r\n"
        "DESCRIPTION:Predați rezolvarea în format PDF.\r\n"
        "DTSTAMP:20260817T120000Z\r\n"
        "DTSTART:" + data_temei + "T120000Z\r\n"
        "CATEGORIES:Analiză Matematică\r\n"
        "END:VEVENT\r\n"
        # 2. examen la o materie nouă, cu numele rupt pe două rânduri
        "BEGIN:VEVENT\r\n"
        "UID:examen1@moodle.test\r\n"
        "SUMMARY:Examen final Structuri de Date\r\n"
        "DTSTAMP:20260817T120000Z\r\n"
        "DTSTART:20261120T080000Z\r\n"
        "CATEGORIES:Structuri de Date si Algo\r\n"
        " ritmi\r\n"
        "END:VEVENT\r\n"
        # 3. eveniment pe toată ziua, cu virgulă scrisă in numele cursului
        "BEGIN:VEVENT\r\n"
        "UID:colocviu1@moodle.test\r\n"
        "SUMMARY:Colocviu laborator\r\n"
        "DTSTAMP:20260817T120000Z\r\n"
        "DTSTART;VALUE=DATE:20261015\r\n"
        "CATEGORIES:Fizică Generală\\, partea a II-a\r\n"
        "END:VEVENT\r\n"
        # 4. eveniment personal, fără curs
        "BEGIN:VEVENT\r\n"
        "UID:personal1@moodle.test\r\n"
        "SUMMARY:Consultații\r\n"
        "DTSTAMP:20260817T120000Z\r\n"
        "DTSTART:20261002T140000Z\r\n"
        "END:VEVENT\r\n"
        # 5. rand fara data: trebuie sarit, nu sa strice tot calendarul
        "BEGIN:VEVENT\r\n"
        "UID:stricat@moodle.test\r\n"
        "SUMMARY:Eveniment fără dată\r\n"
        "END:VEVENT\r\n"
        # 6. termen din semestrul trecut: se vede, dar nu se bifeaza singur
        "BEGIN:VEVENT\r\n"
        "UID:vechi1@moodle.test\r\n"
        "SUMMARY:Predare referat is due\r\n"
        "DTSTAMP:20250901T120000Z\r\n"
        "DTSTART:20251110T120000Z\r\n"
        "CATEGORIES:Analiză Matematică\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


CALENDARE = {
    "/prima.ics": calendar_moodle("20260901"),
    "/mutat.ics": calendar_moodle("20260908"),      # aceleași UID-uri, altă dată
}


class Server(BaseHTTPRequestHandler):
    def do_GET(self):                                # noqa: N802
        cale = self.path.split("?")[0]
        if cale == "/nuecalendar.ics":
            corp = b"<html>Autentificare</html>"     # ce intoarce Moodle daca nu esti logat
        elif cale in CALENDARE:
            corp = CALENDARE[cale].encode("utf-8")
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/calendar; charset=utf-8")
        self.send_header("Content-Length", str(len(corp)))
        self.end_headers()
        self.wfile.write(corp)

    def log_message(self, *args):                    # fără zgomot în consolă
        pass


def porneste_calendarul():
    srv = HTTPServer(("127.0.0.1", 0), Server)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_port


def zi_locala(iso_utc: str) -> str:
    """Ce zi e la noi când calendarul spune ora asta în UTC."""
    d = datetime.strptime(iso_utc, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return d.astimezone().strftime("%Y-%m-%d")


PREVIZUALIZARE = r"""
(function () {
  var out = {};
  out.stare = (document.querySelector('#moodleStare') || {}).textContent || '';
  out.stare_rea = !!(document.querySelector('#moodleStare') || {classList: {contains: function () {}}})
                    .classList.contains('e-rau');
  out.materii_noi = Array.prototype.slice.call(document.querySelectorAll('.moodle__materie'))
                      .map(function (e) { return e.textContent; });
  out.randuri = Array.prototype.slice.call(document.querySelectorAll('.mrand')).map(function (r) {
    return {
      stare: (r.className.match(/mrand--(\w+)/) || [])[1] || '',
      titlu: (r.querySelector('.mrand__titlu') || {}).textContent || '',
      jos: (r.querySelector('.mrand__jos') || {}).textContent || '',
      bifat: !!(r.querySelector('input') || {}).checked
    };
  });
  out.buton_adauga = !document.querySelector('#moodleAplica').hidden;
  out.sumar = (document.querySelector('#moodleSumar') || {}).textContent || '';
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


def adu(window, url):
    window.evaluate_js("""
        var i = document.querySelector('#moodleUrl');
        i.value = %s;
        document.querySelector('#moodleAdu').click();
        'ok'
    """ % json.dumps(url))
    time.sleep(2.5)


def date_de_pe_disc():
    if not app.DATA_FILE.exists():
        return {}
    return json.loads(app.DATA_FILE.read_text(encoding="utf-8"))


def probe(window):
    out = {}
    try:
        port = porneste_calendarul()
        baza = "http://127.0.0.1:%d" % port
        out["aplicatia_a_pornit"] = asteapta_aplicatia(window)

        window.evaluate_js("document.querySelector('#moodleBtn').click(); 'ok'")
        time.sleep(1.2)
        out["dialogul_se_deschide"] = window.evaluate_js(
            "document.querySelector('#moodleDlg').open")

        # ---- o adresă care nu întoarce un calendar trebuie spusă pe șleau ----
        adu(window, baza + "/nuecalendar.ics")
        gresit = citeste(window.evaluate_js(PREVIZUALIZARE))
        out["adresa_gresita"] = {"stare": gresit["stare"], "e_rau": gresit["stare_rea"],
                                 "randuri": len(gresit["randuri"])}

        # ---- calendarul adevărat ----
        adu(window, baza + "/prima.ics")
        out["previzualizare"] = citeste(window.evaluate_js(PREVIZUALIZARE))
        out["zi_asteptata_tema"] = zi_locala("20260901T120000Z")
        out["zi_asteptata_examen"] = zi_locala("20261120T080000Z")

        # „Bifează tot” prinde și trecutul, „Nicio bifă” le lasă pe toate
        window.evaluate_js("""
            var b = Array.prototype.slice.call(document.querySelectorAll('.moodle__bifa'));
            b.filter(function (x) { return /Bifeaz/.test(x.textContent); })[0].click();
            'ok'
        """)
        time.sleep(0.8)
        out["dupa_bifeaza_tot"] = citeste(window.evaluate_js(
            "JSON.stringify(Array.prototype.slice.call("
            "document.querySelectorAll('.mrand input')).map(function (i) { return i.checked; }))"))
        window.evaluate_js("""
            var b = Array.prototype.slice.call(document.querySelectorAll('.moodle__bifa'));
            b.filter(function (x) { return /Nicio/.test(x.textContent); })[0].click();
            'ok'
        """)
        time.sleep(0.8)
        out["dupa_nicio_bifa"] = citeste(window.evaluate_js(
            "JSON.stringify(Array.prototype.slice.call("
            "document.querySelectorAll('.mrand input')).map(function (i) { return i.checked; }))"))

        # înapoi la ce se alegea singur, ca restul testului să meargă mai departe
        adu(window, baza + "/prima.ics")

        # nimic nu trebuie scris pe disc înainte de „Adaugă”
        inainte = date_de_pe_disc()
        out["nimic_pana_la_confirmare"] = not any(
            (t.get("sursa") or "").startswith("moodle:") for t in inainte.get("termene") or [])

        window.evaluate_js("document.querySelector('#moodleAplica').click(); 'ok'")
        time.sleep(2.5)

        date = date_de_pe_disc()
        materii = [s["name"] for s in date.get("subjects") or []]
        din_moodle = [t for t in date.get("termene") or []
                      if (t.get("sursa") or "").startswith("moodle:")]
        out["materii_dupa"] = materii
        out["termene_aduse"] = sorted(
            [{"titlu": t["titlu"], "data": t["data"], "tip": t["tip"],
              "are_materie": bool(t["subjectId"]), "nota": t["nota"]} for t in din_moodle],
            key=lambda t: t["data"])
        out["url_tinut_minte"] = (date.get("moodle") or {}).get("url", "").endswith("/prima.ics")

        # materia care exista deja nu trebuie creată a doua oară
        out["fara_materie_dublata"] = materii.count("Analiză Matematică") == 1
        # cursul cu virgulă în nume s-a potrivit la „Fizică Generală”, nu s-a creat altul
        out["cate_materii"] = len(materii)

        # ---- a doua aducere a aceluiași calendar nu schimbă nimic ----
        window.evaluate_js("document.querySelector('#moodleBtn').click(); 'ok'")
        time.sleep(1.2)
        adu(window, baza + "/prima.ics")
        out["a_doua_oara"] = citeste(window.evaluate_js(PREVIZUALIZARE))

        # ---- același calendar, cu un termen mutat: se înnoiește, nu se dublează ----
        adu(window, baza + "/mutat.ics")
        mutat = citeste(window.evaluate_js(PREVIZUALIZARE))
        out["dupa_mutare"] = {"stari": [r["stare"] for r in mutat["randuri"]],
                              "bifate": [r["bifat"] for r in mutat["randuri"]]}
        window.evaluate_js("document.querySelector('#moodleAplica').click(); 'ok'")
        time.sleep(2.5)

        date = date_de_pe_disc()
        din_moodle = [t for t in date.get("termene") or []
                      if (t.get("sursa") or "").startswith("moodle:")]
        out["termene_dupa_mutare"] = len(din_moodle)
        tema = next((t for t in din_moodle if "Tema 1" in t["titlu"]), {})
        out["tema_s_a_mutat"] = tema.get("data")
        out["zi_asteptata_dupa_mutare"] = zi_locala("20260908T120000Z")
        out["materii_dupa_mutare"] = len(date.get("subjects") or [])

        # ---- fișier .ics ales de pe disc, nu de pe internet ----
        window.evaluate_js("document.querySelector('#moodleBtn').click(); 'ok'")
        time.sleep(1.2)
        window.evaluate_js("""
            var t = %s;
            var dt = new DataTransfer();
            dt.items.add(new File([t], 'calendar.ics', {type: 'text/calendar'}));
            var inp = document.querySelector('#moodleInput');
            inp.files = dt.files;
            inp.dispatchEvent(new Event('change', {bubbles: true}));
            'ok'
        """ % json.dumps(CALENDARE["/prima.ics"]))
        time.sleep(2)
        dinFisier = citeste(window.evaluate_js(PREVIZUALIZARE))
        out["din_fisier"] = {"randuri": len(dinFisier["randuri"]),
                             "stari": [r["stare"] for r in dinFisier["randuri"]]}
        window.evaluate_js("document.querySelector('#moodleDlg').close(); 'ok'")

        out["insigna"] = window.evaluate_js(
            "(document.querySelector('#cMoodle') || {}).textContent")
        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-moodle-"))
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
