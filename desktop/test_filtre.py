"""
Verifică filtrarea după mai multe materii deodată, în fereastra reală:
alegerea se adună, notițele afișate sunt exact ale materiilor alese,
iar renunțarea aduce totul înapoi.
"""

import json
import tempfile
import time
from pathlib import Path

import webview

import main as app


NUMARA = r"""
(function () {
  var out = {};
  var carduri = Array.prototype.slice.call(document.querySelectorAll('.note-card'));
  out.notite_afisate = carduri.length;
  out.titluri = carduri.map(function (c) {
    var t = c.querySelector('.note-card__title');
    return (t ? t.textContent : c.textContent).trim().slice(0, 40);
  });
  out.cap_de_lista = document.querySelector('#listTitle').textContent;
  out.materii_aprinse = document.querySelectorAll('.subject.is-active').length;
  out.rand_alese = (document.querySelector('.subject-alese') || {}).textContent || '';
  return JSON.stringify(out);
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def apasa_materia(window, nume):
    return window.evaluate_js("""
        (function () {
          var toate = Array.prototype.slice.call(document.querySelectorAll('.subject'));
          var b = toate.filter(function (s) {
            var n = s.querySelector('.subject__name');
            return n && n.textContent.indexOf('%s') >= 0;
          })[0];
          if (!b) return false;
          b.click();
          return true;
        })()
    """ % nume)


def probe(window):
    out = {}
    try:
        time.sleep(5)
        out["materii_in_bara"] = window.evaluate_js(
            "Array.prototype.slice.call(document.querySelectorAll('.subject__name'))"
            ".map(function (n) { return n.textContent; })")
        out["la_inceput"] = citeste(window.evaluate_js(NUMARA))

        out["apasat_prima"] = apasa_materia(window, "Analiz")
        time.sleep(1)
        out["o_materie"] = citeste(window.evaluate_js(NUMARA))

        out["apasat_a_doua"] = apasa_materia(window, "Fizic")
        time.sleep(1)
        out["doua_materii"] = citeste(window.evaluate_js(NUMARA))

        out["apasat_a_treia"] = apasa_materia(window, "Obiecte")
        time.sleep(1)
        out["trei_materii"] = citeste(window.evaluate_js(NUMARA))

        # a doua apăsare pe aceeași materie o scoate din filtru
        apasa_materia(window, "Fizic")
        time.sleep(1)
        out["dupa_scoatere"] = citeste(window.evaluate_js(NUMARA))

        # notița nouă nu primește materie când sunt alese mai multe
        window.evaluate_js("document.querySelector('#newNoteBtn').click(); 'ok'")
        time.sleep(2)
        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            noua = (date.get("notes") or [{}])[0]
            out["notita_noua_fara_materie"] = not noua.get("subjectId")

        # „Renunță” aduce toate notițele înapoi
        window.evaluate_js("""
            var b = Array.prototype.slice.call(
                document.querySelectorAll('.subject-alese__btn'))
              .filter(function (x) { return /Renun/.test(x.textContent); })[0];
            if (b) b.click();
            'ok'
        """)
        time.sleep(1.5)
        out["dupa_renuntare"] = citeste(window.evaluate_js(NUMARA))

        out["erori"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                      # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-filtre-"))
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
