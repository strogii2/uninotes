"""
Verifică puntea de fișiere (export .md, import .json, pregătirea paginii de printare)
fără să deschidă dialoguri sau ferestre: înlocuim dialogul și os.startfile.
"""

import json
import os
import tempfile
from pathlib import Path

import main as app

rezultate = {}
tmp = Path(tempfile.mkdtemp(prefix="uninotes-test-"))

# Testul strică fișierul de notițe intenționat, ca să verifice recuperarea.
# Îl mutăm mai întâi într-un folder al lui, ca notițele reale să rămână întregi.
app.DATA_DIR = tmp / "date"
app.DATA_FILE = app.DATA_DIR / "notite.json"
app.DATA_DIR.mkdir(parents=True, exist_ok=True)


class FereastraFalsa:
    """Ține locul ferestrei reale: întoarce o cale în loc să deschidă dialogul."""

    def __init__(self, cale):
        self.cale = cale

    def create_file_dialog(self, *args, **kwargs):
        return (str(self.cale),)


api = app.Api()

# --- export .md ---
tinta = tmp / "notita.md"
api._window = FereastraFalsa(tinta)
continut = "# Titlu cu diacritice\n\n- [ ] ceva de făcut\n\nȘțîâă"
cale = api.save_file("notita.md", continut)
rezultate["export_cale_intoarsa"] = cale is not None
rezultate["export_continut_identic"] = tinta.read_text(encoding="utf-8") == continut

# --- import .json ---
sursa = tmp / "backup.json"
sursa.write_text(json.dumps({"notes": [{"title": "Notiță importată"}]}, ensure_ascii=False),
                 encoding="utf-8")
api._window = FereastraFalsa(sursa)
adus = api.open_file()
rezultate["import_nume"] = adus["name"]
rezultate["import_titlu"] = json.loads(adus["content"])["notes"][0]["title"]

# --- pagina de printare ---
deschise = []
original_startfile = os.startfile
os.startfile = lambda p: deschise.append(p)          # nu deschidem nimic pe ecran
try:
    ok = api.print_note("Curs 1 — Limite", "<h2>Test</h2><p>corp</p>", "body{margin:0}")
finally:
    os.startfile = original_startfile
rezultate["printare_ok"] = ok
rezultate["printare_fisier_scris"] = bool(deschise) and Path(deschise[0]).exists()
if deschise:
    html = Path(deschise[0]).read_text(encoding="utf-8")
    rezultate["printare_contine_titlul"] = "Curs 1 — Limite" in html
    rezultate["printare_contine_corpul"] = "<p>corp</p>" in html

# --- scriere/citire date, cu fișier stricat ---
api._window = None
rezultate["salvare_date"] = api.save_data({"notes": [], "subjects": [], "settings": {}})["ok"]
app.DATA_FILE.write_text("{ asta nu e json valid", encoding="utf-8")
rezultate["json_stricat_nu_arunca"] = api.load_data() is None
rezultate["json_stricat_pus_deoparte"] = app.DATA_FILE.with_suffix(".json.stricat").exists()

# --- poze din notițe ---
import base64

mic_png = base64.b64encode(b"\xff\xd8\xff\xe0 poza de test").decode("ascii")
api._window = None
rezultate["poza_salvata"] = api.save_image("abc123", "data:image/jpeg;base64," + mic_png)["ok"]
adus = api.load_image("abc123")
rezultate["poza_citita_identic"] = adus == "data:image/jpeg;base64," + mic_png
rezultate["poza_in_lista"] = "abc123" in api.list_images()
rezultate["poza_lipsa_da_none"] = api.load_image("nu-exista") is None

# numele vine din interfață: nu trebuie să poată ieși din folderul cu imagini
api.save_image("../../evadare", "data:image/jpeg;base64," + mic_png)
rezultate["fara_evadare_din_folder"] = not (app.DATA_DIR.parent / "evadare.jpg").exists()
rezultate["nume_curatat"] = "evadare" in api.list_images()

# desenele vin ca PNG, nu ca JPEG
mic_png_real = base64.b64encode(b"\x89PNG\r\n\x1a\n desen de test").decode("ascii")
api.save_image("desen1", "data:image/png;base64," + mic_png_real)
rezultate["desen_pastreaza_png"] = api.load_image("desen1").startswith("data:image/png;base64,")
rezultate["desen_e_fisier_png"] = (app.DATA_DIR / "imagini" / "desen1.png").exists()
rezultate["desen_in_lista"] = "desen1" in api.list_images()

# reînlocuit cu alt format: nu trebuie să rămână două fișiere
api.save_image("desen1", "data:image/jpeg;base64," + mic_png)
rezultate["fara_dublura_la_schimbare"] = (
    (app.DATA_DIR / "imagini" / "desen1.jpg").exists()
    and not (app.DATA_DIR / "imagini" / "desen1.png").exists()
)
rezultate["format_neacceptat_refuzat"] = not api.save_image("x1", "data:image/gif;base64," + mic_png)["ok"]
api.delete_image("desen1")

rezultate["poza_stearsa"] = api.delete_image("abc123")
rezultate["poza_chiar_stearsa"] = api.load_image("abc123") is None
api.delete_image("evadare")

print("REZULTAT " + json.dumps(rezultate, ensure_ascii=False))
