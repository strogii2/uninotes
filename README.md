# UniNotes — notițe pentru universitate

Aplicație de notițe pentru studenți. Aceeași aplicație rulează în trei feluri: program
Windows de sine stătător, aplicație instalată pe telefon, sau direct în browser.

**Online:** https://strogii2.github.io/uninotes/

## Pe telefon (iPhone și Android)

Deschide **https://strogii2.github.io/uninotes/** pe telefon și instaleaz-o pe ecranul
principal:

- **iPhone (Safari):** apasă butonul **Partajează** (pătratul cu săgeata în sus) →
  derulează în jos → **Adaugă pe ecranul principal** → *Adaugă*.
  Trebuie folosit Safari; din Chrome pe iPhone opțiunea nu apare.
- **Android (Chrome):** meniul `⋮` → **Instalează aplicația** (sau *Adaugă pe ecranul
  principal*).

După instalare capătă iconiță proprie, se deschide pe tot ecranul fără bara de browser și
**merge fără internet** — tot ce îi trebuie e ținut în telefon de la prima deschidere.

Notițele de pe telefon sunt separate de cele de pe calculator; nu se sincronizează între
ele. Ca să le muți dintr-o parte în alta, folosește **Backup** (export `.json`) pe un
dispozitiv și **Import** pe celălalt.

> Pe iPhone nu se poate face o aplicație din App Store fără un Mac și un cont de
> dezvoltator Apple plătit. Varianta instalată din Safari e cea mai apropiată de o
> aplicație adevărată și, la folosirea de zi cu zi, se comportă la fel.

## Pe calculator: cum o pornești

Dublu-click pe **`UniNotes.exe`**, sau pe scurtătura **UniNotes** de pe desktop.

Prima pornire durează câteva secunde (executabilul se dezarhivează în memorie), apoi merge
instant. Ca s-o ai la îndemână: click-dreapta pe scurtătură → *Fixare în bara de activități*.

Aplicația e **portabilă** — poți muta `UniNotes.exe` oriunde (stick, alt folder, alt
calculator cu Windows). Își face singură folderul de notițe acolo unde e pus.

## Unde sunt notițele

Lângă executabil, în folderul **`Notite UniNotes\notite.json`**. Butonul
**„Folderul cu notițe"** din bara laterală ți-l deschide direct în Explorer.

Asta înseamnă că notițele sunt fișiere obișnuite pe calculator: le poți copia, pune pe
stick, sincroniza cu Drive sau salva pe alt disc. Dacă muți executabilul, ia și folderul
`Notite UniNotes` cu el.

Dacă pui aplicația într-un loc unde Windows nu lasă să se scrie (de exemplu
`C:\Program Files`), notițele merg automat în `%APPDATA%\UniNotes`.

Salvarea e automată, la fiecare tastă. Fișierul se scrie atomic — întâi într-un fișier
temporar, apoi se înlocuiește cel real — ca o pană de curent să nu-l lase la jumătate.
Dacă fișierul ajunge totuși corupt, aplicația îl pune deoparte ca `notite.json.stricat`
și pornește curat, în loc să refuze să deschidă.

## Ce poate

- **Organizare pe materii** — fiecare materie are culoare proprie și, opțional, numele profesorului.
- **Etichete** libere (`#curs`, `#laborator`, `#examen`) cu filtrare rapidă din bara laterală.
- **Căutare** în titlu, conținut, etichete și denumirea materiei, cu evidențierea potrivirilor.
- **Editor Markdown** cu previzualizare: titluri, îngroșat/înclinat, liste, liste de bifat,
  citate, cod, tabele, linkuri. Listele se continuă automat la Enter.
- **Fixare** (notița stă sus) și **favorite**.
- **Arhivă** pentru notițele terminate, ca să nu aglomereze lista.
- **Mod întunecat**, pentru sesiunile de învățat de seara.
- **Export**: o notiță ca `.md`, sau tot ce ai ca `.json`, prin fereastra obișnuită
  „Salvează ca". **Import** înapoi din `.json`.
- **Printare / PDF** — notița se pregătește curat, fără interfață, și se deschide în
  browserul implicit, unde apeși `Ctrl+P`. (Fereastra aplicației nu poate deschide singură
  dialogul de printare.)

## Scurtături

| Tastă | Acțiune |
| --- | --- |
| `Ctrl+N` | Notiță nouă |
| `Ctrl+K` | Caută |
| `Ctrl+S` | Salvează acum |
| `Ctrl+P` | Previzualizare Markdown |
| `Ctrl+D` | Favorită |
| `Ctrl+Shift+P` | Fixează sus |
| `Ctrl+B` / `Ctrl+I` | Îngroșat / înclinat |
| `Esc` | Închide fereastra deschisă |

## Fișiere

| Fișier | Ce conține |
| --- | --- |
| `UniNotes.exe` | aplicația propriu-zisă (13 MB, un singur fișier) |
| `index.html` | structura interfeței și setul de iconițe SVG |
| `styles.css` | culorile, temele light/dark, layout-ul |
| `app.js` | starea, salvarea, parserul Markdown, toate interacțiunile |
| `manifest.webmanifest` | datele de instalare pe telefon (nume, iconițe, culori) |
| `sw.js` | service worker — ține aplicația în telefon ca să meargă offline |
| `icons\` | iconițele pentru iOS și Android |
| `desktop\make_png_icons.py` | generează iconițele pentru telefon |
| `desktop\server_telefon.py` | server local cu listă albă, pentru testat pe telefon în rețea |
| `desktop\main.py` | fereastra nativă și puntea către fișierele de pe disc |
| `desktop\icon.ico` | iconița aplicației |
| `desktop\make_icon.py` | generează iconița |
| `desktop\selftest.py` | test automat: pornește aplicația și verifică salvarea pe disc |
| `desktop\test_api.py` | test automat pentru export, import și printare |

Interfața rămâne un web app obișnuit — poți deschide `index.html` direct în browser dacă
vrei; atunci notițele se salvează în browser, nu în fișier.

## Cum funcționează pe dinăuntru

Fereastra e nativă (WinForms), iar interfața e randată de **Edge WebView2** — motorul deja
prezent în Windows 11. De asta executabilul are 13 MB și nu 200: nu împachetează un browser
propriu. Interfața se servește pe `127.0.0.1`, pe un port ales de sistem, care ascultă doar
local. Partea de Python se ocupă doar de fișiere: citire, scriere atomică și dialogurile
native de salvare/deschidere.

## Dacă vrei s-o modifici și s-o recompilezi

```powershell
cd C:\Users\carpd\UniNotes
python -m venv .build\venv
.build\venv\Scripts\python.exe -m pip install pywebview pyinstaller

# testele (opțional, dar recomandat)
.build\venv\Scripts\python.exe desktop\selftest.py
.build\venv\Scripts\python.exe desktop\test_api.py

# executabilul
.build\venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name UniNotes `
  --icon C:\Users\carpd\UniNotes\desktop\icon.ico `
  --add-data "C:\Users\carpd\UniNotes\index.html;web" `
  --add-data "C:\Users\carpd\UniNotes\styles.css;web" `
  --add-data "C:\Users\carpd\UniNotes\app.js;web" `
  --distpath .build\dist --workpath .build\work --specpath .build `
  C:\Users\carpd\UniNotes\desktop\main.py
```

Executabilul rezultat e în `.build\dist\UniNotes.exe`. Pentru modificări doar de aspect sau
de comportament în interfață (`index.html`, `styles.css`, `app.js`) e mai rapid să rulezi
`.build\venv\Scripts\python.exe desktop\main.py` — vezi schimbările fără să recompilezi.

## Design

- **Culori:** albastru `#2563EB` (focus) + verde `#059669` (accent), pe fundal deschis `#F5F7FB`.
- **Fonturi:** Plus Jakarta Sans pentru interfață, Lora pentru corpul notiței (se citește
  mai ușor la text lung), JetBrains Mono pentru cod. Fonturile se iau de la Google; fără
  internet aplicația merge la fel, doar cu fonturile de sistem.
- Tranziții de 150–300 ms, ținte de atingere de minim 44px pe ecrane mici, contrast conform
  WCAG AA, focus vizibil pentru navigarea de la tastatură, suport pentru
  `prefers-reduced-motion`.
