"""
Verifică meniul de pe telefon: butonul stă fix, iar meniul nu mai vine
alunecând din stânga.

Partea care contează cel mai mult e ultima: un meniu făcut nevăzut prin
transparență, dar rămas la locul lui, ar înghiți apăsările destinate paginii
de dedesubt — ai apăsa pe o notiță și n-ar răspunde nimeni, fără niciun semn
că ceva e în neregulă.
"""

import json
import tempfile
import time
from pathlib import Path

import sys

# Consola Windows nu scrie diacritice implicit, iar rezultatul testului
# s-ar pierde tocmai cand ai nevoie de el.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import webview

import main as app

MASOARA = r"""
(function () {
  var b = document.querySelector('#menuBtn');
  var s = document.querySelector('#sidebar');
  var rb = b.getBoundingClientRect();
  var rs = s.getBoundingClientRect();
  var st = getComputedStyle(s);
  var card = document.querySelector('.note-card');

  // cine primeste apasarea in coltul din stanga-sus al listei, acolo unde
  // sta butonul, si in mijlocul paginii, unde stau notitele
  function cine(x, y) {
    var el = document.elementFromPoint(x, y);
    if (!el) return 'nimic';
    if (el.closest('#sidebar')) return 'meniu';
    if (el.closest('#menuBtn')) return 'buton';
    if (el.closest('#scrim')) return 'perdea';
    if (el.closest('.note-card')) return 'notita';
    if (el.closest('.azi-rand')) return 'rand azi';
    return el.tagName.toLowerCase() + '.' + (el.className || '').toString().split(' ')[0];
  }

  return JSON.stringify({
    buton_x: Math.round(rb.left),
    buton_y: Math.round(rb.top),
    meniu_x: Math.round(rs.left),
    meniu_opacitate: st.opacity,
    meniu_vizibilitate: st.visibility,
    meniu_deplasare: st.transform,
    card_x: card ? Math.round(card.getBoundingClientRect().left) : null,
    la_buton: cine(rb.left + rb.width / 2, rb.top + rb.height / 2),
    la_mijloc: cine(Math.round(window.innerWidth / 2), Math.round(window.innerHeight / 2)),
    ecran: document.documentElement.clientWidth
  });
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def probe(window):
    out = {}
    try:
        for _ in range(80):
            if window.evaluate_js("!!document.querySelector('#menuBtn')"):
                break
            time.sleep(0.5)
        time.sleep(3)
        window.resize(400, 850)
        time.sleep(2.5)
        window.evaluate_js(
            "document.querySelector('.nav__item[data-filter=\"all\"]').click(); 'ok'")
        time.sleep(1.5)

        out["inchis"] = citeste(window.evaluate_js(MASOARA))

        window.evaluate_js("document.querySelector('#menuBtn').click(); 'ok'")
        time.sleep(1.2)
        out["deschis"] = citeste(window.evaluate_js(MASOARA))

        window.evaluate_js("document.querySelector('#scrim').click(); 'ok'")
        time.sleep(1.2)
        out["inchis_din_nou"] = citeste(window.evaluate_js(MASOARA))

        # se poate apasa pe o notita dupa ce meniul s-a inchis?
        out["notita_raspunde"] = window.evaluate_js("""
            (function () {
              var c = document.querySelector('.note-card');
              if (!c) return 'nicio notita';
              c.click();
              return document.querySelector('#app').dataset.pane;
            })()
        """)

        i, d = out["inchis"], out["deschis"]
        out["butonul_nu_se_misca"] = i["buton_x"] == d["buton_x"] == out["inchis_din_nou"]["buton_x"]
        out["meniul_nu_aluneca"] = i["meniu_x"] == d["meniu_x"]
        # inchis, meniul n-are voie sa stea peste pagina: nici la buton, nici
        # in mijloc, unde sunt notitele
        out["meniul_inchis_nu_prinde_apasari"] = (
            i["la_buton"] == "buton" and i["la_mijloc"] != "meniu"
            and out["notita_raspunde"] == "editor")
        out["butonul_aliniat_cu_lista"] = (
            i["card_x"] is not None and abs(i["buton_x"] - i["card_x"]) <= 2)

        # ---- intoarcerea din printare nu trebuie sa lase ecranul micsorat ----
        out["viewport_inainte"] = window.evaluate_js(
            "document.querySelector('meta[name=\"viewport\"]').getAttribute('content')")
        window.evaluate_js("""
            var n = document.querySelector('#notesList');
            if (n) n.scrollTop = 120;
            window.dispatchEvent(new Event('beforeprint'));
            window.dispatchEvent(new Event('afterprint'));
            'ok'
        """)
        time.sleep(0.15)
        out["viewport_in_timpul_reasezarii"] = window.evaluate_js(
            "document.querySelector('meta[name=\"viewport\"]').getAttribute('content')")
        time.sleep(1.2)
        out["viewport_dupa"] = window.evaluate_js(
            "document.querySelector('meta[name=\"viewport\"]').getAttribute('content')")
        out["viewport_pus_la_loc"] = out["viewport_dupa"] == out["viewport_inainte"]
        out["a_fortat_reasezarea"] = "maximum-scale=1" in (out["viewport_in_timpul_reasezarii"] or "")
        out["foaia_de_tipar_golita"] = window.evaluate_js(
            "document.querySelector('#printArea').innerHTML.length === 0")

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-meniu-"))
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
