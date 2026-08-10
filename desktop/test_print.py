"""
Verifică dacă fereastra aplicației chiar deschide dialogul de printare.

Cum: în Chromium, window.print() blochează firul de JavaScript până când dialogul e
închis. Dacă apelul se întoarce imediat, înseamnă că printarea e ignorată; dacă rămâne
blocat, dialogul s-a deschis. Un cronometru închide procesul, ca să nu rămână agățat.
"""

import os
import sys
import threading
import time

import webview

import main as app


def opreste_dupa(secunde, mesaj):
    def bomba():
        time.sleep(secunde)
        print(mesaj, flush=True)
        os._exit(0)
    threading.Thread(target=bomba, daemon=True).start()


def probe(window):
    try:
        time.sleep(5)
        print("BUTON_PRINT=%s" % window.evaluate_js("!!document.querySelector('#printBtn')"), flush=True)
        print("ARE_PRINT=%s" % window.evaluate_js("typeof window.print === 'function'"), flush=True)

        window.evaluate_js("document.querySelectorAll('.note-card')[0].click(); 1")
        time.sleep(0.8)
        lung = window.evaluate_js(
            "document.querySelector('#printBtn').click();"
            "document.querySelector('#printArea').innerHTML.length")
        print("ZONA_PRINT_CARACTERE=%s" % lung, flush=True)

        time.sleep(1.5)
        raspuns = window.evaluate_js("'JS_LIBER'")
        print("WINDOW_PRINT_BLOCHEAZA=%s" % (raspuns is None), flush=True)

        # calea nativă: ShowPrintUI prin API-ul WebView2
        print("SHOW_PRINT_UI=%s" % API.print_ui(), flush=True)

        # de ce a eșuat? mergem pas cu pas prin obiectele native
        jurnal = []
        try:
            nativ = window.native
            jurnal.append("native=%s" % type(nativ).__name__)
            browser = getattr(nativ, "browser", None)
            jurnal.append("browser=%s" % type(browser).__name__)
            ctrl = getattr(browser, "webview", None)
            jurnal.append("webview=%s" % type(ctrl).__name__)
            jurnal.append("are_Invoke=%s" % hasattr(ctrl, "Invoke"))

            from System import Action
            def pe_ui():
                try:
                    core = ctrl.CoreWebView2
                    jurnal.append("core=%s" % type(core).__name__)
                    jurnal.append("are_ShowPrintUI=%s" % hasattr(core, "ShowPrintUI"))
                    from Microsoft.Web.WebView2.Core import CoreWebView2PrintDialogKind
                    core.ShowPrintUI(CoreWebView2PrintDialogKind.Browser)
                    jurnal.append("apel=OK")
                except Exception as e:
                    jurnal.append("apel_eroare=%r" % (e,))
            ctrl.Invoke(Action(pe_ui))
        except Exception as e:
            jurnal.append("eroare=%r" % (e,))
        print("DIAGNOSTIC=" + " | ".join(jurnal), flush=True)
        time.sleep(2)
        os._exit(0)
    except Exception as exc:                                   # noqa: BLE001
        print("EROARE=%r" % (exc,), flush=True)
        os._exit(1)


API = None


def run():
    global API
    API = app.Api()
    api = API
    window = webview.create_window(
        "UniNotes",
        url="http://127.0.0.1:%d/index.html?desktop=1" % app.start_local_server(),
        js_api=api, width=1200, height=800,
    )
    api.window = window
    opreste_dupa(45, "REZULTAT=TIMP_EXPIRAT")
    webview.start(probe, window, gui="edgechromium", private_mode=False,
                  storage_path=str(app.DATA_DIR / ".fereastra-test"))


if __name__ == "__main__":
    run()
