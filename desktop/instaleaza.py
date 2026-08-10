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
import tempfile
import time
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


def porneste_si_citeste_versiunea(exe: Path):
    """
    Singurul martor de încredere e aplicația pornită. Arhiva lipită la coada
    executabilului nu e un zip și e comprimată, deci nu se poate citi de pe disc;
    în schimb, la pornire își desface fișierele într-un folder temporar.
    Lăsăm aplicația deschisă la final — oricum asta vrei după instalare.
    """
    temp = Path(tempfile.gettempdir())
    inainte = set(temp.glob("_MEI*"))
    subprocess.Popen([str(exe)])
    for _ in range(60):
        time.sleep(0.5)
        for d in temp.glob("_MEI*"):
            if d in inainte:
                continue
            f = d / "web" / "app.js"
            if f.exists():
                m = re.search(r"VERSIUNE = (\d+)",
                              f.read_text(encoding="utf-8", errors="replace"))
                if m:
                    return m.group(1)
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

    print("Instalat: " + str(INSTALAT))
    print("Copie a versiunii precedente: " + str(SPEC.parent / "UniNotes-precedent.exe"))

    v = porneste_si_citeste_versiunea(INSTALAT)
    if not v:
        print("ATENȚIE: aplicația s-a instalat, dar nu am putut confirma versiunea.")
        return 1
    print("Versiunea care chiar rulează acum: " + v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
