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

Interfața e gândită pentru o singură mână: butonul rotund de „notiță nouă" stă jos-dreapta,
bara de formatare se lipește deasupra tastaturii cât scrii, iar acțiunile mai rare
(fixare, favorite, export, printare) sunt strânse în meniul `⋮`. În josul barei laterale
scrie versiunea instalată — util ca să știi dacă telefonul a preluat o actualizare.

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
  Le adaugi scriind în câmpul de sub titlu (Enter sau butonul „+"), cu sugestii din cele
  folosite deja; le scoți din notiță cu „×" de pe etichetă. Din bara laterală, „×" de pe o
  etichetă o șterge din **toate** notițele, după o confirmare care îți spune câte sunt
  afectate — și se poate anula.
- **Căutare** în titlu, conținut, etichete și denumirea materiei, cu evidențierea potrivirilor.
- **Editor Markdown** cu previzualizare: titluri, îngroșat/înclinat, liste, liste de bifat,
  citate, cod, tabele, linkuri. Listele se continuă automat la Enter.
- **Gesturi pe notițe, în listă:**
  - **spre dreapta → favorită** (fundal galben cu stea, notița revine cu un arc);
  - **spre stânga → ștergere** (fundal roșu, notița alunecă afară și rândul se strânge),
    cu **Anulează** în mesajul care apare;
  - **apăsare lungă → favorită**, dacă preferi așa.

  Pe calculator ai și butoane care apar pe notiță când treci cu mouse-ul peste ea.
  Pe telefon gestul folosește evenimentele de atingere (nu pointer events), fiindcă iOS
  decide devreme că mișcarea e derulare și retrage pointerul.
- **Ziua și ora, în timp real**, în bara de jos a editorului, cât scrii. Butonul cu ceas
  din bara de formatare inserează data și ora în text, unde ai cursorul.
- **Orar**, din bara laterală. Ține orele săptămânii și îți spune ce urmează:
  - cardul **Astăzi** arată orele zilei, cu ora curentă marcată „acum" și următoarea
    „în N min"; butonul „Orar" din meniu arată ora următoare (sau „acum");
  - pe calculator vezi toată săptămâna deodată, pe telefon o zi pe rând, cu file;
  - o dată pe zi, la deschidere, primești un mesaj scurt cu ce ai în ziua respectivă;
  - orele se pot adăuga și de mână (materie, zi, interval, tip, sala, profesor,
    săptămână pară/impară);
  - dacă ora e legată de o materie existentă, cardul preia culoarea materiei și are un
    buton care te duce direct la notițele ei.
- **Orarul citit dintr-o poză** — apeși „Scanează poza", alegi fotografia tabelului cu
  orarul, iar Claude îl citește și îl transformă în ore. Înainte să se salveze ceva, vezi
  lista a ce s-a înțeles și poți scoate rândurile greșite; apoi alegi „Adaugă la orar" sau
  „Înlocuiește orarul". Materiile care nu există încă pot fi create cu un buton.

  **Scanarea merge fără niciun cont și fără nicio cheie.** Fără cheie, poza e citită chiar
  pe dispozitiv (Tesseract, în browser): nu iese nimic în internet, e gratis și merge pe
  orice telefon. Prima citire descarcă vreo 6 MB, o singură dată.

  Cu o cheie, poza e citită de un model care „vede" imagini și rezultatul e vizibil mai bun.
  Lipești cheia de la oricare dintre cele două — aplicația își dă seama singură care e, după
  cum începe:

  | Cum citește | Cost | Cheia | Cât de exact |
  | --- | --- | --- | --- |
  | **pe dispozitiv** (implicit) | gratis, fără cont | — | ziua și ora ies de obicei bine; sălile și tipul orei trebuie deseori corectate |
  | [Google AI Studio](https://aistudio.google.com/apikey) | **gratuit**, fără card | `AIza…` | foarte bun; poza ajunge la Google, iar pe planul gratuit datele pot fi folosite pentru îmbunătățirea serviciilor |
  | [Anthropic (Claude)](https://console.anthropic.com/settings/keys) | câțiva cenți | `sk-ant-…` | foarte bun; cere card, dar pozele nu sunt folosite pentru antrenare |

  **Cheia rămâne doar pe dispozitivul tău**: stă separat de notițe, deci nu intră în copiile
  de siguranță exportate. Oricum ar fi citită poza, vezi lista înainte să se salveze ceva.
- **Notiță pornită din orar** — din cardul „Astăzi", butonul de lângă o oră creează o notiță
  cu materia, tipul, numărul de ordine și data deja completate („Curs 4 — Analiză Matematică"),
  iar cursorul sare direct în text. Dacă ora nu e legată de nicio materie, materia se creează.
- **Săptămâni pare și impare** — spui o dată „săptămâna asta e pară", iar de acolo încolo
  paritatea se calculează singură. Orele care nu au loc săptămâna asta nu mai apar la
  „Astăzi" și nu mai declanșează „acum"; în grilă rămân vizibile, dar stinse. Setarea apare
  doar dacă orarul chiar are ore alternative.
- **Termene și examene**, cu buton propriu în meniu: examene, colocvii, parțiale, predări.
  Lista e grupată în restante / astăzi / zilele următoare / mai târziu / făcute, insigna arată
  câte zile mai sunt până la cel mai apropiat, iar anunțul de dimineață pomenește ce bate la ușă.
- **Poze în notițe** — butonul cu aparat foto din bara de formatare inserează o fotografie
  (tabla, un slide); pe telefon alegi între cameră și galerie. Pozele sunt micșorate la
  1600 px, intră în copiile de siguranță și apar și la printare. În browser stau în
  IndexedDB, iar în aplicația de Windows ca fișiere în `Notite UniNotes\imagini`.
- **Repetiție pentru examen** — orice linie de forma `întrebare :: răspuns` din notițe devine
  o întrebare de repetat, la intervale care cresc (1, 3, 7, 16, 35, 75 de zile). O întrebare
  greșită revine peste zece minute și pleacă înapoi de la o zi. Spațiile din jurul lui `::`
  contează, ca `std::vector` din notițele de programare să nu devină întrebare.
- **Sincronizare între telefon și calculator** — printr-un gist secret din contul tău de
  GitHub: pui același jeton pe ambele, trimiți de pe unul și aduci pe celălalt. Trimiterea și
  aducerea sunt manuale, cu confirmare care îți spune câte notițe înlocuiești, și cu
  avertisment dacă pe cont e o versiune mai nouă decât ultima pe care ai văzut-o.

  „Secret" la GitHub înseamnă nelistat și negăsibil prin căutare, dar **nu** protejat prin
  parolă: cine are adresa gistului îl poate deschide. Pentru notițe de facultate e în regulă;
  pentru altceva, mai bine nu.
- **Fixare** (notița stă sus) și **favorite**.
- **Arhivă** pentru notițele terminate, ca să nu aglomereze lista.
- **Mod întunecat implicit**, pentru sesiunile de învățat de seara. Dacă îl schimbi pe
  luminos din bara laterală, alegerea ta rămâne.
- **Export**: o notiță ca `.md`, sau tot ce ai ca `.json`, prin fereastra obișnuită
  „Salvează ca". **Import** înapoi din `.json`.
- **Printare direct din aplicație** — butonul cu imprimantă din bara editorului, sau
  `Ctrl+P`. Se deschide dialogul obișnuit de printare, de unde alegi imprimanta sau
  *Salvează ca PDF*. Pe hârtie ajunge doar notița — titlul, materia, etichetele și data,
  apoi conținutul formatat; fără bara laterală, fără butoane.

## Scurtături

| Tastă | Acțiune |
| --- | --- |
| `Ctrl+N` | Notiță nouă |
| `Ctrl+K` | Caută |
| `Ctrl+S` | Salvează acum |
| `Ctrl+P` | Printează notița |
| `Ctrl+E` | Previzualizare Markdown |
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
| `desktop\test_api.py` | test automat pentru export, import și pregătirea printării |
| `desktop\test_print.py` | test automat: verifică dacă fereastra deschide dialogul de printare |

Interfața rămâne un web app obișnuit — poți deschide `index.html` direct în browser dacă
vrei; atunci notițele se salvează în browser, nu în fișier.

## Cum funcționează pe dinăuntru

Orarul, termenele și starea repetițiilor stau în același fișier cu notițele, sub cheile
`orar`, `termene` și `repetitii`. Fișierele făcute înainte ca ele să existe nu le au — se
adaugă goale la citire, deci copiile vechi se deschid normal. La fel, intrările cu tipuri
greșite sau valori imposibile sunt aruncate la încărcare, ca un fișier editat de mână să nu
împiedice pornirea.

Pozele nu stau în fișierul cu notițe: sunt prea mari. Un singur depozit cu `pune`/`ia`/
`sterge` alege singur unde scrie — IndexedDB în browser, fișiere în `imagini` pe desktop —
deci restul codului nu știe unde sunt. În Markdown apar ca `![poză](uninotes:<id>)`, iar
sursa se completează după randare, fiindcă citirea e asincronă; la printare o așteptăm
explicit, altfel pozele ar ieși goale pe hârtie. La exportul unei notițe ca `.md` poza e
inclusă în fișier, fiindcă `uninotes:...` n-are niciun înțeles în afara aplicației.

Repetiția își ține starea pe amprenta întrebării, nu pe poziția liniei în text: așa
supraviețuiește editării și rearanjării notiței.

Citirea pe dispozitiv nu trimite poza nicăieri. Tesseract dă înapoi fiecare cuvânt împreună
cu poziția lui în imagine — textul citit „la rând" e inutilizabil pentru un tabel, fiindcă
sare între coloane, dar din coordonate se poate reconstrui grila: cuvintele care sunt nume
de zile dau coloanele, intervalele orare dau rândurile, granița dintre două benzi vecine
trece prin mijlocul distanței dintre centrele lor, iar fiecare cuvânt rămas cade în caseta
în care se află. Merge și cu orarele întoarse, cu zilele pe rânduri. Înainte de citire poza
e trecută în alb-negru cu prag Otsu și adusă la ~2400 px; fără pasul ăsta, o poză înclinată
și cu umbră pierde rânduri întregi. Cuvintele citite nesigur sunt scoase din denumiri —
mai bine o denumire scurtă decât una cu litere inventate.

Scanarea prin cheie e singurul moment în care aplicația vorbește cu ceva din afară. Poza e
micșorată în browser (canvas, maxim 2200 px pe latura lungă, JPEG) și trimisă cu cheia ta
direct de pe dispozitiv — nu există server intermediar. Cei doi furnizori stau într-un
tabel (`FURNIZORI` din `app.js`): fiecare își spune adresa, antetele, forma cererii și de
unde se scoate răspunsul, deci restul codului nu știe cu cine vorbește.

| | Google | Anthropic |
| --- | --- | --- |
| adresă | `generativelanguage.googleapis.com/v1beta/interactions` | `api.anthropic.com/v1/messages` |
| autentificare | antetul `x-goog-api-key` | antetul `x-api-key` |
| model | `gemini-3.6-flash` | `claude-opus-5` |
| schema | `response_format.schema` | `output_config.format` |
| răspuns | `output_text` | primul bloc `text` |

Cheia merge în antet, niciodată în adresă, ca să nu ajungă în jurnale. Răspunsul e cerut ca
JSON după aceeași schemă fixă la ambii, așa că nu trebuie ghicit din text liber; orele care
ies din schemă sau au intervale imposibile sunt aruncate înainte să ajungă pe ecran. Textul
din poză e tratat ca date, nu ca instrucțiuni. Cheia se ține în `localStorage`, separat de
notițe, ca să nu plece în backup-uri.

La printare, WebView2 e o excepție: ignoră `window.print()` din JavaScript, așa că fereastra
de Windows cheamă dialogul propriu al motorului (`ShowPrintUI`) prin puntea de Python. În
browser și pe telefon se folosește `window.print()` obișnuit. Dacă apelul nativ nu reușește,
aplicația deschide notița în browserul implicit, ca să poți printa oricum.

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
