"""
Verificare automată a aplicației desktop: pornește fereastra, folosește interfața
din interior și confirmă că notițele ajung în fișierul de pe disc. Apoi închide.
"""

import json
import tempfile
import time
from pathlib import Path

import webview

import main as app


def probe(window):
    out = {}
    try:
        time.sleep(4)                      # lăsăm WebView2 să încarce pagina

        out["punte_activa"] = window.evaluate_js("!!(window.pywebview && window.pywebview.api)")
        out["carduri_afisate"] = window.evaluate_js("document.querySelectorAll('.note-card').length")
        out["buton_folder_vizibil"] = window.evaluate_js(
            "!document.querySelector('#dataFolderBtn').hidden")
        out["erori_js"] = window.evaluate_js(
            "window.__erori ? window.__erori.length : 0")

        window.evaluate_js("""
            document.querySelector('#newNoteBtn').click();
            var t = document.querySelector('#titleInput');
            t.value = 'Proba de scriere pe disc';
            t.dispatchEvent(new Event('input', {bubbles:true}));
            var c = document.querySelector('#contentInput');
            c.value = '- [ ] verificat salvarea\\n\\nText cu diacritice: ăâîșț';
            c.dispatchEvent(new Event('input', {bubbles:true}));
            'ok'
        """)
        time.sleep(2)

        out["fisier_exista"] = app.DATA_FILE.exists()
        if app.DATA_FILE.exists():
            data = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            notes = data.get("notes", [])
            out["notite_in_fisier"] = len(notes)
            proba = next((n for n in notes if n.get("title") == "Proba de scriere pe disc"), None)
            out["proba_salvata"] = proba is not None
            out["diacritice_ok"] = bool(proba and "ăâîșț" in proba.get("content", ""))
            out["materii_in_fisier"] = len(data.get("subjects", []))

        # ne asigurăm că previzualizarea Markdown merge și în WebView2
        out["preview_html"] = window.evaluate_js("""
            document.querySelector('#previewBtn').click();
            document.querySelectorAll('#previewPane input[type=checkbox]').length
        """)

        # Orarul: butoanele lui au cedat o dată fiindcă bind() se oprea la primul
        # element lipsă, așa că fluxul de adăugare a unei ore rămâne verificat aici.
        out["orar_se_deschide"] = window.evaluate_js("""
            document.querySelector('#orarBtn').click();
            document.querySelector('#orarDlg').open
        """)
        out["orar_formular_se_deschide"] = window.evaluate_js("""
            document.querySelector('#orarAddBtn').click();
            document.querySelector('#oraModal').open
        """)
        window.evaluate_js("""
            document.querySelector('#oraMaterie').value = 'Ora din test';
            document.querySelector('#oraStart').value = '08:00';
            document.querySelector('#oraEnd').value = '10:00';
            document.querySelector('#oraForm button[type="submit"]').click();
            'ok'
        """)
        time.sleep(2)

        # celelalte ferestre noi trebuie să se deschidă la fel
        for nume, buton, dialog in (("termene", "#termeneBtn", "#termeneDlg"),
                                    ("repetitie", "#repetitieBtn", "#repetitieDlg")):
            out[nume + "_se_deschide"] = window.evaluate_js(
                "document.querySelector('%s').click();"
                "var d = document.querySelector('%s');"
                "var deschis = d.open; d.close(); deschis" % (buton, dialog))

        out["fara_elemente_lipsa"] = window.evaluate_js(
            "!document.querySelector('.toast.toast--err')")

        if app.DATA_FILE.exists():
            date = json.loads(app.DATA_FILE.read_text(encoding="utf-8"))
            ore = (date.get("orar") or {}).get("entries", [])
            out["ora_salvata_pe_disc"] = any(o.get("materie") == "Ora din test" for o in ore)
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    # Verificarea pornește de la zero, deci într-un folder al ei:
    # notițele reale ale utilizatorului nu au ce căuta aici.
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-test-"))
    app.DATA_FILE = app.DATA_DIR / "notite.json"              # pornim de la zero

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
