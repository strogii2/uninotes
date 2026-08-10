"""
Compilează aplicația și o pune chiar acolo unde o deschide utilizatorul.

Există fiindcă e ușor de greșit: PyInstaller scrie în .build/dist, iar aplicația
pe care o deschizi tu stă în rădăcina proiectului. Se poate recompila de zeci de
ori fără ca aplicația ta să se schimbe cu ceva — și totul pare în regulă, pentru
că verifici copia proaspătă, nu pe cea instalată. Scriptul face ambii pași și,
la final, citește versiunea din executabilul instalat, nu din cel construit.
"""

import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
SPEC = RADACINA / ".build" / "UniNotes.spec"
DIST = RADACINA / ".build" / "dist" / "UniNotes.exe"
INSTALAT = RADACINA / "UniNotes.exe"


def opreste_aplicatia():
    """Un executabil deschis nu poate fi înlocuit."""
    subprocess.run(["taskkill", "/IM", "UniNotes.exe", "/F"],
                   capture_output=True, text=True)
    time.sleep(1.2)


def versiunea_din(exe: Path):
    """Citim app.js direct din arhiva lipită la coada executabilului."""
    try:
        with zipfile.ZipFile(exe) as z:
            for nume in z.namelist():
                if nume.endswith("app.js"):
                    text = z.read(nume).decode("utf-8", "replace")
                    m = re.search(r"VERSIUNE = (\d+)", text)
                    return m.group(1) if m else "?"
    except Exception:                                            # noqa: BLE001
        pass
    return None


def main():
    if not SPEC.exists():
        print("Nu găsesc " + str(SPEC) + ".")
        print("Rulează scriptul din copia principală a proiectului: fișierele de")
        print("compilare stau în .build și nu sunt urmărite de git, deci lipsesc")
        print("dintr-un folder de lucru separat.")
        return 1

    print("Compilez…")
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC),
         "--distpath", str(SPEC.parent / "dist"),
         "--workpath", str(SPEC.parent / "work"), "--noconfirm"],
        capture_output=True, text=True)
    if r.returncode != 0 or not DIST.exists():
        print("Compilarea a eșuat:")
        print((r.stderr or r.stdout)[-1500:])
        return 1

    opreste_aplicatia()
    if INSTALAT.exists():
        shutil.copy2(INSTALAT, SPEC.parent / "UniNotes-precedent.exe")
    shutil.copy2(DIST, INSTALAT)

    v = versiunea_din(INSTALAT)
    print("Instalat: " + str(INSTALAT))
    print("Versiunea din executabilul instalat: " + (v or "(necitită)"))
    print("Copie a versiunii precedente: " + str(SPEC.parent / "UniNotes-precedent.exe"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
