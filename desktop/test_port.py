"""
Proba portului statornic.

Browserul dinăuntru ține cheia de Moodle legată de adresa paginii, iar adresa
cuprinde portul. Cât timp portul era ales de sistem, fiecare pornire deschidea
alt sertar, gol: cheia părea pierdută și trebuia luată din nou de fiecare dată.
Pe disc se vedeau limpede trei sertare, cu chei diferite în ele.

Aici verificăm că portul iese mereu la fel din calea notițelor, că două seturi
de notițe primesc porturi diferite, că un port ocupat nu oprește pornirea și că
serverul chiar servește pagina. Fără internet și fără fereastră.
"""
import json
import socket
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import main  # noqa: E402

out = {}
vechi = main.DATA_DIR

try:
    # 1. același drum → același port, de câte ori l-ai întreba
    a = main.port_statornic()
    b = main.port_statornic()
    out["acelasi_port"] = a == b
    out["in_interval"] = 40000 <= a < 49000

    # 2. alte notițe → alt port, ca două copii să nu se calce pe picioare
    main.DATA_DIR = Path(r"C:\cu totul\altundeva")
    c = main.port_statornic()
    out["alte_notite_alt_port"] = c != a
    main.DATA_DIR = vechi

    # 3. pornirea chiar ia portul statornic
    port1 = main.start_local_server()
    out["porneste_pe_portul_lui"] = port1 == a

    # 4. cu portul ocupat, pornirea merge mai departe pe vecin — nu cade
    port2 = main.start_local_server()
    out["ocupat_merge_pe_vecin"] = port2 != port1 and a <= port2 < a + 8

    # 5. și serverul chiar servește pagina
    with urllib.request.urlopen("http://127.0.0.1:%d/index.html" % port1,
                                timeout=10) as r:
        pagina = r.read(4000).decode("utf-8", errors="replace")
    out["serveste_pagina"] = "<title>" in pagina.lower()

    # 6. ascultă doar local: din afară nu se vede
    gazda = socket.socket()
    gazda.settimeout(2)
    try:
        gazda.connect((socket.gethostbyname(socket.gethostname()), port1))
        out["doar_local"] = False
    except Exception:
        out["doar_local"] = True
    finally:
        gazda.close()
except Exception as e:                                            # noqa: BLE001
    out["eroare"] = "%s: %s" % (type(e).__name__, e)
finally:
    main.DATA_DIR = vechi

print("REZULTAT " + json.dumps(out, ensure_ascii=False), flush=True)
