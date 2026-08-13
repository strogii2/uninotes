"""
Verifică drumul complet al unei poze în fereastra reală: alegerea fișierului,
comprimarea, salvarea pe disc și — partea care lipsea — apariția ei în notiță,
printre rânduri, în timp ce scrii.
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


# o imagine mică, făcută în pagină, ca să nu depindem de un fișier de pe disc
ALEGE_POZA = r"""
(async function () {
  var out = {};
  var c = document.createElement('canvas');
  c.width = 240; c.height = 160;
  var g = c.getContext('2d');
  g.fillStyle = '#2563EB'; g.fillRect(0, 0, 240, 160);
  g.fillStyle = '#fff'; g.fillRect(30, 30, 90, 60);
  var blob = await new Promise(function (r) { c.toBlob(r, 'image/png'); });
  out.poza_pregatita = !!blob && blob.size > 0;

  var inp = document.querySelector('#pozaInput');
  out.input_exista = !!inp;
  if (!inp) return JSON.stringify(out);

  var dt = new DataTransfer();
  dt.items.add(new File([blob], 'tabla.png', {type: 'image/png'}));
  inp.files = dt.files;
  inp.dispatchEvent(new Event('change', {bubbles: true}));
  return JSON.stringify(out);
})()
"""

STARE = r"""
(function () {
  var out = {};
  var casete = Array.prototype.slice.call(
    document.querySelectorAll('#editorFlux > textarea'));
  out.casete = casete.length;
  out.text_scris = casete.map(function (t) { return t.value; }).join('|');

  // ce vede omul cat timp scrie
  out.editor_vizibil = !document.querySelector('#editorFlux').hidden;
  var imgs = Array.prototype.slice.call(document.querySelectorAll('#editorFlux img'));
  out.imagini_in_editor = imgs.length;
  out.imagini_cu_sursa = imgs.filter(function (im) {
    return im.src && im.src.length > 40;
  }).length;
  out.imagini_vizibile = imgs.filter(function (im) {
    var r = im.getBoundingClientRect();
    return r.width > 20 && r.height > 20;
  }).length;
  out.marcaj_ramas_in_text = /uninotes:/.test(out.text_scris);
  out.buton_stergere = document.querySelectorAll('#editorFlux .ed-media__btn').length;
  out.lipsa_afisata = document.querySelectorAll('.md-poza-lipsa').length;
  return JSON.stringify(out);
})()
"""


def citeste(valoare):
    """WebView2 întoarce uneori text, alteori obiectul deja desfăcut."""
    return json.loads(valoare) if isinstance(valoare, (str, bytes, bytearray)) else valoare


def probe(window):
    out = {}
    try:
        time.sleep(5)
        window.evaluate_js("document.querySelector('#newNoteBtn').click(); 'ok'")
        time.sleep(1)

        # întâi puțin text, ca poza să aibă unde să se așeze
        window.evaluate_js("""
            var ti = document.querySelector('#titleInput');
            ti.value = 'PROBA POZA';
            ti.dispatchEvent(new Event('input', {bubbles: true}));
            var t = document.querySelector('#editorFlux > textarea');
            t.focus();
            t.value = 'Curs 3 — teorema lui Lagrange';
            t.dispatchEvent(new Event('input', {bubbles: true}));
            t.setSelectionRange(t.value.length, t.value.length);
            'ok'
        """)
        time.sleep(1)

        out.update(citeste(window.evaluate_js(ALEGE_POZA)) or {})
        time.sleep(3)

        out["dupa_inserare"] = citeste(window.evaluate_js(STARE))

        # la lățime de telefon imaginea trebuie să încapă, nu să iasă din ecran
        window.resize(400, 850)
        time.sleep(2)
        out["pe_telefon"] = citeste(window.evaluate_js(r"""
            (function () {
              var im = document.querySelector('#editorFlux img');
              var W = document.documentElement.clientWidth;
              if (!im) return JSON.stringify({imagine: false});
              var r = im.getBoundingClientRect();
              return JSON.stringify({
                imagine: true,
                ecran: W,
                latime_imagine: Math.round(r.width),
                incape: r.left >= -2 && r.right <= W + 2,
                se_vede: r.width > 20 && r.height > 20
              });
            })()
        """))
        window.resize(1320, 860)
        time.sleep(1.5)

        imagini = app.DATA_DIR / "imagini"
        out["fisiere_pe_disc"] = sorted(p.name for p in imagini.glob("*")) if imagini.exists() else []

        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            nota = next((n for n in date.get("notes") or [] if n.get("title") == "PROBA POZA"), {})
            out["salvat_pe_disc"] = "uninotes:" in (nota.get("content") or "")
            out["textul_a_ramas"] = "Lagrange" in (nota.get("content") or "")

        # și textul scris după poză trebuie să ajungă tot în notiță
        window.evaluate_js("""
            var c = document.querySelectorAll('#editorFlux > textarea');
            var ultim = c[c.length - 1];
            ultim.focus();
            ultim.value = 'concluzie: derivata se anuleaza';
            ultim.dispatchEvent(new Event('input', {bubbles: true}));
            'ok'
        """)
        time.sleep(2.5)
        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            nota = next((n for n in date.get("notes") or [] if n.get("title") == "PROBA POZA"), {})
            out["text_dupa_poza_salvat"] = "concluzie" in (nota.get("content") or "")
            out["ordinea_pastrata"] = (nota.get("content") or "").find("Lagrange") < \
                                      (nota.get("content") or "").find("uninotes:") < \
                                      (nota.get("content") or "").find("concluzie")

        # o notiță redeschisă se construiește pe alt drum prin cod:
        # imaginea trebuie să apară și atunci, nu doar la inserare
        window.evaluate_js("""
            var carduri = Array.prototype.slice.call(document.querySelectorAll('.note-card'));
            var alta = carduri.filter(function (c) {
                return !/PROBA POZA/.test(c.textContent);
            })[0];
            if (alta) alta.click();
            'ok'
        """)
        time.sleep(1.5)
        out["a_plecat_de_pe_notita"] = window.evaluate_js(
            "document.querySelector('#titleInput').value")
        window.evaluate_js("""
            var carduri = Array.prototype.slice.call(document.querySelectorAll('.note-card'));
            var a = carduri.filter(function (c) { return /PROBA POZA/.test(c.textContent); })[0];
            if (a) a.click();
            'ok'
        """)
        time.sleep(2)
        out["s_a_intors_pe_notita"] = window.evaluate_js(
            "document.querySelector('#titleInput').value")
        out["dupa_redeschidere"] = citeste(window.evaluate_js(STARE))

        # ștergerea imaginii nu trebuie să ia textul cu ea
        window.evaluate_js("""
            var b = document.querySelector('#editorFlux .ed-media__btn');
            if (b) b.click();
            'ok'
        """)
        time.sleep(1)
        window.evaluate_js("""
            var d = document.querySelector('dialog[open] .btn--danger, dialog[open] button');
            var toate = document.querySelectorAll('dialog[open] button');
            for (var i = 0; i < toate.length; i++) {
                if (/terge/.test(toate[i].textContent)) { toate[i].click(); break; }
            }
            'ok'
        """)
        time.sleep(2.5)
        out["dupa_stergere"] = citeste(window.evaluate_js(STARE))
        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            nota = next((n for n in date.get("notes") or [] if n.get("title") == "PROBA POZA"), {})
            c = nota.get("content") or ""
            out["textul_a_supravietuit_stergerii"] = "Lagrange" in c and "concluzie" in c

        out["erori"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                      # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-poza-"))
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
