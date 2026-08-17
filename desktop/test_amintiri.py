"""
Verifică amintirile pentru termene, în fereastra reală: alegerea „cu câte zile
înainte”, clopoțelul din listă, notificarea care chiar pleacă (o singură dată
pe zi) și fișierul de calendar cu alarme, care e singurul lucru ce sună pe
telefon și cu aplicația închisă.

Nu cerem niciodată permisiunea adevărată de notificări — ar deschide o fereastră
a sistemului care ar bloca testul. Punem în loc un Notification prefăcut, care
scrie într-o listă ce i s-a cerut să arate.
"""

import json
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

import sys

# Consola Windows nu scrie diacritice implicit, iar rezultatul testului
# s-ar pierde tocmai cand ai nevoie de el.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import webview

import main as app

AZI = date.today()
PESTE_2 = (AZI + timedelta(days=2)).isoformat()
PESTE_30 = (AZI + timedelta(days=30)).isoformat()
ACUM_5 = (AZI - timedelta(days=5)).isoformat()

# Notification prefacut: nu deschide nimic, doar tine minte ce i s-a cerut.
FALS = r"""
(function () {
  window.__anunturi = [];
  function F(titlu, opt) { window.__anunturi.push({titlu: titlu, corp: (opt || {}).body}); }
  F.permission = 'granted';
  F.requestPermission = function () { return Promise.resolve('granted'); };
  window.Notification = F;
  return 'ok';
})()
"""


def adauga(window, titlu, data, aminteste, nota=""):
    window.evaluate_js("""
        document.querySelector('#termenAddBtn').click();
        'ok'
    """)
    time.sleep(0.8)
    window.evaluate_js("""
        var d = document.querySelector('#termenModal');
        d.querySelector('#termenTitlu').value = %s;
        d.querySelector('#termenData').value = %s;
        d.querySelector('#termenNota').value = %s;
        var a = d.querySelector('#termenAminteste');
        a.value = %s;
        a.dispatchEvent(new Event('change', {bubbles: true}));
        d.querySelector('button[type="submit"]').click();
        'ok'
    """ % (json.dumps(titlu), json.dumps(data), json.dumps(nota), json.dumps(aminteste)))
    time.sleep(1.5)


STARE = r"""
(function () {
  var out = {};
  var randuri = Array.prototype.slice.call(document.querySelectorAll('.termen'));
  out.termene = randuri.map(function (r) {
    return {
      titlu: (r.querySelector('.termen__titlu') || {}).textContent || '',
      clopot: !!r.querySelector('.termen__clopot')
    };
  });
  var bara = document.querySelector('#termeneAnuntBara');
  out.bara_vizibila = !!bara && !bara.hidden;
  out.bara_text = (document.querySelector('#termeneAnuntText') || {}).textContent || '';
  out.anunturi = window.__anunturi || [];
  return JSON.stringify(out);
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def asteapta_aplicatia(window, secunde=40):
    for _ in range(int(secunde * 2)):
        try:
            if window.evaluate_js("!!document.querySelector('#termeneBtn')"):
                return True
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


def probe(window):
    out = {}
    try:
        out["aplicatia_a_pornit"] = asteapta_aplicatia(window)
        window.evaluate_js(FALS)
        window.evaluate_js("document.querySelector('#termeneBtn').click(); 'ok'")
        time.sleep(1.2)

        # trei termene: unul aproape cu amintire, unul departe, unul trecut
        adauga(window, "Predare proiect POO, partea a II-a", PESTE_2, "3",
               "de predat pe platformă")
        adauga(window, "Examen Analiză", PESTE_30, "1")
        adauga(window, "Referat vechi", ACUM_5, "1")

        out["dupa_adaugare"] = citeste(window.evaluate_js(STARE))

        # ---- notificarile: numai cele intrate in fereastra de amintire ----
        date_disc = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
        termene = {t["titlu"]: t for t in date_disc.get("termene") or []}
        out["salvat_aminteste"] = {t["titlu"]: t.get("aminteste") for t in termene.values()}
        out["anuntat_pentru_cel_apropiat"] = bool(
            termene.get("Predare proiect POO, partea a II-a", {}).get("anuntat"))
        out["nu_a_anuntat_cel_departe"] = not termene.get("Examen Analiză", {}).get("anuntat")
        out["nu_a_anuntat_cel_trecut"] = not termene.get("Referat vechi", {}).get("anuntat")

        # ---- a doua trecere, in aceeasi zi, nu mai anunta inca o data ----
        window.evaluate_js("window.__anunturi = []; 'ok'")
        adauga(window, "Fara amintire", PESTE_2, "")
        out["a_doua_oara"] = citeste(window.evaluate_js(STARE))

        # ---- fisierul de calendar ----
        window.evaluate_js("document.querySelector('#termeneCalendar').click(); 'ok'")
        time.sleep(3)
        ics = Path(app.CALE_SALVATA[0]) if app.CALE_SALVATA else None
        if ics and ics.exists():
            # newline="" ca sa vedem capetele de rand chiar asa cum sunt pe disc
            with open(ics, encoding="utf-8", newline="") as f:
                text = f.read()
            out["ics"] = {
                "evenimente": text.count("BEGIN:VEVENT"),
                "alarme": text.count("BEGIN:VALARM"),
                "pe_toata_ziua": text.count("DTSTART;VALUE=DATE:"),
                "trigger_3_zile": "TRIGGER:-P3DT15H" in text,
                "trigger_1_zi": "TRIGGER:-P1DT15H" in text,
                "virgula_scapata": "\\," in text,
                "capete_de_rand_curate": "\r\r" not in text and text.count("\r\n") > 10,
                "randuri_prea_lungi": [r[:60] for r in text.split("\r\n") if len(r) > 75],
                "are_final": text.rstrip().endswith("END:VCALENDAR"),
                "termenul_trecut_sarit": "Referat vechi" not in text,
            }
        else:
            out["ics"] = "fisierul nu s-a scris"

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-amintiri-"))
    app.DATA_FILE = app.DATA_DIR / "notite.json"

    # „Salvează ca” ar deschide o fereastră a sistemului, care ar bloca testul:
    # o înlocuim cu o scriere directă și ținem minte unde a scris.
    app.CALE_SALVATA = []

    def save_file(self, suggested_name, content):
        cale = app.DATA_DIR / suggested_name
        # ca in punte: fara traducerea capetelor de rand
        with open(cale, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        app.CALE_SALVATA.append(str(cale))
        return str(cale)

    app.Api.save_file = save_file

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
