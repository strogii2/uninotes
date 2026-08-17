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
    """`aminteste` e lista etichetelor de apăsat, ex. ['Cu o zi înainte']."""
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
        var vrute = %s;
        // pornim de la ce e bifat implicit si aducem la ce cere testul
        Array.prototype.slice.call(d.querySelectorAll('#termenAminteste .optiune'))
          .forEach(function (b) {
            var trebuie = vrute.indexOf(b.textContent.trim()) >= 0;
            if (b.classList.contains('is-active') !== trebuie) b.click();
          });
        'ok'
    """ % (json.dumps(titlu), json.dumps(data), json.dumps(nota), json.dumps(aminteste)))
    time.sleep(0.6)
    window.evaluate_js("""
        document.querySelector('#termenModal button[type="submit"]').click();
        'ok'
    """)
    time.sleep(1.5)


STARE = r"""
(function () {
  var out = {};
  var randuri = Array.prototype.slice.call(document.querySelectorAll('.termen'));
  out.termene = randuri.map(function (r) {
    var c = r.querySelector('.termen__clopot');
    return {
      titlu: (r.querySelector('.termen__titlu') || {}).textContent || '',
      clopot: !!c,
      cate: c ? ((c.querySelector('em') || {}).textContent || '1') : '',
      explicatie: c ? (c.getAttribute('title') || '') : ''
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
        # in fereastra de Windows, notificarile paginii sunt refuzate din start:
        # amintirile trebuie sa plece prin sistem, nu prin browser
        out["browserul_refuza_notificarile"] = window.evaluate_js(
            "(typeof Notification === 'undefined') ? 'lipseste' : Notification.permission")
        window.evaluate_js(FALS)
        window.evaluate_js("document.querySelector('#termeneBtn').click(); 'ok'")
        time.sleep(1.2)

        # Examenul are TREI amintiri deodata; e la 30 de zile, deci acum
        # trebuie sa sune doar cea de o saptamana? nu — nici aceea: 30 > 7.
        adauga(window, "Predare proiect POO, partea a II-a", PESTE_2,
               ["Cu 3 zile înainte", "În ziua respectivă"], "de predat pe platformă")
        adauga(window, "Examen Analiză", PESTE_30,
               ["Cu o zi înainte", "Cu 3 zile înainte", "Cu o săptămână înainte"])
        adauga(window, "Referat vechi", ACUM_5, ["Cu o zi înainte"])

        out["dupa_adaugare"] = citeste(window.evaluate_js(STARE))

        date_disc = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
        termene = {t["titlu"]: t for t in date_disc.get("termene") or []}
        out["salvat_aminteste"] = {t["titlu"]: t.get("aminteste") for t in termene.values()}
        out["anuntate_la_cel_apropiat"] = termene.get(
            "Predare proiect POO, partea a II-a", {}).get("anuntate")
        out["nu_a_anuntat_cel_departe"] = not termene.get("Examen Analiză", {}).get("anuntate")
        out["nu_a_anuntat_cel_trecut"] = not termene.get("Referat vechi", {}).get("anuntate")

        # ---- a doua trecere, in aceeasi zi, nu mai anunta inca o data ----
        window.evaluate_js("window.__anunturi = []; 'ok'")
        adauga(window, "Fara amintire", PESTE_2, [])
        out["a_doua_oara"] = citeste(window.evaluate_js(STARE))

        # ---- optiunea care le prinde pe toate deodata ----
        def toate(eticheta):
            window.evaluate_js("""
                var b = Array.prototype.slice.call(
                    document.querySelectorAll('#toateAmintirile .optiune'))
                  .filter(function (x) { return x.textContent.trim() === %s; })[0];
                if (b) b.click();
                'ok'
            """ % json.dumps(eticheta))
            time.sleep(2)
            date_disc = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            return {t["titlu"]: t.get("aminteste") for t in date_disc.get("termene") or []}

        out["starea_butoanelor_la_toate"] = citeste(window.evaluate_js(r"""
            (function () {
              return JSON.stringify(Array.prototype.slice.call(
                document.querySelectorAll('#toateAmintirile .optiune')).map(function (b) {
                  return {
                    text: b.textContent.trim(),
                    aprins: b.classList.contains('is-active'),
                    partial: b.classList.contains('e-partial')
                  };
                }));
            })()
        """))
        out["dupa_pus_la_toate"] = toate("Cu o săptămână înainte")
        out["dupa_scos_de_la_toate"] = toate("Cu o săptămână înainte")

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

        # amintirile au plecat prin sistem, nu prin Notification al paginii
        out["anunturi_prin_sistem"] = app.ANUNTURI_SISTEM
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

    # Notificarea adevărată de Windows ar umple ecranul cu bule în timpul
    # testului; o înlocuim cu o însemnare, ca să vedem totuși ce s-a cerut.
    app.ANUNTURI_SISTEM = []

    def notifica(self, titlu, corp):
        app.ANUNTURI_SISTEM.append({"titlu": titlu, "corp": corp})
        return True

    app.Api.notifica = notifica

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
