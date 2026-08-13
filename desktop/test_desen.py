"""
Verifică desenul în fereastra reală (WebView2), pas cu pas:
pânza primește dimensiuni, liniile se înregistrează, desenul ajunge în notiță.

Rulează pe fișierele din folderul proiectului, nu pe cele împachetate în .exe.
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


PROBA = r"""
(function () {
  var out = {};
  var c = document.querySelector('#desenCanvas');
  if (!c) { out.eroare = 'lipseste panza'; return JSON.stringify(out); }

  out.dialog_deschis = document.querySelector('#desenDlg').open;
  out.buffer = c.width + 'x' + c.height;
  out.css = c.clientWidth + 'x' + c.clientHeight;
  out.panza_masurata = c.width > 300 && c.height > 150;

  function numara() {
    var d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data, n = 0;
    for (var i = 0; i < d.length; i += 4) {
      if (d[i] < 200 || d[i + 1] < 200 || d[i + 2] < 200) n++;
    }
    return n;
  }
  out.pixeli_inainte = numara();

  var r = c.getBoundingClientRect();

  // Evenimentele trimise direct pânzei ocolesc verificarea a ce e deasupra ei.
  // Un strat invizibil ar opri degetul real, dar nu și testul, așa că întrebăm
  // pagina cine chiar primește atingerea în câteva puncte de pe pânză.
  out.cine_primeste = [[0.5, 0.5], [0.1, 0.1], [0.9, 0.9]].map(function (p) {
    var el = document.elementFromPoint(r.left + r.width * p[0], r.top + r.height * p[1]);
    if (!el) return 'nimic';
    return el.id ? '#' + el.id : (el.tagName + '.' + (el.className || '')).slice(0, 40);
  });
  out.panza_primeste_atingerea = out.cine_primeste.every(function (x) { return x === '#desenCanvas'; });
  out.touch_action = getComputedStyle(c).touchAction;

  var W = document.documentElement.clientWidth, H = document.documentElement.clientHeight;
  out.ecran = W + 'x' + H;
  out.incape_in_ecran = r.left >= -2 && r.top >= -2 &&
                        r.right <= W + 2 && r.bottom <= H + 2;

  function ev(tip, x, y, id, fel) {
    c.dispatchEvent(new PointerEvent(tip, {
      pointerId: id, bubbles: true, cancelable: true,
      pointerType: fel, isPrimary: true,
      clientX: r.left + x, clientY: r.top + y
    }));
  }
  // o linie cu mouse-ul
  ev('pointerdown', 60, 60, 1, 'mouse');
  ev('pointermove', 160, 110, 1, 'mouse');
  ev('pointermove', 260, 70, 1, 'mouse');
  ev('pointermove', 360, 160, 1, 'mouse');
  ev('pointerup', 360, 160, 1, 'mouse');
  out.pixeli_dupa_mouse = numara();

  // si una cu degetul
  ev('pointerdown', 60, 220, 2, 'touch');
  ev('pointermove', 200, 250, 2, 'touch');
  ev('pointermove', 340, 210, 2, 'touch');
  ev('pointerup', 340, 210, 2, 'touch');
  out.pixeli_dupa_deget = numara();

  out.sfat_ascuns = document.querySelector('#desenSfat').hidden;
  out.buton_inapoi_activ = !document.querySelector('#desenInapoi').disabled;
  return JSON.stringify(out);
})()
"""


URMA_PENSULEI = r"""
(function () {
  var out = {};
  var c = document.querySelector('#desenCanvas');
  var g = c.getContext('2d');
  var r = c.getBoundingClientRect();

  out.pensule = document.querySelectorAll('.desen-pensula').length;
  out.culori = document.querySelectorAll('#desenCulori .desen-culoare').length;
  out.glisor = !!document.querySelector('#desenGrosime');
  out.paleta_libera = !!document.querySelector('#desenOricare');

  // alegem pensula si o culoare inchisa, apoi o grosime mare
  var b = Array.prototype.slice.call(document.querySelectorAll('.desen-pensula'))
    .filter(function (x) { return x.getAttribute('aria-label') === 'PENSULA'; })[0];
  if (!b) { out.eroare = 'nu gasesc pensula PENSULA'; return JSON.stringify(out); }
  b.click();
  document.querySelectorAll('#desenCulori .desen-culoare')[0].click();
  var s = document.querySelector('#desenGrosime');
  s.value = '14';
  s.dispatchEvent(new Event('input', {bubbles: true}));
  out.grosime_setata = s.value;
  out.bulina = (document.querySelector('#desenBulina') || {}).style
    ? document.querySelector('#desenBulina').style.width : '';

  function ev(tip, x, y) {
    c.dispatchEvent(new PointerEvent(tip, {
      pointerId: 1, bubbles: true, cancelable: true, pointerType: 'mouse',
      isPrimary: true, clientX: r.left + x, clientY: r.top + y
    }));
  }
  var Y = Math.round(r.height / 2);
  ev('pointerdown', 60, Y);
  ev('pointermove', 200, Y);
  ev('pointermove', 340, Y);
  ev('pointerup', 340, Y);

  function pixel(x, y) {
    var d = g.getImageData(Math.round(x * (c.width / r.width)),
                           Math.round(y * (c.height / r.height)), 1, 1).data;
    return [d[0], d[1], d[2]];
  }
  out.miez = pixel(200, Y);                    // chiar pe linie
  out.langa = pixel(200, Y + 14);              // putin sub linie
  out.departe = pixel(200, Y + 60);            // hartie curata
  return JSON.stringify(out);
})()
"""

RADIERA = r"""
(function () {
  var out = {};
  var c = document.querySelector('#desenCanvas');
  var g = c.getContext('2d');
  var r = c.getBoundingClientRect();
  function ev(tip, x, y, id) {
    c.dispatchEvent(new PointerEvent(tip, {
      pointerId: id, bubbles: true, cancelable: true, pointerType: 'mouse',
      isPrimary: true, clientX: r.left + x, clientY: r.top + y
    }));
  }
  function pixel(x, y) {
    var d = g.getImageData(Math.round(x * (c.width / r.width)),
                           Math.round(y * (c.height / r.height)), 1, 1).data;
    return [d[0], d[1], d[2]];
  }
  var Y = Math.round(r.height / 2);

  // intai o linie cu pixul
  Array.prototype.slice.call(document.querySelectorAll('.desen-pensula'))
    .filter(function (x) { return x.getAttribute('aria-label') === 'Pix'; })[0].click();
  document.querySelectorAll('#desenCulori .desen-culoare')[0].click();
  ev('pointerdown', 60, Y, 1); ev('pointermove', 200, Y, 1);
  ev('pointermove', 340, Y, 1); ev('pointerup', 340, Y, 1);
  out.dupa_pix = pixel(200, Y);

  // apoi trecem radiera peste ea
  Array.prototype.slice.call(document.querySelectorAll('.desen-pensula'))
    .filter(function (x) { return x.getAttribute('aria-label') === 'Radieră'; })[0].click();
  ev('pointerdown', 60, Y, 2); ev('pointermove', 200, Y, 2);
  ev('pointermove', 340, Y, 2); ev('pointerup', 340, Y, 2);
  out.dupa_radiera = pixel(200, Y);
  out.a_sters = out.dupa_radiera[0] > 240 && out.dupa_radiera[1] > 240 && out.dupa_radiera[2] > 240;
  return JSON.stringify(out);
})()
"""


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def probe(window):
    out = {}
    try:
        time.sleep(5)

        out["eroare_pornire"] = window.evaluate_js("window.__eroare || ''")

        # o notiță nouă, ca butonul de desen să fie activ
        window.evaluate_js("document.querySelector('#newNoteBtn').click(); 'ok'")
        time.sleep(1)
        out["buton_desen_exista"] = window.evaluate_js("!!document.querySelector('#desenBtn')")

        window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
        time.sleep(1.5)

        out.update(json.loads(window.evaluate_js(PROBA)))

        # Aceeași verificare la lățime de telefon: acolo bara de unelte se rearanjează
        # și pânza poate rămâne fără înălțime sau poate ajunge sub altceva.
        window.evaluate_js("document.querySelector('#desenInchide').click(); 'ok'")
        window.resize(400, 850)
        time.sleep(2)
        window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
        time.sleep(2)
        out["telefon"] = json.loads(window.evaluate_js(PROBA))

        # iPhone-ul are ecran dens (2–3 puncte fizice per punct CSS). Îl imităm,
        # fiindcă acolo pânza își dublează rezoluția și își poate umfla layout-ul.
        window.evaluate_js("""
            document.querySelector('#desenInchide').click();
            Object.defineProperty(window, 'devicePixelRatio',
                                  {get: function () { return 2; }, configurable: true});
            'ok'
        """)
        time.sleep(0.5)
        window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
        time.sleep(3)
        out["telefon_dpr2"] = json.loads(window.evaluate_js(PROBA))
        out["latime_pagina"] = window.evaluate_js("document.documentElement.clientWidth")
        window.resize(1320, 860)
        time.sleep(1.5)

        # --- uneltele noi: fiecare pensulă trebuie să lase altă urmă ---
        window.evaluate_js("document.querySelector('#desenInchide').click(); 'ok'")
        time.sleep(1)
        out["unelte"] = {}
        out["s_a_deschis"] = {}
        for pensula in ("Pix", "Marker", "Neon"):
            window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
            time.sleep(1.5)
            out["s_a_deschis"][pensula.lower()] = window.evaluate_js(
                "document.querySelector('#desenDlg').open")
            out["unelte"][pensula.lower()] = citeste(window.evaluate_js(
                URMA_PENSULEI.replace("PENSULA", pensula)))
            window.evaluate_js("document.querySelector('#desenInchide').click(); 'ok'")
            time.sleep(0.8)

        # radiera trebuie să lase hârtia curată acolo unde trece
        window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
        time.sleep(2)
        out["s_a_deschis"]["radiera"] = window.evaluate_js(
            "document.querySelector('#desenDlg').open")
        out["unelte"]["radiera"] = citeste(window.evaluate_js(RADIERA))
        window.evaluate_js("document.querySelector('#desenInchide').click(); 'ok'")
        time.sleep(1)

        # desenul final, cel care ajunge în notiță
        window.evaluate_js("document.querySelector('#desenBtn').click(); 'ok'")
        time.sleep(1.5)
        window.evaluate_js(PROBA)
        time.sleep(0.5)

        # salvarea în notiță: desenul trebuie să se vadă printre rânduri
        window.evaluate_js("document.querySelector('#desenSalveaza').click(); 'ok'")
        time.sleep(2.5)
        out["desen_vizibil_in_notita"] = window.evaluate_js(
            "document.querySelectorAll('#editorFlux img').length")
        out["desen_are_sursa"] = window.evaluate_js(
            "Array.prototype.slice.call(document.querySelectorAll('#editorFlux img'))"
            ".filter(function (i) { return i.src && i.src.length > 40; }).length")
        out["cursor_sub_desen"] = window.evaluate_js(
            "!!(document.activeElement && document.activeElement.classList"
            ".contains('ed-text'))")
        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            nota = (date.get("notes") or [{}])[0]
            out["desen_in_notita"] = "uninotes:d" in (nota.get("content") or "")

        imagini = app.DATA_DIR / "imagini"
        out["fisiere_imagine"] = sorted(p.name for p in imagini.glob("*")) if imagini.exists() else []
        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                      # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    # Testul scrie notițe și imagini, așa că îl mutăm într-un folder al lui.
    # Notițele reale ale utilizatorului rămân neatinse.
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
