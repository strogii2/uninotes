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


def radacina_principala(p: Path) -> Path:
    """
    Un folder de lucru separat (.claude/worktrees/…) e tot proiectul, dar
    aplicația pe care o deschizi tu stă în copia principală. Acolo trebuie
    instalat, altfel compilarea ar fi degeaba: ai deschide mai departe
    versiunea veche și n-ai avea de unde să bănuiești.
    """
    for parinte in [p] + list(p.parents):
        if parinte.name == "worktrees" and parinte.parent.name == ".claude":
            return parinte.parent.parent
    return p


RADACINA = Path(__file__).resolve().parent.parent      # de unde se ia codul
PRINCIPALA = radacina_principala(RADACINA)             # unde stă aplicația ta
BUILD = PRINCIPALA / ".build"
SPEC = BUILD / "UniNotes.spec"
DIST = BUILD / "dist" / "UniNotes.exe"
INSTALAT = PRINCIPALA / "UniNotes.exe"

# Specificația se scrie de fiecare dată: căile din ea trebuie să arate spre
# copia din care se compilează acum, iar aceea nu e mereu cea principală.
SABLON = """# -*- mode: python ; coding: utf-8 -*-
# Scris de desktop/instaleaza.py — modificările de aici se pierd la următoarea rulare.

a = Analysis(
    ['{r}/desktop/main.py'],
    pathex=[],
    binaries=[],
    datas=[('{r}/index.html', 'web'), ('{r}/styles.css', 'web'), ('{r}/app.js', 'web')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='UniNotes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['{r}/desktop/icon.ico'],
)
"""


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
    lipsa = [c for c in ("index.html", "styles.css", "app.js", "desktop/main.py")
             if not (RADACINA / c).exists()]
    if lipsa:
        print("Lipsesc fișiere din " + str(RADACINA) + ": " + ", ".join(lipsa))
        return 1

    BUILD.mkdir(parents=True, exist_ok=True)
    SPEC.write_text(SABLON.format(r=RADACINA.as_posix()), encoding="utf-8")

    print("Compilez din: " + str(RADACINA))
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC),
         "--distpath", str(BUILD / "dist"),
         "--workpath", str(BUILD / "work"), "--noconfirm"],
        capture_output=True, text=True)
    if r.returncode != 0 or not DIST.exists():
        print("Compilarea a eșuat:")
        print((r.stderr or r.stdout)[-1500:])
        return 1

    opreste_aplicatia()
    if INSTALAT.exists():
        shutil.copy2(INSTALAT, BUILD / "UniNotes-precedent.exe")
    shutil.copy2(DIST, INSTALAT)

    print("Instalat: " + str(INSTALAT))
    print("Copie a versiunii precedente: " + str(BUILD / "UniNotes-precedent.exe"))

    v = porneste_si_citeste_versiunea(INSTALAT)
    if not v:
        print("ATENȚIE: aplicația s-a instalat, dar nu am putut confirma versiunea.")
        return 1
    print("Versiunea care chiar rulează acum: " + v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
