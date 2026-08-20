"""
Proba adresei mutate.

Facultatea a mutat Moodle-ul de la moodle.usm.md la elearning.usm.md și a
lăsat în urmă o trimitere. Python urmează trimiterea, dar pe drum preface
POST-ul în GET și lasă datele acasă: Moodle primea o cerere goală și răspundea
„A lipsit un parametru obligatoriu (username)" — deși utilizatorul îl scrisese.

Aici ridicăm două servere de casă: unul care spune „m-am mutat" și unul care
răspunde ca un Moodle. Dacă utilizatorul ajunge întreg la al doilea, repararea
ține. Nu are nevoie de internet, deci prinde defectul și peste un an.
"""
import json
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import main  # noqa: E402


def porneste(clasa):
    s = HTTPServer(("127.0.0.1", 0), clasa)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, "http://127.0.0.1:%d" % s.server_port


class Tacut(BaseHTTPRequestHandler):
    def log_message(self, *a):                                    # fără zgomot
        pass


def fa_moodle():
    """Un Moodle de casă: dă cheia dacă a primit utilizatorul, altfel se plânge."""
    class Moodle(Tacut):
        def do_POST(self):
            lung = int(self.headers.get("Content-Length") or 0)
            camp = urllib.parse.parse_qs(self.rfile.read(lung).decode("utf-8"))
            if self.path.endswith("/login/token.php"):
                if not camp.get("username", [""])[0]:
                    corp = {"error": "A lipsit un parametru obligatoriu (username)",
                            "errorcode": "missingparam"}
                else:
                    corp = {"token": "cheie-" + camp["username"][0]}
            else:
                corp = {"sitename": "Moodle de casă",
                        "username": camp.get("wstoken", [""])[0]}
            brut = json.dumps(corp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(brut)))
            self.end_headers()
            self.wfile.write(brut)

        def do_GET(self):                                         # cerere fără date
            self.do_POST_gol()

        def do_POST_gol(self):
            brut = json.dumps({"error": "A lipsit un parametru obligatoriu (username)",
                               "errorcode": "missingparam"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(brut)))
            self.end_headers()
            self.wfile.write(brut)

    return porneste(Moodle)


def fa_mutarea(catre, cod=301):
    class Mutat(Tacut):
        def do_POST(self):
            # citim cererea până la capăt înainte de a răspunde: altfel Windows
            # rupe legătura, exact ca un server prost purtat, și n-am mai proba
            # ce voiam
            lung = int(self.headers.get("Content-Length") or 0)
            if lung:
                self.rfile.read(lung)
            self.send_response(cod)
            self.send_header("Location", catre + self.path)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = do_POST

    return porneste(Mutat)


def main_proba():
    rez = {}
    api = main.Api.__new__(main.Api)

    s_moodle, adr_moodle = fa_moodle()
    s_vechi, adr_vechi = fa_mutarea(adr_moodle)

    # 1. conectarea pe adresa veche trebuie să ajungă la Moodle cu utilizator cu tot
    r = api.moodle_login(adr_vechi, "ion.popescu", "parola")
    rez["cheie_primita"] = bool(r.get("ok") and r.get("token") == "cheie-ion.popescu")
    rez["nu_mai_zice_missingparam"] = "missingparam" not in json.dumps(r)
    rez["adresa_corectata"] = r.get("site") == adr_moodle

    # 2. serviciile web, la fel
    a = api.moodle_api(adr_vechi, "cheia-mea", "core_webservice_get_site_info", {})
    rez["servicii_ok"] = bool(a.get("ok"))
    rez["cheia_a_ajuns"] = (a.get("raspuns") or {}).get("username") == "cheia-mea"
    rez["servicii_adresa"] = a.get("site") == adr_moodle

    # 3. verificarea spune unde s-a mutat
    v = api.moodle_verifica(adr_vechi)
    rez["verifica_spune_mutarea"] = v.get("mutat") == adr_moodle

    # 4. și mutarea de tip 302/307 merge
    s_307, adr_307 = fa_mutarea(adr_moodle, 307)
    r3 = api.moodle_login(adr_307, "ana", "x")
    rez["si_307"] = r3.get("token") == "cheie-ana"

    # 5. o trimitere spre http, în afara calculatorului, se refuză: parola n-are
    #    ce căuta pe o legătură necriptată
    s_afara, adr_afara = fa_mutarea("http://exemplu-nesigur.md")
    r4 = api.moodle_login(adr_afara, "ana", "x")
    rez["refuza_necriptat"] = (not r4.get("ok")) and "necriptat" in (r4.get("eroare") or "")

    # 6. o trimitere în cerc nu blochează aplicația
    s_cerc = None
    class Cerc(Tacut):
        def do_POST(self):
            lung = int(self.headers.get("Content-Length") or 0)
            if lung:
                self.rfile.read(lung)
            self.send_response(301)
            self.send_header("Location", adr_cerc + self.path)
            self.send_header("Content-Length", "0")
            self.end_headers()
        do_GET = do_POST
    s_cerc, adr_cerc = porneste(Cerc)
    r5 = api.moodle_login(adr_cerc, "ana", "x")
    rez["cerc_se_opreste"] = (not r5.get("ok")) and "mută" in (r5.get("eroare") or "")

    for s in (s_moodle, s_vechi, s_307, s_afara, s_cerc):
        s.shutdown()

    rez["tot_bine"] = all(v is True for v in rez.values())
    print("REZULTAT " + json.dumps(rez, ensure_ascii=False))
    return 0 if rez["tot_bine"] else 1


if __name__ == "__main__":
    sys.exit(main_proba())
