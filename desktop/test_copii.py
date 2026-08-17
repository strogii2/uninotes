"""
Verifică drumul de întoarcere la o copie, în fereastra reală — exact situația
în care ai șters din greșeală și vrei textul înapoi.

Scriem o notiță, facem o copie, stricăm notița, apoi ne întoarcem la copie și
ne uităm dacă textul chiar s-a întors. Verificăm și că starea de dinaintea
întoarcerii a fost pusă deoparte: nici pasul ăsta nu trebuie să fie fără cale
de întors.
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

TEXT = "Teorema lui Lagrange, demonstrata la seminar pe 17 august"


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def asteapta_aplicatia(window, secunde=40):
    for _ in range(int(secunde * 2)):
        try:
            if window.evaluate_js("!!document.querySelector('#copiiBtn')"):
                return True
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


def notita_de_pe_disc():
    if not app.DATA_FILE.exists():
        return {}
    date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
    return next((n for n in date.get("notes") or [] if n.get("title") == "DE PASTRAT"), {})


def probe(window):
    out = {}
    try:
        out["aplicatia_a_pornit"] = asteapta_aplicatia(window)

        # ---- o notiță la care ținem ----
        window.evaluate_js("document.querySelector('#newNoteBtn').click(); 'ok'")
        time.sleep(1.5)
        window.evaluate_js("""
            var ti = document.querySelector('#titleInput');
            ti.value = 'DE PASTRAT';
            ti.dispatchEvent(new Event('input', {bubbles: true}));
            var t = document.querySelector('#editorFlux > textarea');
            t.focus();
            t.value = %s;
            t.dispatchEvent(new Event('input', {bubbles: true}));
            'ok'
        """ % json.dumps(TEXT))
        time.sleep(2.5)
        out["textul_e_pe_disc"] = TEXT in (notita_de_pe_disc().get("content") or "")

        # ---- copie cerută anume ----
        window.evaluate_js("document.querySelector('#copiiBtn').click(); 'ok'")
        time.sleep(2)
        window.evaluate_js("document.querySelector('#copieAcum').click(); 'ok'")
        time.sleep(2.5)
        out["dupa_copie"] = citeste(window.evaluate_js(r"""
            (function () {
              var r = Array.prototype.slice.call(document.querySelectorAll('.copie'));
              return JSON.stringify({
                cate: r.length,
                primul: r.length ? (r[0].querySelector('small') || {}).textContent : ''
              });
            })()
        """))
        window.evaluate_js("document.querySelector('#copiiClose').click(); 'ok'")
        time.sleep(0.8)

        # ---- stricăm notița, ca dintr-o greșeală ----
        window.evaluate_js("""
            var t = document.querySelector('#editorFlux > textarea');
            t.focus();
            t.value = '';
            t.dispatchEvent(new Event('input', {bubbles: true}));
            'ok'
        """)
        time.sleep(2.5)
        out["textul_s_a_pierdut"] = TEXT not in (notita_de_pe_disc().get("content") or "")

        # ---- ne întoarcem la copie ----
        window.evaluate_js("document.querySelector('#copiiBtn').click(); 'ok'")
        time.sleep(2)
        window.evaluate_js("""
            var b = document.querySelector('.copie button');
            if (b) b.click();
            'ok'
        """)
        time.sleep(1.2)
        window.evaluate_js("""
            var toate = document.querySelectorAll('dialog[open] button');
            for (var i = 0; i < toate.length; i++) {
                if (/ntoarce-te/.test(toate[i].textContent)) { toate[i].click(); break; }
            }
            'ok'
        """)
        time.sleep(3)

        out["textul_s_a_intors"] = TEXT in (notita_de_pe_disc().get("content") or "")
        out["se_vede_si_in_aplicatie"] = citeste(window.evaluate_js(r"""
            (function () {
              var carduri = Array.prototype.slice.call(document.querySelectorAll('.note-card'));
              return JSON.stringify({
                notite: carduri.length,
                are_notita: carduri.some(function (c) { return /DE PASTRAT/.test(c.textContent); })
              });
            })()
        """))

        # starea de dinaintea intoarcerii trebuie sa fi fost pusa deoparte
        copii = app.Api().list_backups()
        out["cate_copii"] = len(copii)
        goale = [c for c in copii if c["notite"] is not None]
        out["exista_si_copia_dinaintea_intoarcerii"] = len(goale) >= 2

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-copii-"))
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
