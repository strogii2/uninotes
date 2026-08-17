"""
Verifică desenul făcut chiar în notiță, în fereastra reală: blocul apare între
rânduri, pânza încape pe ecran și primește atingerea, fiecare pensulă lasă altă
urmă, desenul se salvează singur când ieși din el și se poate relua mai târziu
peste ce era deja desenat.
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


BLOC = r"""
(function () {
  var out = {};
  // într-o notiță pot sta mai multe desene: ne uităm la cel deschis acum
  var fig = document.querySelector('#editorFlux .ed-desen.is-activ') ||
            document.querySelector('#editorFlux .ed-desen');
  out.bloc_exista = !!fig;
  out.cate_desene = document.querySelectorAll('#editorFlux .ed-desen').length;
  if (!fig) return JSON.stringify(out);
  out.bloc_activ = fig.classList.contains('is-activ');

  var c = fig.querySelector('canvas.desen-panza');
  out.panza_exista = !!c;
  out.pensule = fig.querySelectorAll('.desen-pensula').length;
  out.culori = fig.querySelectorAll('.desen-culoare').length;
  out.glisor = !!fig.querySelector('.desen-bara input[type="range"]');
  out.paleta_libera = !!fig.querySelector('.desen-oricare input[type="color"]');
  out.buton_gata = !!fig.querySelector('[data-dz="gata"]');
  if (!c) return JSON.stringify(out);

  var r = c.getBoundingClientRect();
  var W = document.documentElement.clientWidth;
  out.ecran = W;
  out.latime_panza = Math.round(r.width);
  out.inaltime_panza = Math.round(r.height);
  out.pixeli_panza = c.width + 'x' + c.height;
  out.incape_in_ecran = r.left >= -2 && r.right <= W + 2;
  out.se_vede = r.width > 40 && r.height > 40;

  // atingerea trebuie sa ajunga la panza, nu la sfatul de deasupra
  var puncte = [[0.5, 0.5], [0.2, 0.3], [0.8, 0.7]];
  out.cine_primeste = puncte.map(function (p) {
    var el = document.elementFromPoint(r.left + r.width * p[0], r.top + r.height * p[1]);
    if (!el) return 'nimic';
    if (el === c) return 'panza';
    return el.className || el.tagName;
  });
  out.panza_primeste_atingerea = out.cine_primeste.every(function (x) { return x === 'panza'; });
  return JSON.stringify(out);
})()
"""


# desenează o linie orizontală cu pensula cerută și citește pixelii din jurul ei
URMA = r"""
(function (tip, frac) {
  var c = document.querySelector('#editorFlux canvas.desen-panza');
  if (!c) return JSON.stringify({panza: false});

  var b = document.querySelector('.desen-pensula[data-pensula="' + tip + '"]');
  if (b) b.click();
  var s = document.querySelector('.desen-bara input[type="range"]');
  if (s) { s.value = '18'; s.dispatchEvent(new Event('input', {bubbles: true})); }

  var r = c.getBoundingClientRect();
  var y = r.top + r.height * frac;
  var x0 = r.left + r.width * 0.15, x1 = r.left + r.width * 0.85;
  var id = 30 + Math.round(frac * 100);
  function trimite(nume, x) {
    c.dispatchEvent(new PointerEvent(nume, {
      pointerId: id, clientX: x, clientY: y, bubbles: true, isPrimary: true
    }));
  }
  trimite('pointerdown', x0);
  for (var i = 1; i <= 12; i++) trimite('pointermove', x0 + (x1 - x0) * i / 12);
  trimite('pointerup', x1);

  var g = c.getContext('2d');
  var k = c.width / r.width;                 // din pixeli de ecran în pixeli de pânză
  var px = Math.round((x0 + (x1 - x0) / 2 - r.left) * k);
  var py = Math.round((y - r.top) * k);
  function ia(dy) {
    var yy = Math.max(0, Math.min(c.height - 1, py + Math.round(dy * k)));
    var d = g.getImageData(px, yy, 1, 1).data;
    return [d[0], d[1], d[2]];
  }
  return JSON.stringify({
    panza: true,
    linii: (document.querySelectorAll('.desen-pensula.is-active').length),
    miez: ia(0), langa: ia(14), departe: ia(30)
  });
})
"""


STARE_NOTITA = r"""
(function () {
  var out = {};
  var copii = Array.prototype.slice.call(document.querySelectorAll('#editorFlux > *'));
  out.bucati = copii.map(function (e) { return e.tagName.toLowerCase(); });
  out.text = copii.filter(function (e) { return e.tagName === 'TEXTAREA'; })
                  .map(function (t) { return t.value; }).join('|');
  var fig = document.querySelector('#editorFlux .ed-desen');
  out.cate_desene = document.querySelectorAll('#editorFlux .ed-desen').length;
  out.desen_in_notita = !!fig;
  out.desen_activ = !!(fig && fig.classList.contains('is-activ'));
  if (fig) {
    var im = fig.querySelector('img');
    out.imagine_cu_sursa = !!(im && im.src && im.src.length > 60);
    out.buton_deseneaza = !!fig.querySelector('[data-act="deseneaza"]');
    var r = fig.getBoundingClientRect();
    var W = document.documentElement.clientWidth;
    out.incape_in_ecran = r.left >= -2 && r.right <= W + 2;
    out.inaltime = Math.round(r.height);
  }
  return JSON.stringify(out);
})()
"""


# cât de închisă e imaginea: dacă desenul vechi s-a întors ca fundal, nu e toată albă
CAT_E_DESENAT = r"""
(function () {
  var c = document.querySelector('#editorFlux canvas.desen-panza');
  if (!c) return JSON.stringify({panza: false});
  var g = c.getContext('2d');
  var d = g.getImageData(0, 0, c.width, c.height).data;
  var colorati = 0, total = 0;
  for (var i = 0; i < d.length; i += 4 * 37) {          // din 37 în 37, e destul
    total++;
    if (d[i] < 240 || d[i + 1] < 240 || d[i + 2] < 240) colorati++;
  }
  return JSON.stringify({panza: true, total: total, colorati: colorati});
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def asteapta_aplicatia(window, secunde=40):
    for _ in range(int(secunde * 2)):
        try:
            if window.evaluate_js("!!document.querySelector('#newNoteBtn')"):
                return True
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


def probe(window):
    out = {}
    try:
        out["aplicatia_a_pornit"] = asteapta_aplicatia(window)
        window.evaluate_js("document.querySelector('#newNoteBtn').click(); 'ok'")
        time.sleep(1.5)

        window.evaluate_js("""
            var ti = document.querySelector('#titleInput');
            ti.value = 'PROBA DESEN';
            ti.dispatchEvent(new Event('input', {bubbles: true}));
            var t = document.querySelector('#editorFlux > textarea');
            t.focus();
            t.value = 'Curs 5 — schema montajului';
            t.dispatchEvent(new Event('input', {bubbles: true}));
            t.setSelectionRange(t.value.length, t.value.length);
            'ok'
        """)
        time.sleep(1)

        # ---- desenul se deschide chiar în notiță ----
        window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
        time.sleep(2)
        out["dupa_apasare"] = citeste(window.evaluate_js(BLOC))

        # ---- fiecare pensulă lasă altă urmă ----
        for pensula, frac in (("pix", 0.22), ("marker", 0.5), ("neon", 0.78)):
            out["urma_" + pensula] = citeste(
                window.evaluate_js("(" + URMA + ")('%s', %s)" % (pensula, frac)))
            time.sleep(0.4)

        # radiera trece peste linia de pix și o scoate
        out["urma_radiera"] = citeste(
            window.evaluate_js("(" + URMA + ")('radiera', 0.22)"))
        time.sleep(0.4)

        out["cu_desen_pe_panza"] = citeste(window.evaluate_js(CAT_E_DESENAT))

        # ---- o apăsare în text încheie desenul și îl salvează ----
        window.evaluate_js("""
            var t = document.querySelector('#editorFlux > textarea');
            t.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerId: 9}));
            t.click();
            'ok'
        """)
        time.sleep(2.5)
        out["dupa_incheiere"] = citeste(window.evaluate_js(STARE_NOTITA))

        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            nota = next((n for n in date.get("notes") or []
                         if n.get("title") == "PROBA DESEN"), {})
            c = nota.get("content") or ""
            out["marcaj_in_notita"] = "uninotes:d" in c
            out["textul_a_ramas"] = "montajului" in c

        imagini = app.DATA_DIR / "imagini"
        out["fisiere_pe_disc"] = sorted(p.name for p in imagini.glob("*")) \
            if imagini.exists() else []

        # ---- la lățime de telefon blocul trebuie să încapă ----
        window.resize(400, 850)
        time.sleep(2)
        out["pe_telefon"] = citeste(window.evaluate_js(STARE_NOTITA))

        # uneltele trebuie să încapă și pe telefon, cu butoane cât degetul
        window.evaluate_js("""
            var b = document.querySelector('#editorFlux [data-act="deseneaza"]');
            if (b) b.click();
            'ok'
        """)
        time.sleep(2.5)
        out["panza_pe_telefon"] = citeste(window.evaluate_js(BLOC))
        out["bara_pe_telefon"] = citeste(window.evaluate_js(r"""
            (function () {
              var bara = document.querySelector('#editorFlux .desen-bara');
              if (!bara) return JSON.stringify({bara: false});
              var W = document.documentElement.clientWidth;
              var copii = Array.prototype.slice.call(bara.querySelectorAll('button,input'));
              var iese = copii.filter(function (e) {
                var r = e.getBoundingClientRect();
                return r.left < -2 || r.right > W + 2;
              });
              var mici = copii.filter(function (e) {
                var r = e.getBoundingClientRect();
                return r.height > 0 && r.height < 30;
              });
              return JSON.stringify({
                bara: true, ecran: W, unelte: copii.length,
                iese_din_ecran: iese.length, prea_mici: mici.length,
                inaltime_bara: Math.round(bara.getBoundingClientRect().height)
              });
            })()
        """))
        window.evaluate_js("""
            var b = document.querySelector('#editorFlux [data-dz="gata"]');
            if (b) b.click();
            'ok'
        """)
        time.sleep(2)

        window.resize(1320, 860)
        time.sleep(1.5)

        # ---- notița redeschisă: desenul se poate relua peste ce era ----
        window.evaluate_js("""
            var carduri = Array.prototype.slice.call(document.querySelectorAll('.note-card'));
            var alta = carduri.filter(function (c) { return !/PROBA DESEN/.test(c.textContent); })[0];
            if (alta) alta.click();
            'ok'
        """)
        time.sleep(1.5)
        window.evaluate_js("""
            var carduri = Array.prototype.slice.call(document.querySelectorAll('.note-card'));
            var a = carduri.filter(function (c) { return /PROBA DESEN/.test(c.textContent); })[0];
            if (a) a.click();
            'ok'
        """)
        time.sleep(2)
        out["dupa_redeschidere"] = citeste(window.evaluate_js(STARE_NOTITA))

        window.evaluate_js("""
            var b = document.querySelector('#editorFlux [data-act="deseneaza"]');
            if (b) b.click();
            'ok'
        """)
        time.sleep(2.5)
        out["reluat"] = citeste(window.evaluate_js(BLOC))
        out["desenul_vechi_s_a_intors"] = citeste(window.evaluate_js(CAT_E_DESENAT))

        # o linie nouă peste desenul vechi, apoi „Gata”
        out["urma_peste_vechi"] = citeste(
            window.evaluate_js("(" + URMA + ")('pix', 0.35)"))
        time.sleep(0.4)
        window.evaluate_js("""
            var b = document.querySelector('#editorFlux [data-dz="gata"]');
            if (b) b.click();
            'ok'
        """)
        time.sleep(2.5)
        out["dupa_gata"] = citeste(window.evaluate_js(STARE_NOTITA))

        if imagini.exists():
            out["fisiere_la_final"] = sorted(p.name for p in imagini.glob("*"))

        # ---- desen început și lăsat gol: blocul nu trebuie să rămână ----
        window.evaluate_js("""
            var c = document.querySelectorAll('#editorFlux > textarea');
            var ultim = c[c.length - 1];
            ultim.focus();
            ultim.setSelectionRange(ultim.value.length, ultim.value.length);
            document.querySelector('#desenBtn').click();
            'ok'
        """)
        time.sleep(2)
        out["gol_deschis"] = citeste(window.evaluate_js(BLOC))
        window.evaluate_js("""
            var t = document.querySelector('#editorFlux > textarea');
            t.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerId: 11}));
            'ok'
        """)
        time.sleep(2)
        out["gol_dupa_iesire"] = citeste(window.evaluate_js(STARE_NOTITA))
        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            nota = next((n for n in date.get("notes") or []
                         if n.get("title") == "PROBA DESEN"), {})
            c = nota.get("content") or ""
            out["un_singur_desen_in_text"] = c.count("uninotes:d") == 1

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-desen-"))
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
