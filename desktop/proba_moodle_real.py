"""
Probă pe un Moodle adevărat, nu pe cel prefăcut din teste.

`test_moodle_cont.py` rulează pe un Moodle scris de noi: e rapid, sigur și
merge fără internet, dar întoarce exact ce i-am spus noi să întoarcă. Proba
asta ține celălalt capăt: vorbește cu demonstrația publică a Moodle, pe care
o ține chiar Moodle și care oferă singură, pe pagina de autentificare, un cont
de student pentru oricine vrea să se uite.

De aceea NU face parte din suita obișnuită: are nevoie de internet, depinde de
un site străin și se resetează din oră în oră. Se rulează de mână, atunci când
schimbi ceva la felul în care vorbim cu Moodle:

    python desktop\\proba_moodle_real.py

Nu scrie nimic nicăieri: doar citește și povestește.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import main as app

SITE = "https://school.moodledemo.net"
UTILIZATOR = "student"
PAROLA = "moodle26"      # scrise la vedere pe pagina de autentificare a demonstrației

TREBUIE = [
    "core_enrol_get_users_courses",
    "mod_assign_get_assignments",
    "gradereport_user_get_grade_items",
    "core_course_get_contents",
    "mod_forum_get_forums_by_courses",
]

api = app.Api()


def cere(jeton, functie, param=None):
    r = api.moodle_api(SITE, jeton, functie, param or {})
    if not r.get("ok"):
        return {"_eroare": r.get("eroare")}
    d = r["raspuns"]
    if isinstance(d, dict) and d.get("exception"):
        return {"_eroare": d.get("errorcode"), "_mesaj": d.get("message")}
    return d


def main():
    out = {}

    # 1. verificarea de dinainte de orice cont
    v = api.moodle_verifica(SITE)
    cod = ((v.get("servicii") or {}).get("json") or {}).get("errorcode")
    out["verificarea_vede_serviciile"] = cod == "invalidtoken"

    # 2. utilizator + parolă → cheie
    r = api.moodle_login(SITE, UTILIZATOR, PAROLA)
    out["conectare_cu_parola"] = bool(r.get("ok"))
    if not r.get("ok"):
        out["motiv"] = r.get("eroare")
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        return 1
    jeton = r["token"]

    # 3. cine sunt și ce e pornit
    info = cere(jeton, "core_webservice_get_site_info")
    if info.get("_eroare"):
        out["motiv"] = info
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        return 1
    functii = [f["name"] for f in info.get("functions") or []]
    out["nume_citit"] = bool(info.get("fullname"))
    out["functii_lipsa"] = [n for n in TREBUIE if n not in functii]

    uid = info.get("userid")

    # 4. cursurile
    cursuri = cere(jeton, "core_enrol_get_users_courses", {"userid": uid})
    if isinstance(cursuri, dict):
        out["motiv"] = cursuri
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        return 1
    out["cursuri"] = len(cursuri)
    ids = {"courseids[%d]" % i: c["id"] for i, c in enumerate(cursuri)}

    # 5. temele, pentru toate cursurile deodată
    t = cere(jeton, "mod_assign_get_assignments", ids)
    teme = [a for c in (t.get("courses") or []) for a in (c.get("assignments") or [])]
    out["teme"] = len(teme)
    out["teme_cu_termen"] = sum(1 for a in teme if a.get("duedate"))
    out["termen_citibil"] = bool(teme) and all(
        datetime.fromtimestamp(a["duedate"]).year > 2000
        for a in teme if a.get("duedate"))

    # 6. anunțurile
    f = cere(jeton, "mod_forum_get_forums_by_courses", ids)
    stiri = [x for x in (f if isinstance(f, list) else []) if x.get("type") == "news"]
    out["forumuri_de_stiri"] = len(stiri)
    if stiri:
        d = cere(jeton, "mod_forum_get_forum_discussions",
                 {"forumid": stiri[0]["id"], "perpage": 3, "page": 0})
        out["discutii_citite"] = len(d.get("discussions") or [])

    # 7. note și materiale, la primul curs
    if cursuri:
        c0 = cursuri[0]
        g = cere(jeton, "gradereport_user_get_grade_items",
                 {"courseid": c0["id"], "userid": uid})
        randuri = ((g.get("usergrades") or [{}])[0]).get("gradeitems") or []
        out["randuri_de_note"] = len(randuri)
        out["note_cu_valoare"] = sum(
            1 for it in randuri if (it.get("gradeformatted") or "-").strip() not in ("-", ""))

        s = cere(jeton, "core_course_get_contents", {"courseid": c0["id"]})
        out["materiale"] = sum(
            1 for sect in (s if isinstance(s, list) else [])
            for m in (sect.get("modules") or []) if m.get("modname") != "label")

    out["totul_a_mers"] = (out.get("conectare_cu_parola")
                           and not out.get("functii_lipsa")
                           and out.get("cursuri", 0) > 0
                           and out.get("teme", 0) > 0)
    print("REZULTAT " + json.dumps(out, ensure_ascii=False))
    return 0 if out["totul_a_mers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
