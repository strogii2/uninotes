"""
Sondă de pornire: verifică, secundă cu secundă, dacă firul de JavaScript răspunde
și cât a apucat aplicația să inițializeze. Separă „blocat" de „eroare la pornire".
"""

import os
import threading
import time

import webview

import main as app


def opreste_dupa(secunde):
    def bomba():
        time.sleep(secunde)
        print("SFARSIT=timp_expirat", flush=True)
        os._exit(0)
    threading.Thread(target=bomba, daemon=True).start()


def probe(window):
    opreste_dupa(60)
    for i in range(1, 25):
        time.sleep(1)
        try:
            viu = window.evaluate_js("1+1")
        except Exception as exc:                       # noqa: BLE001
            print("t=%2ds EROARE_EVAL=%r" % (i, exc), flush=True)
            continue
        if viu != 2:
            print("t=%2ds js_nu_raspunde" % i, flush=True)
            continue
        stare = window.evaluate_js("""
          (function () {
            return [
              document.querySelectorAll('.note-card').length,
              document.querySelector('#versiune') ? document.querySelector('#versiune').textContent : 'x',
              (typeof window.pywebview !== 'undefined') + '',
              (!!(window.pywebview && window.pywebview.api)) + '',
              window.__eroare || '-',
              (window.pywebview && window.pywebview.api)
                ? Object.keys(window.pywebview.api).sort().join(',') : 'fara-api'
            ].join(' | ');
          })()
        """)
        print("t=%2ds  carduri | versiune | pywebview | api | eroare  =  %s" % (i, stare), flush=True)
        if stare and stare.split(' | ')[0] != '0':
            print("SFARSIT=pornit_ok", flush=True)
            os._exit(0)
    print("SFARSIT=nu_a_pornit", flush=True)
    os._exit(0)


def run():
    api = app.Api()
    window = webview.create_window(
        "UniNotes",
        url="http://127.0.0.1:%d/index.html?desktop=1" % app.start_local_server(),
        js_api=api, width=1200, height=800,
    )
    api._window = window
    webview.start(probe, window, gui="edgechromium", private_mode=False,
                  storage_path=str(app.DATA_DIR / ".fereastra-boot"))


if __name__ == "__main__":
    run()
