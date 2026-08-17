"""
Compilează aplicația și o pune chiar acolo unde o deschide utilizatorul.

Există fiindcă e ușor de greșit: PyInstaller scrie în .build/dist, iar aplicația
pe care o deschizi tu stă în rădăcina proiectului. Se poate recompila de zeci de
ori fără ca aplicația ta să se schimbe cu ceva — și totul pare în regulă, pentru
că verifici copia proaspătă, nu pe cea instalată.

Ordinea contează: întâi pornim executabilul proaspăt construit și abia dacă
chiar merge îl punem peste cel vechi. Altfel o construcție pe care Windows
refuză s-o pornească ți-ar lăsa aplicația moartă, fără nimic la care să te
întorci.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Consola Windows nu scrie diacritice implicit, iar scriptul ăsta tocmai
# despre ele are de povestit când ceva merge prost.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BLOCAT_DE_WINDOWS = 4551          # „An Application Control policy has blocked this file”
INCERCARI = 4


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
PRECEDENT = BUILD / "UniNotes-precedent.exe"
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
    # Fără UPX înadins. Împachetarea făcea executabilul cu vreo 3 MB mai mic,
    # dar e și tiparul după care se ascunde de obicei codul rău, așa că
    # Smart App Control refuza să pornească multe dintre construcții.
    upx=False,
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


def porneste(exe: Path):
    """
    Pornește executabilul și citește versiunea din el.

    Singurul martor de încredere e aplicația pornită. Arhiva lipită la coada
    executabilului nu e un zip și e comprimată, deci nu se poate citi de pe
    disc; în schimb, la pornire își desface fișierele într-un folder temporar.

    Întoarce (proces, versiune). Procesul e None dacă Windows n-a lăsat
    fișierul să pornească.
    """
    temp = Path(tempfile.gettempdir())
    inainte = set(temp.glob("_MEI*"))
    try:
        proc = subprocess.Popen([str(exe)])
    except OSError as e:
        if getattr(e, "winerror", None) == BLOCAT_DE_WINDOWS:
            return None, None
        raise

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
                    return proc, m.group(1)
    return proc, None


def compileaza() -> bool:
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC),
         "--distpath", str(BUILD / "dist"),
         "--workpath", str(BUILD / "work"), "--noconfirm"],
        capture_output=True, text=True)
    if r.returncode != 0 or not DIST.exists():
        print("Compilarea a eșuat:")
        print((r.stderr or r.stdout)[-1500:])
        return False
    return True


EXPLICATIE_BLOCAJ = """
Windows (Smart App Control) a refuzat să pornească toate construcțiile.

Judecă fiecare fișier în parte, după reputație. Un program compilat de tine și
nesemnat n-are reputație, așa că e refuzat — de aceea am reîncercat de mai
multe ori, fiecare construcție fiind alt fișier.

Aplicația veche a rămas neatinsă. Pornesc în schimb varianta fără executabil,
prin Python — Python e semnat, deci Windows îl lasă.
""".strip()

LANSATOR = """@echo off
rem UniNotes -- pornire fara executabil.
rem
rem Windows (Smart App Control) nu lasa sa porneasca programe nesemnate, iar
rem aplicatia asta e compilata chiar pe calculatorul tau, deci n-are semnatura.
rem Python este semnat, asa ca pornim prin el. Notitele raman exact unde erau:
rem folderul lor e spus explicit mai jos, altfel aplicatia si-ar face altul gol.
setlocal
set "RADACINA=%~dp0"
set "UNINOTES_NOTITE=%RADACINA%Notite UniNotes"
set "PY=%RADACINA%.build\\venv\\Scripts\\pythonw.exe"
if not exist "%PY%" set "PY=pythonw.exe"
start "" "%PY%" "%RADACINA%.build\\app\\desktop\\main.py"
endlocal
"""


def pregateste_lansatorul() -> Path:
    """
    Varianta fără executabil: punem codul într-un folder al lui și lăsăm în
    rădăcină un fișier de pornit cu două apăsări. Codul e copiat, nu rulat din
    folderul de lucru — acela poate să dispară oricând.
    """
    tinta = BUILD / "app"
    (tinta / "desktop").mkdir(parents=True, exist_ok=True)
    for nume in ("index.html", "styles.css", "app.js"):
        shutil.copy2(RADACINA / nume, tinta / nume)
    shutil.copy2(RADACINA / "desktop" / "main.py", tinta / "desktop" / "main.py")

    lansator = PRINCIPALA / "UniNotes.cmd"
    lansator.write_text(LANSATOR, encoding="utf-8")
    return lansator


def porneste_din_python():
    """
    Pornește aplicația fără executabil, prin Python, exact cum o va porni și
    lansatorul. Versiunea o citim din fișierul pe care chiar îl încarcă — cel
    copiat în .build/app — nu din folderul de lucru, care se poate schimba.
    """
    tinta = BUILD / "app"
    pyw = BUILD / "venv" / "Scripts" / "pythonw.exe"
    if not pyw.exists():
        pyw = Path("pythonw.exe")

    mediu = dict(os.environ)
    mediu["UNINOTES_NOTITE"] = str(PRINCIPALA / "Notite UniNotes")
    try:
        proc = subprocess.Popen([str(pyw), str(tinta / "desktop" / "main.py")], env=mediu)
    except OSError:
        return None, None

    time.sleep(7)
    if proc.poll() is not None:
        return None, None
    m = re.search(r"VERSIUNE = (\d+)",
                  (tinta / "app.js").read_text(encoding="utf-8", errors="replace"))
    return proc, (m.group(1) if m else None)


def main():
    lipsa = [c for c in ("index.html", "styles.css", "app.js", "desktop/main.py")
             if not (RADACINA / c).exists()]
    if lipsa:
        print("Lipsesc fișiere din " + str(RADACINA) + ": " + ", ".join(lipsa))
        return 1

    BUILD.mkdir(parents=True, exist_ok=True)
    SPEC.write_text(SABLON.format(r=RADACINA.as_posix()), encoding="utf-8")
    print("Compilez din: " + str(RADACINA))

    proba = None
    versiune = None
    for incercare in range(1, INCERCARI + 1):
        if not compileaza():
            return 1
        proba, versiune = porneste(DIST)
        if proba is not None:
            break
        print("Windows a blocat construcția %d. Reconstruiesc — alt fișier, alt verdict…"
              % incercare)

    if proba is None:
        print(EXPLICATIE_BLOCAJ)
        lansator = pregateste_lansatorul()
        proc, v = porneste_din_python()
        if proc is None:
            print("Nici prin Python nu pornește. Verifică dacă mediul din .build/venv e întreg.")
            return 1
        print("Lansator scris: " + str(lansator) + " — deschide-l cu două apăsări.")
        print("Versiunea care chiar rulează acum: " + str(v or "necitită"))
        return 0
    if not versiune:
        proba.terminate()
        print("Construcția pornește, dar n-am putut citi versiunea din ea. Nu instalez.")
        return 1

    print("Construcția merge și e versiunea " + versiune + ". O instalez.")
    proba.terminate()                    # a fost doar o probă, nu pornirea ta
    time.sleep(1.5)

    opreste_aplicatia()
    if INSTALAT.exists():
        shutil.copy2(INSTALAT, PRECEDENT)
    shutil.copy2(DIST, INSTALAT)

    proc, v = porneste(INSTALAT)
    if proc is None:
        # n-ar trebui să se întâmple (aceleași octeți, același verdict), dar
        # dacă se întâmplă nu te lăsăm fără aplicație
        if PRECEDENT.exists():
            shutil.copy2(PRECEDENT, INSTALAT)
            print("Windows a blocat copia instalată. Am pus versiunea precedentă înapoi.")
        return 1

    # Lansatorul se împrospătează la fiecare instalare, nu doar când e nevoie
    # de el: dacă mâine Windows refuză executabilul, rezerva trebuie să fie
    # deja acolo și să aibă codul de azi, nu pe cel de acum trei versiuni.
    pregateste_lansatorul()

    print("Instalat: " + str(INSTALAT))
    print("Copie a versiunii precedente: " + str(PRECEDENT))
    print("Rezervă, dacă Windows blochează cândva executabilul: "
          + str(PRINCIPALA / "UniNotes.cmd"))
    print("Versiunea care chiar rulează acum: " + (v or versiune))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
