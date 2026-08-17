"""
Verifică ecranul „Azi”, în fereastra reală.

Pregătim dinainte un fișier de notițe cu o oră care se ține chiar acum, una
care s-a terminat, un termen de azi și unul restant — apoi ne uităm dacă
ecranul le arată pe toate la locul lor și dacă se deosebesc între ele.
"""

import json
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import sys

# Consola Windows nu scrie diacritice implicit, iar rezultatul testului
# s-ar pierde tocmai cand ai nevoie de el.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import webview

import main as app

ACUM = datetime.now()
ZI = (ACUM.weekday())                      # 0 = luni, la fel ca in aplicatie
AZI = date.today().isoformat()
RESTANT = (date.today() - timedelta(days=3)).isoformat()
PESTE_O_LUNA = (date.today() + timedelta(days=40)).isoformat()


def ceas(delta_minute):
    t = ACUM + timedelta(minutes=delta_minute)
    return "%02d:%02d" % (t.hour, t.minute)


def seminte():
    ms = int(ACUM.timestamp() * 1000)
    return {
        "version": 1,
        "settings": {"theme": "dark", "themeSetByUser": True},
        "subjects": [{"id": "m1", "name": "Analiză Matematică", "prof": "", "color": "#2563EB"}],
        "notes": [{"id": "n1", "title": "Curs de ieri", "content": "ceva",
                   "tags": [], "createdAt": ms, "updatedAt": ms, "subjectId": "m1",
                   "pinned": False, "favorite": False, "archived": False}],
        "orar": {"entries": [
            {"id": "o1", "zi": ZI, "start": ceas(-30), "end": ceas(30),
             "materie": "Analiză Matematică", "tip": "curs", "sala": "A3",
             "profesor": "", "saptamana": "toate", "subjectId": "m1"},
            {"id": "o2", "zi": ZI, "start": ceas(-180), "end": ceas(-120),
             "materie": "Fizică", "tip": "laborator", "sala": "L2",
             "profesor": "", "saptamana": "toate", "subjectId": None},
        ]},
        "termene": [
            {"id": "t1", "titlu": "Predare azi", "data": AZI, "tip": "predare",
             "subjectId": "m1", "nota": "", "gata": False, "aminteste": [], "anuntate": []},
            {"id": "t2", "titlu": "Restanta veche", "data": RESTANT, "tip": "test",
             "subjectId": None, "nota": "", "gata": False, "aminteste": [], "anuntate": []},
            {"id": "t3", "titlu": "Departe de tot", "data": PESTE_O_LUNA, "tip": "examen",
             "subjectId": None, "nota": "", "gata": False, "aminteste": [], "anuntate": []},
        ],
        "repetitii": {},
    }


ECRAN = r"""
(function () {
  var out = {};
  out.azi_e_ales = document.querySelector('#aziBtn').classList.contains('is-active');
  out.panoul_azi_vizibil = !document.querySelector('#aziPane').hidden;
  out.lista_ascunsa = document.querySelector('#notesList').hidden;
  out.titlu = (document.querySelector('#listTitle') || {}).textContent || '';
  out.insigna = (document.querySelector('#cAzi') || {}).textContent || '';
  out.grupuri = Array.prototype.slice.call(document.querySelectorAll('.azi-grup h2'))
    .map(function (h) { return h.textContent; });
  out.randuri = Array.prototype.slice.call(document.querySelectorAll('.azi-rand'))
    .map(function (r) {
      return {
        titlu: (r.querySelector('.azi-rand__titlu') || {}).textContent || '',
        jos: (r.querySelector('.azi-rand__jos') || {}).textContent || '',
        dreapta: (r.querySelector('.azi-rand__dreapta') || {}).textContent || '',
        clasa: (r.className.match(/e-\w+/) || [''])[0]
      };
    });
  return JSON.stringify(out);
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def probe(window):
    out = {}
    try:
        for _ in range(80):
            if window.evaluate_js("!!document.querySelector('#aziBtn')"):
                break
            time.sleep(0.5)
        time.sleep(3)

        out["la_pornire"] = citeste(window.evaluate_js(ECRAN))

        # ---- „Toate notițele” ne scoate din Azi ----
        window.evaluate_js("""
            document.querySelector('.nav__item[data-filter="all"]').click();
            'ok'
        """)
        time.sleep(1.2)
        out["dupa_toate_notitele"] = citeste(window.evaluate_js(r"""
            (function () {
              return JSON.stringify({
                azi_e_ales: document.querySelector('#aziBtn').classList.contains('is-active'),
                panoul_azi_vizibil: !document.querySelector('#aziPane').hidden,
                lista_vizibila: !document.querySelector('#notesList').hidden,
                titlu: (document.querySelector('#listTitle') || {}).textContent || ''
              });
            })()
        """))

        # ---- si butonul „Azi” ne aduce inapoi ----
        window.evaluate_js("document.querySelector('#aziBtn').click(); 'ok'")
        time.sleep(1.2)
        out["dupa_intoarcere"] = citeste(window.evaluate_js(ECRAN))

        # ---- o apasare pe o notita recenta o deschide ----
        window.evaluate_js("""
            var r = Array.prototype.slice.call(document.querySelectorAll('.azi-rand'))
              .filter(function (x) { return /Curs de ieri/.test(x.textContent); })[0];
            if (r) r.click();
            'ok'
        """)
        time.sleep(1.5)
        out["a_deschis_notita"] = window.evaluate_js(
            "(document.querySelector('#titleInput') || {}).value")

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-azi-"))
    app.DATA_FILE = app.DATA_DIR / "notite.json"
    app.DATA_FILE.write_text(json.dumps(seminte(), ensure_ascii=False), encoding="utf-8")

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
