"""
Verifică desenul în fereastra reală (WebView2), pas cu pas:
pânza primește dimensiuni, liniile se înregistrează, desenul ajunge în notiță.

Rulează pe fișierele din folderul proiectului, nu pe cele împachetate în .exe.
"""

import json
import tempfile
import time
from pathlib import Path

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

        # salvarea în notiță
        window.evaluate_js("document.querySelector('#desenSalveaza').click(); 'ok'")
        time.sleep(2)
        out["continut_notita"] = window.evaluate_js(
            "(document.querySelector('#contentInput') || {}).value || ''")
        out["desen_in_notita"] = "uninotes:d" in (out.get("continut_notita") or "")

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
