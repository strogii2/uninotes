/* ============================================================
   UniNotes — logica aplicației
   Vanilla JS, fără dependențe. Datele stau în localStorage.
   ============================================================ */
(function () {
  'use strict';

  const STORE_KEY = 'uninotes.v1';
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /* ==========================================================
     PUNTEA CU DISCUL
     În aplicația desktop (UniNotes.exe) notițele stau într-un fișier de pe disc,
     scris de Python. Deschisă direct în browser, aceeași interfață folosește
     localStorage, ca să rămână utilizabilă și așa.
     ========================================================== */
  // Aplicația desktop deschide pagina cu ?desktop=1. Puntea pywebview apare abia
  // după window.load, deci nu ne putem baza pe prezența ei ca să știm unde rulăm.
  const DESKTOP = new URLSearchParams(location.search).has('desktop');
  const api = () => (window.pywebview && window.pywebview.api) || null;

  function apiReady() {
    if (!DESKTOP) return Promise.resolve(false);
    if (api()) return Promise.resolve(true);
    return new Promise(resolve => {
      let settled = false;
      const done = () => { if (!settled) { settled = true; resolve(!!api()); } };
      window.addEventListener('pywebviewready', done, { once: true });
      setTimeout(done, 5000);   // plasă de siguranță, ca să nu rămână ecranul gol
    });
  }

  const PALETTE = ['#2563EB', '#059669', '#7C3AED', '#DB2777', '#EA580C',
                   '#0891B2', '#CA8A04', '#DC2626', '#4F46E5', '#16A34A'];

  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  const now = () => Date.now();

  /* ==========================================================
     STARE
     ========================================================== */
  let db = null;              // se încarcă la pornire (vezi boot())
  let ui = {
    filter: { type: 'all', subjectId: null, tag: null },
    query: '',
    sort: 'updated',
    activeId: null,
    preview: false
  };
  let saveTimer = null;
  let lastDeleted = null;

  function seed() {
    const s1 = uid(), s2 = uid(), s3 = uid();
    const t = now();
    return {
      version: 1,
      settings: { theme: 'light' },
      subjects: [
        { id: s1, name: 'Analiză Matematică', color: '#2563EB', prof: 'Prof. Popescu' },
        { id: s2, name: 'Programare Orientată pe Obiecte', color: '#059669', prof: 'Conf. Ionescu' },
        { id: s3, name: 'Fizică Generală', color: '#7C3AED', prof: '' }
      ],
      notes: [
        {
          id: uid(), subjectId: s1, title: 'Curs 1 — Limite de funcții',
          tags: ['curs', 'examen'], pinned: true, favorite: true, archived: false,
          createdAt: t - 864e5 * 3, updatedAt: t - 3600e3 * 5,
          content:
`# Limite de funcții

## Definiția cu vecinătăți
Fie \`f: D → R\` și \`a\` punct de acumulare al lui \`D\`.

> Spunem că **L** este limita lui *f* în *a* dacă pentru orice vecinătate V a lui L
> există o vecinătate U a lui a astfel încât f(U ∩ D \\ {a}) ⊂ V.

## Limite remarcabile
| Expresie | Limită |
| --- | --- |
| sin(x)/x, x→0 | 1 |
| (1 + 1/x)^x, x→∞ | e |
| (a^x − 1)/x, x→0 | ln a |

## De reținut pentru examen
- [x] Criteriul cleștelui
- [ ] Cazuri de nedeterminare: 0/0, ∞/∞, 0·∞
- [ ] Regula lui L'Hôpital — condiții de aplicare

---
*Seminar joi: exerciții 1–14 din culegere.*`
        },
        {
          id: uid(), subjectId: s2, title: 'Moștenire și polimorfism',
          tags: ['laborator', 'java'], pinned: false, favorite: false, archived: false,
          createdAt: t - 864e5 * 2, updatedAt: t - 3600e3 * 26,
          content:
`## Cei 4 piloni ai POO
1. Încapsulare
2. Moștenire
3. Polimorfism
4. Abstractizare

### Exemplu
\`\`\`java
abstract class Forma {
    abstract double arie();
}

class Cerc extends Forma {
    private final double r;
    Cerc(double r) { this.r = r; }
    @Override double arie() { return Math.PI * r * r; }
}
\`\`\`

**Atenție la examen:** metoda \`equals()\` se suprascrie mereu împreună cu \`hashCode()\`.

- [ ] Tema 2 — deadline vineri`
        },
        {
          id: uid(), subjectId: s3, title: 'Laborator — pendulul gravitațional',
          tags: ['laborator'], pinned: false, favorite: false, archived: false,
          createdAt: t - 864e5 * 6, updatedAt: t - 864e5 * 4,
          content:
`## Scopul lucrării
Determinarea accelerației gravitaționale **g** prin măsurarea perioadei pendulului simplu.

Formula de lucru: \`T = 2π√(l/g)\`  ⇒  \`g = 4π²l / T²\`

### Date măsurate
| l (m) | 10T (s) | T (s) |
| --- | --- | --- |
| 0.50 | 14.2 | 1.42 |
| 0.75 | 17.4 | 1.74 |
| 1.00 | 20.1 | 2.01 |

### Concluzie
Valoarea medie obținută: **g ≈ 9.79 m/s²**, eroare relativă sub 1%.`
        },
        {
          id: uid(), subjectId: null, title: 'Termene și examene — semestrul curent',
          tags: ['deadline'], pinned: true, favorite: false, archived: false,
          createdAt: t - 864e5 * 8, updatedAt: t - 3600e3 * 2,
          content:
`## De predat
- [ ] Referat Fizică — **vineri, ora 12:00**
- [ ] Tema 2 POO — vineri
- [x] Fișa de laborator 3

## Sesiune
> Analiză Matematică — scris + oral
> POO — proiect + test grilă

[Orarul facultății](https://example.edu/orar)`
        }
      ]
    };
  }

  function normalize(parsed) {
    if (!parsed || !Array.isArray(parsed.notes)) return null;
    parsed.subjects = parsed.subjects || [];
    parsed.settings = parsed.settings || { theme: 'light' };
    return parsed;
  }

  async function loadData() {
    if (await apiReady()) {
      try {
        return normalize(await api().load_data()) || seed();
      } catch (e) {
        console.warn('[UniNotes] nu am putut citi fișierul cu notițe', e);
        return seed();
      }
    }
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (!raw) return seed();
      return normalize(JSON.parse(raw)) || seed();
    } catch (e) {
      console.warn('[UniNotes] date corupte, pornesc de la zero', e);
      return seed();
    }
  }

  let saveFailed = false;

  function persist() {
    if (api()) {
      api().save_data(db).then(res => {
        if (res && res.ok === false && !saveFailed) {
          saveFailed = true;
          toast('Nu am putut scrie fișierul cu notițe: ' + res.error, 'err');
        }
      }).catch(() => {});
      return true;
    }
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(db));
      return true;
    } catch (e) {
      toast('Nu am putut salva — spațiu insuficient în browser.', 'err');
      return false;
    }
  }

  /* ==========================================================
     UTILE
     ========================================================== */
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  const fmtTime = new Intl.DateTimeFormat('ro-RO', { hour: '2-digit', minute: '2-digit' });
  const fmtDay = new Intl.DateTimeFormat('ro-RO', { day: 'numeric', month: 'short' });
  const fmtFull = new Intl.DateTimeFormat('ro-RO', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  function relTime(ts) {
    const d = now() - ts;
    if (d < 60e3) return 'acum';
    if (d < 3600e3) return 'acum ' + Math.floor(d / 60e3) + ' min';
    const date = new Date(ts), today = new Date();
    const sameDay = date.toDateString() === today.toDateString();
    if (sameDay) return 'azi ' + fmtTime.format(date);
    const y = new Date(today.getTime() - 864e5);
    if (date.toDateString() === y.toDateString()) return 'ieri ' + fmtTime.format(date);
    if (date.getFullYear() === today.getFullYear()) return fmtDay.format(date);
    return date.toLocaleDateString('ro-RO');
  }

  function subjectOf(note) {
    return db.subjects.find(s => s.id === note.subjectId) || null;
  }

  function plainExcerpt(md, max) {
    return md
      .replace(/```[\s\S]*?```/g, ' ')
      .replace(/[#>*_`|~-]/g, ' ')
      .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, max || 150);
  }

  async function saveAs(filename, content, type, okMsg) {
    if (api()) {
      const path = await api().save_file(filename, content);   // dialog nativ „Salvează ca”
      if (path) toast(okMsg + ' → ' + path.split('\\').pop(), 'ok');
      return;
    }
    const blob = new Blob([content], { type: type || 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(okMsg, 'ok');
  }

  function slug(s) {
    return (s || 'notita').toLowerCase()
      .replace(/[ăâà]/g, 'a').replace(/[îí]/g, 'i').replace(/[șş]/g, 's')
      .replace(/[țţ]/g, 't').replace(/[éè]/g, 'e')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'notita';
  }

  /* ==========================================================
     MARKDOWN
     ========================================================== */
  function inline(str) {
    const codes = [];
    let s = str.replace(/`([^`]+)`/g, (m, c) => {
      codes.push(c); return '\uE000C' + (codes.length - 1) + '\uE000';
    });
    // linkurile devin marcaje, altfel regula de mai jos ar rescrie chiar href-ul generat
    const links = [];
    const link = (url, txt) => {
      links.push('<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + txt + '</a>');
      return '\uE000L' + (links.length - 1) + '\uE000';
    };
    s = s.replace(/!\[([^\]]*)\]\([^)\s]+\)/g, '$1');                       // imagine → text alternativ
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, txt, url) => link(url, txt));
    s = s.replace(/(^|[\s(])(https?:\/\/[^\s<]+[^\s<.,;:)])/g,
      (m, pre, url) => pre + link(url, url));
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    s = s.replace(/(^|[^\w])_([^_\n]+)_/g, '$1<em>$2</em>');
    s = s.replace(/~~([^~]+)~~/g, '<s>$1</s>');
    s = s.replace(/==([^=]+)==/g, '<mark>$1</mark>');
    s = s.replace(/\uE000L(\d+)\uE000/g, (m, i) => links[+i]);
    return s.replace(/\uE000C(\d+)\uE000/g, (m, i) => '<code>' + codes[+i] + '</code>');
  }

  function renderMarkdown(src) {
    if (!src || !src.trim()) return '<p class="md-empty">Nimic de previzualizat încă.</p>';

    const blocks = [];
    let text = escapeHtml(src.replace(/\r\n/g, '\n'));
    text = text.replace(/```([\w+#-]*)\n?([\s\S]*?)```/g, (m, lang, code) => {
      blocks.push('<pre><code>' + code.replace(/\n$/, '') + '</code></pre>');
      return '\uE000B' + (blocks.length - 1) + '\uE000';
    });

    const lines = text.split('\n');
    const out = [];
    const stack = [];           // liste deschise: {tag, indent}
    let para = [], quote = [], table = null;
    // Blocurile de cod au colapsat mai multe linii într-una, deci indexul de linie
    // nu mai corespunde sursei. Numerotăm bifele în ordine și le regăsim la fel în sursă.
    let taskNo = 0;

    const closeLists = (toIndent) => {
      while (stack.length && stack[stack.length - 1].indent >= toIndent) {
        out.push('</' + stack.pop().tag + '>');
      }
    };
    const flushPara = () => { if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
    const flushQuote = () => { if (quote.length) { out.push('<blockquote>' + inline(quote.join(' ')) + '</blockquote>'); quote = []; } };
    const flushTable = () => {
      if (!table) return;
      const cells = row => row.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      const head = cells(table[0]);
      const body = table.slice(table.length > 1 && /^[\s|:-]+$/.test(table[1]) ? 2 : 1);
      let html = '<table><thead><tr>' + head.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr></thead>';
      if (body.length) {
        html += '<tbody>' + body.map(r =>
          '<tr>' + cells(r).map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') + '</tbody>';
      }
      table = null;
      out.push(html + '</table>');
    };
    const flushAll = () => { flushPara(); flushQuote(); flushTable(); closeLists(0); };

    lines.forEach((raw, idx) => {
      const line = raw.replace(/\s+$/, '');

      if (!line.trim()) { flushAll(); return; }

      const ph = line.match(/^\uE000B(\d+)\uE000$/);
      if (ph) { flushAll(); out.push(blocks[+ph[1]]); return; }

      const h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        flushAll();
        const lvl = Math.min(h[1].length, 3);
        out.push('<h' + lvl + '>' + inline(h[2]) + '</h' + lvl + '>');
        return;
      }

      if (/^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flushAll(); out.push('<hr>'); return; }

      const q = line.match(/^\s{0,3}&gt;\s?(.*)$/);
      if (q) { flushPara(); flushTable(); closeLists(0); quote.push(q[1]); return; }
      flushQuote();

      if (/^\s{0,3}\|.*\|\s*$/.test(line)) { flushPara(); closeLists(0); (table = table || []).push(line.trim()); return; }
      flushTable();

      const li = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
      if (li) {
        flushPara();
        const indent = Math.floor(li[1].length / 2) + 1;
        const tag = /^\d/.test(li[2]) ? 'ol' : 'ul';
        closeLists(indent + 1);
        const top = stack[stack.length - 1];
        if (!top || top.indent < indent) { out.push('<' + tag + '>'); stack.push({ tag, indent }); }
        else if (top.tag !== tag) { out.push('</' + stack.pop().tag + '>'); out.push('<' + tag + '>'); stack.push({ tag, indent }); }

        const task = li[3].match(/^\[( |x|X)\]\s*(.*)$/);
        if (task) {
          const done = task[1].toLowerCase() === 'x';
          out.push('<li class="task' + (done ? ' done' : '') + '">' +
            '<input type="checkbox" data-task="' + (taskNo++) + '"' + (done ? ' checked' : '') +
            ' aria-label="Bifează"><span>' + inline(task[2]) + '</span></li>');
        } else {
          out.push('<li>' + inline(li[3]) + '</li>');
        }
        return;
      }
      closeLists(0);
      para.push(line.trim());
    });

    flushAll();
    return out.join('\n');
  }

  /* ==========================================================
     TOAST / CONFIRM
     ========================================================== */
  function toast(msg, kind, action) {
    const el = document.createElement('div');
    el.className = 'toast' + (kind ? ' toast--' + kind : '');
    const icon = kind === 'err' ? 'i-x' : 'i-check';
    el.innerHTML = '<svg class="ic"><use href="#' + icon + '"></use></svg><span>' + escapeHtml(msg) + '</span>';
    if (action) {
      const b = document.createElement('button');
      b.textContent = action.label;
      b.addEventListener('click', () => { action.fn(); dismiss(); });
      el.appendChild(b);
    }
    $('#toasts').appendChild(el);
    let timer = setTimeout(dismiss, action ? 6000 : 2600);
    function dismiss() {
      clearTimeout(timer);
      if (!el.isConnected) return;
      el.classList.add('is-out');
      setTimeout(() => el.remove(), 220);
    }
  }

  function confirmDialog(title, text, okLabel) {
    return new Promise(resolve => {
      const dlg = $('#confirmModal');
      $('#confirmTitle').textContent = title;
      $('#confirmText').textContent = text;
      $('#confirmYes').textContent = okLabel || 'Confirmă';
      const done = v => {
        $('#confirmYes').removeEventListener('click', yes);
        $('#confirmNo').removeEventListener('click', no);
        dlg.removeEventListener('close', onClose);
        if (dlg.open) dlg.close();
        resolve(v);
      };
      const yes = () => done(true), no = () => done(false), onClose = () => done(false);
      $('#confirmYes').addEventListener('click', yes);
      $('#confirmNo').addEventListener('click', no);
      dlg.addEventListener('close', onClose);
      dlg.showModal();
    });
  }

  /* ==========================================================
     SELECTARE / FILTRARE
     ========================================================== */
  function visibleNotes() {
    const q = ui.query.trim().toLowerCase();
    let list = db.notes.filter(n => {
      if (ui.filter.type === 'archive') { if (!n.archived) return false; }
      else if (n.archived) return false;

      if (ui.filter.type === 'fav' && !n.favorite) return false;
      if (ui.filter.type === 'subject' && n.subjectId !== ui.filter.subjectId) return false;
      if (ui.filter.tag && !(n.tags || []).includes(ui.filter.tag)) return false;

      if (q) {
        const s = subjectOf(n);
        const hay = (n.title + ' ' + n.content + ' ' + (n.tags || []).join(' ') + ' ' + (s ? s.name : '')).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    const byTitle = (a, b) => (a.title || '').localeCompare(b.title || '', 'ro', { sensitivity: 'base' });
    if (ui.sort === 'title') list.sort(byTitle);
    else if (ui.sort === 'created') list.sort((a, b) => b.createdAt - a.createdAt);
    else if (ui.sort === 'subject') list.sort((a, b) => {
      const sa = subjectOf(a), sb = subjectOf(b);
      const na = sa ? sa.name : 'zzz', nb = sb ? sb.name : 'zzz';
      return na.localeCompare(nb, 'ro') || b.updatedAt - a.updatedAt;
    });
    else list.sort((a, b) => b.updatedAt - a.updatedAt);

    if (ui.sort !== 'subject') list.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
    return list;
  }

  function activeNote() { return db.notes.find(n => n.id === ui.activeId) || null; }

  /* ==========================================================
     RANDARE — SIDEBAR
     ========================================================== */
  function renderSidebar() {
    const live = db.notes.filter(n => !n.archived);
    $('#cAll').textContent = live.length;
    $('#cFav').textContent = live.filter(n => n.favorite).length;
    $('#cArch').textContent = db.notes.filter(n => n.archived).length;

    $$('.nav__item').forEach(b =>
      b.classList.toggle('is-active', ui.filter.type === b.dataset.filter));

    const wrap = $('#subjectList');
    wrap.innerHTML = '';
    if (!db.subjects.length) {
      const p = document.createElement('p');
      p.className = 'list-empty';
      p.style.padding = '4px 12px 8px';
      p.style.textAlign = 'left';
      p.style.fontSize = '12.5px';
      p.textContent = 'Adaugă prima materie cu „+”.';
      wrap.appendChild(p);
    }
    db.subjects.forEach(s => {
      const count = live.filter(n => n.subjectId === s.id).length;
      const btn = document.createElement('button');
      btn.className = 'subject' + (ui.filter.type === 'subject' && ui.filter.subjectId === s.id ? ' is-active' : '');
      btn.setAttribute('role', 'listitem');
      btn.title = s.prof ? s.name + ' — ' + s.prof : s.name;
      btn.innerHTML =
        '<span class="dot" style="background:' + s.color + ';color:' + s.color + '"></span>' +
        '<span class="subject__name"></span>' +
        '<span class="count">' + count + '</span>' +
        '<span class="subject__edit icon-btn icon-btn--sm" role="button" tabindex="0" aria-label="Editează materia">' +
        '<svg class="ic"><use href="#i-edit"></use></svg></span>';
      $('.subject__name', btn).textContent = s.name;
      btn.addEventListener('click', e => {
        if (e.target.closest('.subject__edit')) { openSubjectModal(s); return; }
        setFilter('subject', s.id);
      });
      $('.subject__edit', btn).addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); openSubjectModal(s); }
      });
      wrap.appendChild(btn);
    });

    const tags = new Map();
    live.forEach(n => (n.tags || []).forEach(t => tags.set(t, (tags.get(t) || 0) + 1)));
    const cloud = $('#tagCloud');
    cloud.innerHTML = '';
    Array.from(tags.entries()).sort((a, b) => b[1] - a[1]).slice(0, 14).forEach(([t, c]) => {
      const b = document.createElement('button');
      b.className = 'tag-pill' + (ui.filter.tag === t ? ' is-active' : '');
      b.textContent = '#' + t + ' ' + c;
      b.addEventListener('click', () => {
        ui.filter.tag = ui.filter.tag === t ? null : t;
        renderSidebar(); renderList();
      });
      cloud.appendChild(b);
    });

    const count = db.notes.length;
    $('#brandSub').textContent = count + (count === 1 ? ' notiță salvată' : ' notițe salvate');
  }

  /* ==========================================================
     RANDARE — LISTĂ
     ========================================================== */
  function highlight(text, q) {
    const safe = escapeHtml(text);
    if (!q) return safe;
    const rx = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    return safe.replace(rx, '<mark>$1</mark>');
  }

  function renderList() {
    const titles = { all: 'Toate notițele', fav: 'Favorite', archive: 'Arhivă' };
    let title = titles[ui.filter.type] || 'Notițe';
    if (ui.filter.type === 'subject') {
      const s = db.subjects.find(x => x.id === ui.filter.subjectId);
      title = s ? s.name : 'Materie';
    }
    if (ui.filter.tag) title += ' · #' + ui.filter.tag;
    $('#listTitle').textContent = title;

    const list = visibleNotes();
    const wrap = $('#notesList');
    wrap.innerHTML = '';

    if (!list.length) {
      const d = document.createElement('div');
      d.className = 'list-empty';
      d.innerHTML = ui.query
        ? '<strong>Niciun rezultat</strong>Nicio notiță nu conține „' + escapeHtml(ui.query) + '”.'
        : (ui.filter.type === 'archive'
          ? '<strong>Arhiva e goală</strong>Notițele arhivate apar aici.'
          : '<strong>Nicio notiță aici</strong>Apasă „Notiță nouă” ca să începi.');
      wrap.appendChild(d);
      return;
    }

    const q = ui.query.trim();
    let lastGroup = null;
    list.forEach((n, i) => {
      let group = null;
      if (ui.sort === 'subject') { const s = subjectOf(n); group = s ? s.name : 'Fără materie'; }
      else if (n.pinned) group = 'Fixate';
      else if (list.some(x => x.pinned)) group = 'Restul';

      if (group && group !== lastGroup) {
        const g = document.createElement('div');
        g.className = 'group-label';
        g.textContent = group;
        wrap.appendChild(g);
        lastGroup = group;
      }

      const s = subjectOf(n);
      const card = document.createElement('button');
      card.className = 'note-card' + (n.id === ui.activeId ? ' is-active' : '');
      card.setAttribute('role', 'listitem');
      card.style.animationDelay = Math.min(i * 22, 260) + 'ms';

      const flags =
        (n.pinned ? '<svg class="ic note-card__flag note-card__flag--pin"><use href="#i-pin"></use></svg>' : '') +
        (n.favorite ? '<svg class="ic note-card__flag note-card__flag--fav"><use href="#i-star"></use></svg>' : '');

      card.innerHTML =
        '<div class="note-card__top"><span class="note-card__title">' +
          highlight(n.title || 'Fără titlu', q) + '</span>' + flags + '</div>' +
        '<div class="note-card__excerpt">' + highlight(plainExcerpt(n.content) || 'Notiță goală', q) + '</div>' +
        '<div class="note-card__meta">' +
          (s ? '<span class="note-card__subject"><span class="dot" style="background:' + s.color + '"></span>' +
               escapeHtml(s.name) + '</span><span class="sep">·</span>' : '') +
          '<span>' + relTime(n.updatedAt) + '</span>' +
          ((n.tags || []).length ? '<span class="sep">·</span><span>#' + escapeHtml(n.tags[0]) +
            (n.tags.length > 1 ? ' +' + (n.tags.length - 1) : '') + '</span>' : '') +
        '</div>';

      card.addEventListener('click', () => openNote(n.id));
      wrap.appendChild(card);
    });
  }

  /* ==========================================================
     RANDARE — EDITOR
     ========================================================== */
  function renderSubjectSelect(note) {
    const sel = $('#subjectSelect');
    sel.innerHTML = '';
    const none = new Option('Fără materie', '');
    sel.appendChild(none);
    db.subjects.forEach(s => sel.appendChild(new Option(s.name, s.id)));
    sel.value = note.subjectId || '';
    const s = subjectOf(note);
    $('#subjDot').style.background = s ? s.color : 'var(--border-strong)';
  }

  function renderTags(note) {
    const wrap = $('#tagChips');
    wrap.innerHTML = '';
    (note.tags || []).forEach(t => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.innerHTML = '<span></span><button aria-label="Șterge eticheta ' + escapeHtml(t) +
        '"><svg class="ic"><use href="#i-x"></use></svg></button>';
      $('span', chip).textContent = t;
      $('button', chip).addEventListener('click', () => {
        note.tags = note.tags.filter(x => x !== t);
        touch(note); renderTags(note); renderSidebar(); renderList();
      });
      wrap.appendChild(chip);
    });
  }

  function renderStats(note) {
    const words = (note.content.trim().match(/\S+/g) || []).length;
    const mins = Math.max(1, Math.round(words / 190));
    $('#statMeta').textContent =
      words + (words === 1 ? ' cuvânt' : ' cuvinte') + ' · ~' + mins + ' min citit · modificat ' +
      fmtFull.format(new Date(note.updatedAt));
  }

  function renderEditor() {
    const note = activeNote();
    const ed = $('#editor'), empty = $('#emptyState');
    if (!note) { ed.hidden = true; empty.hidden = false; return; }
    empty.hidden = true; ed.hidden = false;

    $('#titleInput').value = note.title;
    $('#contentInput').value = note.content;
    renderSubjectSelect(note);
    renderTags(note);
    renderStats(note);

    $('#favBtn').setAttribute('aria-pressed', String(!!note.favorite));
    $('#pinBtn').setAttribute('aria-pressed', String(!!note.pinned));
    $('#archLabel').textContent = note.archived ? 'Scoate din arhivă' : 'Arhivează';
    setPreview(ui.preview);
  }

  function setPreview(on) {
    ui.preview = !!on;
    const note = activeNote();
    $('#previewBtn').setAttribute('aria-pressed', String(ui.preview));
    $('#contentInput').hidden = ui.preview;
    $('#toolbar').hidden = ui.preview;
    $('#previewPane').hidden = !ui.preview;
    if (ui.preview && note) $('#previewPane').innerHTML = renderMarkdown(note.content);
  }

  /* ==========================================================
     ACȚIUNI
     ========================================================== */
  function touch(note, quiet) {
    note.updatedAt = now();
    if (!quiet) markDirty();
    scheduleSave();
    renderStats(note);
  }

  function markDirty() {
    const f = $('#savedFlag');
    f.classList.add('is-dirty');
    f.textContent = 'Se salvează…';
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      if (persist()) {
        const f = $('#savedFlag');
        f.classList.remove('is-dirty');
        f.textContent = 'Salvat automat';
      }
      renderList();
      renderSidebar();
    }, 250);
  }

  function flushSave() {
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; persist(); }
  }

  function newNote() {
    const note = {
      id: uid(),
      subjectId: ui.filter.type === 'subject' ? ui.filter.subjectId : null,
      title: '', content: '',
      tags: ui.filter.tag ? [ui.filter.tag] : [],
      pinned: false, favorite: false, archived: false,
      createdAt: now(), updatedAt: now()
    };
    db.notes.unshift(note);
    if (ui.filter.type === 'archive' || ui.filter.type === 'fav') setFilter('all');
    ui.activeId = note.id;
    ui.preview = false;
    persist();
    renderSidebar(); renderList(); renderEditor();
    showPane('editor');
    $('#titleInput').focus();
  }

  function openNote(id) {
    ui.activeId = id;
    ui.preview = false;
    renderEditor();
    renderList();
    showPane('editor');
    $('#editorScroll').scrollTop = 0;
  }

  function deleteNote(note) {
    const idx = db.notes.findIndex(n => n.id === note.id);
    if (idx < 0) return;
    lastDeleted = { note, idx };
    db.notes.splice(idx, 1);
    if (ui.activeId === note.id) ui.activeId = null;
    persist();
    renderSidebar(); renderList(); renderEditor();
    showPane('list');
    toast('Notiță ștearsă', 'ok', {
      label: 'Anulează',
      fn: () => {
        if (!lastDeleted) return;
        db.notes.splice(lastDeleted.idx, 0, lastDeleted.note);
        ui.activeId = lastDeleted.note.id;
        lastDeleted = null;
        persist(); renderSidebar(); renderList(); renderEditor();
      }
    });
  }

  function setFilter(type, subjectId) {
    ui.filter.type = type;
    ui.filter.subjectId = subjectId || null;
    renderSidebar();
    renderList();
    closeNav();
  }

  function showPane(p) {
    $('#app').dataset.pane = p;
  }

  function openNav() { $('#app').classList.add('nav-open'); $('#scrim').hidden = false; }
  function closeNav() { $('#app').classList.remove('nav-open'); $('#scrim').hidden = true; }

  function applyTheme(theme) {
    db.settings.theme = theme;
    document.documentElement.dataset.theme = theme;
    const dark = theme === 'dark';
    $('#themeLabel').textContent = dark ? 'Mod luminos' : 'Mod întunecat';
    $('#themeBtn .ic use').setAttribute('href', dark ? '#i-sun' : '#i-moon');
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#0B1120' : '#2563EB');
    persist();
  }

  /* ==========================================================
     MODAL MATERIE
     ========================================================== */
  let editingSubject = null;
  let pickedColor = PALETTE[0];

  function buildSwatches() {
    const wrap = $('#swatches');
    wrap.innerHTML = '';
    PALETTE.forEach(c => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'swatch';
      b.style.background = c;
      b.setAttribute('role', 'radio');
      b.setAttribute('aria-checked', String(c === pickedColor));
      b.setAttribute('aria-label', 'Culoare ' + c);
      b.innerHTML = '<svg class="ic"><use href="#i-check"></use></svg>';
      b.addEventListener('click', () => {
        pickedColor = c;
        $$('.swatch', wrap).forEach(x => x.setAttribute('aria-checked', String(x === b)));
      });
      wrap.appendChild(b);
    });
  }

  function openSubjectModal(subject) {
    editingSubject = subject || null;
    pickedColor = subject ? subject.color : PALETTE[db.subjects.length % PALETTE.length];
    $('#subjectModalTitle').textContent = subject ? 'Editează materia' : 'Materie nouă';
    $('#subjName').value = subject ? subject.name : '';
    $('#subjProf').value = subject ? (subject.prof || '') : '';
    $('#subjDelete').hidden = !subject;
    buildSwatches();
    $('#subjectModal').showModal();
    setTimeout(() => $('#subjName').focus(), 60);
  }

  /* ==========================================================
     MARKDOWN TOOLBAR
     ========================================================== */
  function applyMd(kind) {
    const ta = $('#contentInput');
    const note = activeNote();
    if (!note) return;
    const start = ta.selectionStart, end = ta.selectionEnd;
    const val = ta.value;
    const sel = val.slice(start, end);

    const wrap = (pre, post, ph) => {
      const body = sel || ph;
      const next = val.slice(0, start) + pre + body + post + val.slice(end);
      ta.value = next;
      const s = start + pre.length;
      ta.setSelectionRange(s, s + body.length);
    };
    const linePrefix = (prefix) => {
      let ls = val.lastIndexOf('\n', start - 1) + 1;
      let le = val.indexOf('\n', end); if (le === -1) le = val.length;
      const chunk = val.slice(ls, le) || 'text';
      const updated = chunk.split('\n').map((l, i) =>
        typeof prefix === 'function' ? prefix(l, i) : prefix + l).join('\n');
      ta.value = val.slice(0, ls) + updated + val.slice(le);
      ta.setSelectionRange(ls, ls + updated.length);
    };

    switch (kind) {
      case 'b': wrap('**', '**', 'text îngroșat'); break;
      case 'i': wrap('*', '*', 'text înclinat'); break;
      case 'code': sel.includes('\n') ? wrap('```\n', '\n```', 'cod') : wrap('`', '`', 'cod'); break;
      case 'link': wrap('[', '](https://)', 'text link'); break;
      case 'h': linePrefix(l => l.startsWith('#') ? l.replace(/^#+\s*/, '') : '## ' + l); break;
      case 'ul': linePrefix(l => '- ' + l.replace(/^\s*([-*+]|\d+[.)])\s*(\[[ xX]\]\s*)?/, '')); break;
      case 'todo': linePrefix(l => '- [ ] ' + l.replace(/^[-*+]\s*(\[[ xX]\]\s*)?/, '')); break;
      case 'quote': linePrefix(l => '> ' + l.replace(/^>\s*/, '')); break;
    }
    ta.focus();
    note.content = ta.value;
    touch(note);
  }

  /* ==========================================================
     IMPORT / EXPORT
     ========================================================== */
  function exportAll() {
    saveAs('uninotes-backup-' + new Date().toISOString().slice(0, 10) + '.json',
      JSON.stringify(db, null, 2), 'application/json', 'Backup salvat');
  }

  function exportNote(note) {
    const s = subjectOf(note);
    const head = '# ' + (note.title || 'Fără titlu') + '\n\n' +
      (s ? '**Materie:** ' + s.name + (s.prof ? ' — ' + s.prof : '') + '  \n' : '') +
      ((note.tags || []).length ? '**Etichete:** ' + note.tags.map(t => '#' + t).join(', ') + '  \n' : '') +
      '**Modificat:** ' + fmtFull.format(new Date(note.updatedAt)) + '\n\n---\n\n';
    saveAs(slug(note.title) + '.md', head + note.content, 'text/markdown;charset=utf-8', 'Notiță exportată');
  }

  /* stil de sine stătător pentru pagina trimisă la imprimantă */
  const PRINT_CSS = `
    @page { margin: 18mm 16mm; }
    body { font: 11.5pt/1.6 Georgia, 'Times New Roman', serif; color:#000; margin:0; }
    .doc { max-width: 17cm; margin: 0 auto; }
    h1 { font-family: Arial, Helvetica, sans-serif; font-size: 20pt; margin:0 0 4pt; }
    h2 { font-family: Arial, Helvetica, sans-serif; font-size: 14pt; margin:16pt 0 6pt; }
    h3 { font-family: Arial, Helvetica, sans-serif; font-size: 12pt; margin:12pt 0 4pt; }
    .meta { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color:#555;
            border-bottom:1px solid #ccc; padding-bottom:8pt; margin:0 0 14pt; }
    p { margin: 0 0 9pt; }
    ul, ol { margin: 0 0 9pt; padding-left: 18pt; }
    blockquote { margin: 9pt 0; padding-left: 12pt; border-left: 2pt solid #888;
                 color:#333; font-style: italic; }
    code { font-family: Consolas, monospace; font-size: 9.5pt; background:#f2f2f2; padding:1pt 3pt; }
    pre { background:#f6f6f6; border:1px solid #ddd; padding:8pt; overflow:hidden;
          white-space: pre-wrap; page-break-inside: avoid; }
    pre code { background:none; padding:0; }
    table { border-collapse: collapse; width:100%; margin:9pt 0; font-size:10pt;
            font-family: Arial, Helvetica, sans-serif; page-break-inside: avoid; }
    th, td { border:1px solid #999; padding:4pt 7pt; text-align:left; }
    th { background:#eee; }
    hr { border:0; border-top:1px solid #ccc; margin:14pt 0; }
    .task { list-style:none; margin-left:-18pt; }
    .task input { margin-right:6pt; }
    h1, h2, h3 { page-break-after: avoid; }
    a { color:#000; }
  `;

  function printNote() {
    const note = activeNote();
    if (!note) return;

    // WebView2 nu deschide dialogul de printare din JS: pregătim pagina în Python
    // și o deschidem în browserul implicit, unde printarea funcționează normal.
    if (api()) {
      const s = subjectOf(note);
      const bits = [];
      if (s) bits.push(s.name + (s.prof ? ' — ' + s.prof : ''));
      if ((note.tags || []).length) bits.push(note.tags.map(t => '#' + t).join(' '));
      bits.push('modificat ' + fmtFull.format(new Date(note.updatedAt)));
      const head = '<p class="meta">' + escapeHtml(bits.join('  ·  ')) + '</p>';
      api().print_note(escapeHtml(note.title || 'Fără titlu'), head + renderMarkdown(note.content), PRINT_CSS)
        .then(ok => toast(ok ? 'Notița s-a deschis pentru printare' : 'Nu am putut deschide printarea',
                          ok ? 'ok' : 'err'))
        .catch(() => toast('Nu am putut deschide printarea', 'err'));
      return;
    }

    const wasPreview = ui.preview;
    $('#previewPane').innerHTML = renderMarkdown(note.content);
    $('#previewPane').hidden = false;
    setTimeout(() => {
      window.print();
      if (!wasPreview) $('#previewPane').hidden = true;
    }, 60);
  }

  async function importText(text) {
    try {
      const data = JSON.parse(text);
      if (!data || !Array.isArray(data.notes)) throw new Error('format');
      const ok = await confirmDialog(
        'Înlocuiești datele actuale?',
        'Cele ' + db.notes.length + ' notițe existente vor fi înlocuite cu ' + data.notes.length +
        ' notițe din fișier. Recomandat: fă întâi un backup.',
        'Înlocuiește');
      if (!ok) return;
      db = {
        version: 1,
        settings: data.settings || { theme: db.settings.theme },
        subjects: Array.isArray(data.subjects) ? data.subjects : [],
        notes: data.notes
      };
      ui.activeId = null;
      persist();
      applyTheme(db.settings.theme || 'light');
      renderSidebar(); renderList(); renderEditor();
      toast('Import reușit — ' + db.notes.length + ' notițe', 'ok');
    } catch (e) {
      toast('Fișier invalid. Aștept un backup .json UniNotes.', 'err');
    }
  }

  /* ==========================================================
     EVENIMENTE
     ========================================================== */
  function bind() {
    $('#newNoteBtn').addEventListener('click', newNote);
    $('#emptyNewBtn').addEventListener('click', newNote);
    $('#newNoteBtnSm').addEventListener('click', newNote);
    $('#menuBtn').addEventListener('click', openNav);
    $('#sidebarClose').addEventListener('click', closeNav);
    $('#scrim').addEventListener('click', closeNav);
    $('#backBtn').addEventListener('click', () => showPane('list'));

    $$('.nav__item').forEach(b =>
      b.addEventListener('click', () => setFilter(b.dataset.filter)));

    $('#addSubjectBtn').addEventListener('click', () => openSubjectModal(null));

    let searchTimer;
    $('#searchInput').addEventListener('input', e => {
      clearTimeout(searchTimer);
      const v = e.target.value;
      searchTimer = setTimeout(() => { ui.query = v; renderList(); }, 140);
    });

    $('#sortSelect').addEventListener('change', e => { ui.sort = e.target.value; renderList(); });

    // --- editor ---
    $('#titleInput').addEventListener('input', e => {
      const n = activeNote(); if (!n) return;
      n.title = e.target.value;
      touch(n);
    });

    $('#contentInput').addEventListener('input', e => {
      const n = activeNote(); if (!n) return;
      n.content = e.target.value;
      touch(n);
    });

    // continuare automată a listelor la Enter
    $('#contentInput').addEventListener('keydown', e => {
      if (e.key !== 'Enter' || e.shiftKey) return;
      const ta = e.target, pos = ta.selectionStart;
      if (pos !== ta.selectionEnd) return;
      const lineStart = ta.value.lastIndexOf('\n', pos - 1) + 1;
      const line = ta.value.slice(lineStart, pos);
      const m = line.match(/^(\s*)([-*+]\s\[[ xX]\]|[-*+]|\d+[.)])\s+(.*)$/);
      if (!m) return;
      e.preventDefault();
      if (!m[3].trim()) {                       // linie goală → ieșim din listă
        ta.setRangeText('', lineStart, pos, 'end');
      } else {
        let marker = m[2];
        if (/^\d/.test(marker)) marker = (parseInt(marker, 10) + 1) + marker.replace(/^\d+/, '');
        else if (/\[/.test(marker)) marker = marker.replace(/\[[xX]\]/, '[ ]');
        ta.setRangeText('\n' + m[1] + marker + ' ', pos, pos, 'end');
      }
      const n = activeNote(); if (n) { n.content = ta.value; touch(n); }
    });

    $('#subjectSelect').addEventListener('change', e => {
      const n = activeNote(); if (!n) return;
      n.subjectId = e.target.value || null;
      const s = subjectOf(n);
      $('#subjDot').style.background = s ? s.color : 'var(--border-strong)';
      touch(n);
    });

    $('#tagInput').addEventListener('keydown', e => {
      const n = activeNote(); if (!n) return;
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        const v = e.target.value.trim().replace(/^#/, '').toLowerCase();
        if (!v) return;
        n.tags = n.tags || [];
        if (!n.tags.includes(v)) { n.tags.push(v); touch(n); renderTags(n); }
        e.target.value = '';
      } else if (e.key === 'Backspace' && !e.target.value && (n.tags || []).length) {
        n.tags.pop(); touch(n); renderTags(n);
      }
    });

    $('#favBtn').addEventListener('click', () => {
      const n = activeNote(); if (!n) return;
      n.favorite = !n.favorite;
      $('#favBtn').setAttribute('aria-pressed', String(n.favorite));
      touch(n); renderList(); renderSidebar();
    });

    $('#pinBtn').addEventListener('click', () => {
      const n = activeNote(); if (!n) return;
      n.pinned = !n.pinned;
      $('#pinBtn').setAttribute('aria-pressed', String(n.pinned));
      touch(n); renderList();
    });

    $('#previewBtn').addEventListener('click', () => setPreview(!ui.preview));

    $('#previewPane').addEventListener('change', e => {
      const cb = e.target.closest('input[type="checkbox"][data-task]');
      const n = activeNote();
      if (!cb || !n) return;
      // regăsim a N-a bifă din sursă, ignorând ce e în interiorul blocurilor de cod
      const lines = n.content.split('\n');
      const wanted = +cb.dataset.task;
      let seen = 0, inCode = false, i = -1;
      for (let k = 0; k < lines.length; k++) {
        if (/^\s*```/.test(lines[k])) { inCode = !inCode; continue; }
        if (inCode) continue;
        if (/^\s*([-*+]|\d+[.)])\s+\[[ xX]\]/.test(lines[k])) {
          if (seen++ === wanted) { i = k; break; }
        }
      }
      if (i < 0) return;
      lines[i] = cb.checked
        ? lines[i].replace(/\[\s?\]/, '[x]')
        : lines[i].replace(/\[[xX]\]/, '[ ]');
      n.content = lines.join('\n');
      $('#contentInput').value = n.content;
      cb.closest('.task').classList.toggle('done', cb.checked);
      touch(n);
    });

    $('#toolbar').addEventListener('click', e => {
      const b = e.target.closest('.tool');
      if (b) applyMd(b.dataset.md);
    });

    // meniul „mai multe”
    const menu = $('#moreMenu'), moreBtn = $('#moreBtn');
    const closeMenu = () => { menu.hidden = true; moreBtn.setAttribute('aria-expanded', 'false'); };
    moreBtn.addEventListener('click', e => {
      e.stopPropagation();
      menu.hidden = !menu.hidden;
      moreBtn.setAttribute('aria-expanded', String(!menu.hidden));
    });
    document.addEventListener('click', e => { if (!e.target.closest('.menu-wrap')) closeMenu(); });

    menu.addEventListener('click', async e => {
      const b = e.target.closest('button[data-act]');
      if (!b) return;
      closeMenu();
      const n = activeNote(); if (!n) return;
      switch (b.dataset.act) {
        case 'export': exportNote(n); break;
        case 'print': printNote(); break;
        case 'duplicate': {
          const copy = Object.assign({}, n, {
            id: uid(), title: (n.title || 'Fără titlu') + ' (copie)',
            pinned: false, createdAt: now(), updatedAt: now(), tags: (n.tags || []).slice()
          });
          db.notes.unshift(copy);
          ui.activeId = copy.id;
          persist(); renderSidebar(); renderList(); renderEditor();
          toast('Notiță duplicată', 'ok');
          break;
        }
        case 'archive': {
          n.archived = !n.archived;
          n.updatedAt = now();
          persist();
          toast(n.archived ? 'Mutată în arhivă' : 'Scoasă din arhivă', 'ok');
          ui.activeId = null;
          renderSidebar(); renderList(); renderEditor(); showPane('list');
          break;
        }
        case 'delete': {
          const ok = await confirmDialog('Ștergi notița?',
            '„' + (n.title || 'Fără titlu') + '” va fi ștearsă definitiv. Poți anula imediat după.',
            'Șterge');
          if (ok) deleteNote(n);
          break;
        }
      }
    });

    // --- sidebar footer ---
    $('#themeBtn').addEventListener('click', () =>
      applyTheme(db.settings.theme === 'dark' ? 'light' : 'dark'));
    $('#exportAllBtn').addEventListener('click', exportAll);
    $('#importBtn').addEventListener('click', async () => {
      if (api()) {                                    // dialog nativ de deschidere
        const picked = await api().open_file();
        if (picked) importText(picked.content);
        return;
      }
      $('#importInput').click();
    });
    $('#importInput').addEventListener('change', async e => {
      const f = e.target.files[0];
      if (f) importText(await f.text());
      e.target.value = '';
    });
    $('#dataFolderBtn').addEventListener('click', () => {
      if (api()) api().open_data_folder();
    });
    $('#helpBtn').addEventListener('click', () => $('#helpModal').showModal());

    // --- modale ---
    $$('[data-close]').forEach(b =>
      b.addEventListener('click', () => b.closest('dialog').close()));

    $('#subjectForm').addEventListener('submit', () => {
      const name = $('#subjName').value.trim();
      if (!name) return;
      const prof = $('#subjProf').value.trim();
      if (editingSubject) {
        editingSubject.name = name;
        editingSubject.prof = prof;
        editingSubject.color = pickedColor;
        toast('Materie actualizată', 'ok');
      } else {
        const s = { id: uid(), name, prof, color: pickedColor };
        db.subjects.push(s);
        toast('Materie adăugată', 'ok');
      }
      persist();
      renderSidebar(); renderList();
      const n = activeNote(); if (n) renderSubjectSelect(n);
      editingSubject = null;
    });

    $('#subjDelete').addEventListener('click', async () => {
      if (!editingSubject) return;
      const s = editingSubject;
      const used = db.notes.filter(n => n.subjectId === s.id).length;
      const ok = await confirmDialog('Ștergi materia?',
        used ? 'Cele ' + used + ' notițe de la „' + s.name + '” rămân salvate, dar fără materie.'
             : '„' + s.name + '” va fi ștearsă.',
        'Șterge materia');
      if (!ok) return;
      db.subjects = db.subjects.filter(x => x.id !== s.id);
      db.notes.forEach(n => { if (n.subjectId === s.id) n.subjectId = null; });
      if (ui.filter.subjectId === s.id) ui.filter = { type: 'all', subjectId: null, tag: null };
      editingSubject = null;
      $('#subjectModal').close();
      persist(); renderSidebar(); renderList();
      const n = activeNote(); if (n) renderSubjectSelect(n);
      toast('Materie ștearsă', 'ok');
    });

    // --- scurtături ---
    document.addEventListener('keydown', e => {
      const mod = e.ctrlKey || e.metaKey;
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);

      if (mod && e.key.toLowerCase() === 'k') { e.preventDefault(); $('#searchInput').focus(); $('#searchInput').select(); return; }
      if (mod && e.key.toLowerCase() === 'n') { e.preventDefault(); newNote(); return; }
      if (mod && e.key.toLowerCase() === 's') {
        e.preventDefault(); clearTimeout(saveTimer);
        if (persist()) { $('#savedFlag').classList.remove('is-dirty'); $('#savedFlag').textContent = 'Salvat automat'; }
        renderList(); renderSidebar(); toast('Salvat', 'ok'); return;
      }
      if (mod && e.key.toLowerCase() === 'p' && !e.shiftKey) {
        if (!activeNote()) return;
        e.preventDefault(); setPreview(!ui.preview); return;
      }
      if (mod && e.shiftKey && e.key.toLowerCase() === 'p') {
        if (!activeNote()) return;
        e.preventDefault(); $('#pinBtn').click(); return;
      }
      if (mod && e.key.toLowerCase() === 'd') {
        if (!activeNote()) return;
        e.preventDefault(); $('#favBtn').click(); return;
      }
      if (mod && document.activeElement === $('#contentInput')) {
        if (e.key.toLowerCase() === 'b') { e.preventDefault(); applyMd('b'); return; }
        if (e.key.toLowerCase() === 'i') { e.preventDefault(); applyMd('i'); return; }
      }
      if (e.key === 'Escape') {
        if (!$('#moreMenu').hidden) { closeMenu(); return; }
        if ($('#app').classList.contains('nav-open')) { closeNav(); return; }
        if (typing && document.activeElement === $('#searchInput')) {
          $('#searchInput').value = ''; ui.query = ''; renderList(); $('#searchInput').blur();
        }
      }
    });

    // salvăm devreme, nu doar la închidere: fereastra nativă se poate închide
    // înainte ca apelul către Python să apuce să plece
    window.addEventListener('blur', flushSave);
    document.addEventListener('visibilitychange', () => { if (document.hidden) flushSave(); });
    window.addEventListener('beforeunload', flushSave);
  }

  /* ==========================================================
     PORNIRE
     ========================================================== */
  function init() {
    const saved = db.settings.theme;
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(saved || (prefersDark ? 'dark' : 'light'));

    bind();
    renderSidebar();
    renderList();

    const first = visibleNotes()[0];
    if (first && window.innerWidth > 860) { ui.activeId = first.id; }
    renderEditor();
    showPane(ui.activeId && window.innerWidth > 860 ? 'editor' : 'list');

    if (api()) {
      const btn = $('#dataFolderBtn');
      btn.hidden = false;
      Promise.resolve(api().data_folder())
        .then(p => { btn.title = 'Notițele se salvează în:\n' + p; })
        .catch(() => {});
    }
  }

  /* ==========================================================
     INSTALARE PE TELEFON
     ========================================================== */
  const HINT_KEY = 'uninotes.hint-instalare';

  function setupInstall() {
    // service worker: ține aplicația în telefon, ca să meargă și fără internet.
    // În aplicația desktop nu-l vrem — ar servi versiuni vechi după o actualizare.
    if (!DESKTOP && 'serviceWorker' in navigator && location.protocol.startsWith('http')) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js').catch(err =>
          console.warn('[UniNotes] service worker neînregistrat', err));
      });
    }

    const standalone = window.matchMedia('(display-mode: standalone)').matches ||
                       window.navigator.standalone === true;
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    let respins = false;
    try { respins = localStorage.getItem(HINT_KEY) === '1'; } catch (e) { /* mod privat */ }

    if (iOS && !standalone && !DESKTOP && !respins) {
      const hint = $('#installHint');
      hint.hidden = false;
      $('#installHintClose').addEventListener('click', () => {
        hint.hidden = true;
        try { localStorage.setItem(HINT_KEY, '1'); } catch (e) { /* ignorăm */ }
      });
    }
  }

  async function boot() {
    db = await loadData();
    init();
    setupInstall();
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
