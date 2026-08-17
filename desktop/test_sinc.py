"""
Verifică sincronizarea automată, în fereastra reală.

Sincronizarea vorbește direct cu GitHub, așa că punem în pagină un GitHub
prefăcut — un gist ținut în memorie — și urmărim cele trei situații care contează:

  • pe cont e ceva nou, aici n-ai scris nimic  → se aduce singur, în tăcere
  • aici ai scris, pe cont n-a scris nimeni    → se trimite singur
  • s-a scris în amândouă părțile              → NU se atinge nimic, te întreabă

A treia e miezul: o sincronizare care ghicește șterge notițe.
"""

import json
import tempfile
import time
from pathlib import Path

import sys

# Consola Windows nu scrie diacritice implicit, iar rezultatul testului
# s-ar pierde tocmai cand ai nevoie de el.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import webview

import main as app

# GitHub prefacut: tine un singur gist in memoria paginii si numara cererile.
GITHUB_FALS = r"""
(function () {
  if (window.__gitfals) return 'deja';
  window.__cereri = [];
  var adevaratul = window.fetch;
  window.fetch = function (adresa, opt) {
    var url = String((adresa && adresa.url) || adresa || '');
    if (url.indexOf('api.github.com/gists') < 0) return adevaratul.apply(this, arguments);
    opt = opt || {};
    window.__cereri.push((opt.method || 'GET') + ' ' + url);

    if ((opt.method || 'GET') === 'GET') {
      var g = localStorage.getItem('__gist_fals');
      if (!g) {
        return Promise.resolve({ok: false, status: 404, json: function () { return Promise.resolve({}); }});
      }
      return Promise.resolve({
        ok: true, status: 200,
        json: function () {
          return Promise.resolve({
            id: 'gistdeproba',
            files: {'uninotes.json': {content: g, truncated: false}}
          });
        }
      });
    }
    // PATCH sau POST: retinem continutul trimis
    var corp = {};
    try { corp = JSON.parse(opt.body || '{}'); } catch (e) {}
    var f = corp.files && corp.files['uninotes.json'];
    if (f) localStorage.setItem('__gist_fals', f.content);
    return Promise.resolve({
      ok: true, status: 200,
      json: function () { return Promise.resolve({id: 'gistdeproba'}); }
    });
  };
  window.__gitfals = true;
  return 'ok';
})()
"""


def pachet(titluri, cand):
    """Un pachet de sincronizare, așa cum îl scrie aplicația."""
    return json.dumps({
        "tip": "uninotes-sync", "versiune": 1, "actualizat": cand,
        "db": {
            "version": 1,
            "settings": {"theme": "dark"},
            "subjects": [],
            "notes": [{"id": "s%d" % i, "title": t, "content": "venit de pe cont",
                       "tags": [], "createdAt": cand, "updatedAt": cand,
                       "subjectId": None, "pinned": False, "favorite": False,
                       "archived": False} for i, t in enumerate(titluri)],
            "orar": {"entries": []}, "termene": [], "repetitii": {}
        },
        "poze": {}
    })


def citeste(v):
    return json.loads(v) if isinstance(v, (str, bytes, bytearray)) else v


def porneste_din_nou(window, secunde=30):
    """
    Reîncarcă pagina și pune GitHub-ul prefăcut înainte să apuce să sincronizeze.

    Semnul după care ne luăm trebuie să fie unul pus de noi, nu un buton din
    pagină: butoanele există și în pagina veche, deci am fi injectat înainte de
    reîncărcare, iar reîncărcarea ar fi șters tot.
    """
    window.evaluate_js("window.__pagina_veche = true; location.reload(); 'ok'")
    for _ in range(int(secunde * 10)):
        time.sleep(0.1)
        try:
            gata = window.evaluate_js(
                "(typeof window.__pagina_veche === 'undefined') && "
                "!!document.querySelector('#newNoteBtn')")
            if gata:
                window.evaluate_js(GITHUB_FALS)
                return True
        except Exception:                                    # noqa: BLE001
            pass
    return False


def titluri(window):
    return citeste(window.evaluate_js(
        "JSON.stringify(Array.prototype.slice.call(document.querySelectorAll('.note-card__title'))"
        ".map(function (t) { return t.textContent.trim(); }))"))


def probe(window):
    out = {}
    try:
        for _ in range(80):
            if window.evaluate_js("!!document.querySelector('#newNoteBtn')"):
                break
            time.sleep(0.5)
        window.evaluate_js(GITHUB_FALS)

        # ---- 0. legarea dintr-un singur pas: cheia, apoi "Gata, leaga-le" ----
        window.evaluate_js("""
            ['uninotes.sync-jeton', 'uninotes.sync-gist', 'uninotes.sync-auto',
             'uninotes.sync-vazut', 'uninotes.sync-schimbat', '__gist_fals']
              .forEach(function (k) { localStorage.removeItem(k); });
            document.querySelector('#syncBtn').click();
            'ok'
        """)
        time.sleep(1.2)
        window.evaluate_js("""
            document.querySelector('#syncToken').value = 'jeton-de-proba';
            document.querySelector('#syncLeaga').click();
            'ok'
        """)
        time.sleep(5)
        out["dintr_un_pas"] = citeste(window.evaluate_js(r"""
            (function () {
              return JSON.stringify({
                gist_salvat: !!localStorage.getItem('uninotes.sync-gist'),
                singura_pornita: !!localStorage.getItem('uninotes.sync-auto'),
                bifa: document.querySelector('#syncAuto').checked,
                are_ceva_pe_cont: !!localStorage.getItem('__gist_fals'),
                stare: (document.querySelector('#syncStare') || {}).textContent || ''
              });
            })()
        """))
        # ---- codul de legatura: o singura lipire pe al doilea dispozitiv ----
        out["cod_facut"] = window.evaluate_js("""
            (function () {
              document.querySelector('#syncCopiazaCod').click();
              return document.querySelector('#syncCod').value ||
                     'copiat in clipboard';
            })()
        """)
        time.sleep(1)

        # Drumul care conteaza e al doilea dispozitiv: un cod facut in alta
        # parte, lipit aici, trebuie sa puna si cheia, si gistul, si sa aduca.
        out["dupa_lipit_cod"] = citeste(window.evaluate_js(r"""
            (function () {
              var cod = 'UNINOTES1:' + btoa('alta-cheie|alt-gist');
              document.querySelector('#syncCod').value = cod;
              document.querySelector('#syncFolosesteCod').click();
              return JSON.stringify({trimis: true});
            })()
        """))
        time.sleep(3)
        out["ce_a_pus_codul"] = citeste(window.evaluate_js(r"""
            (function () {
              return JSON.stringify({
                cheie: localStorage.getItem('uninotes.sync-jeton'),
                gist: localStorage.getItem('uninotes.sync-gist'),
                singura: !!localStorage.getItem('uninotes.sync-auto'),
                campul_golit: document.querySelector('#syncCod').value === ''
              });
            })()
        """))
        # punem la loc legatura de proba, ca sa mearga restul testului
        window.evaluate_js("""
            localStorage.setItem('uninotes.sync-jeton', 'jeton-de-proba');
            localStorage.setItem('uninotes.sync-gist', 'gistdeproba');
            'ok'
        """)

        # un cod stricat nu are voie sa strice legatura de acum
        window.evaluate_js("""
            document.querySelector('#syncCod').value = 'ceva-gresit';
            document.querySelector('#syncFolosesteCod').click();
            'ok'
        """)
        time.sleep(1.5)
        out["cod_stricat"] = citeste(window.evaluate_js(r"""
            (function () {
              return JSON.stringify({
                stare: (document.querySelector('#syncStare') || {}).textContent || '',
                cheia_a_ramas: !!localStorage.getItem('uninotes.sync-jeton')
              });
            })()
        """))

        window.evaluate_js("""
            var b = document.querySelector('#syncModal [data-close]');
            if (b) b.click(); else document.querySelector('#syncModal').close();
            'ok'
        """)
        time.sleep(0.8)

        # ---- 1. pe cont e ceva nou, aici nimic scris → se aduce singur ----
        window.evaluate_js("""
            localStorage.setItem('uninotes.sync-jeton', 'jeton-de-proba');
            localStorage.setItem('uninotes.sync-gist', 'gistdeproba');
            localStorage.setItem('uninotes.sync-auto', '1');
            localStorage.setItem('uninotes.sync-vazut', '1000');
            localStorage.setItem('uninotes.sync-schimbat', '900');
            localStorage.setItem('__gist_fals', %s);
            'ok'
        """ % json.dumps(pachet(["Venita de pe cont", "Si a doua"], 5000)))
        porneste_din_nou(window)
        time.sleep(5)
        out["dupa_aducere_singura"] = titluri(window)
        out["a_retinut_ce_a_adus"] = window.evaluate_js(
            "localStorage.getItem('uninotes.sync-vazut')")

        # ---- 2. scriem aici, pe cont nu s-a schimbat nimic → se trimite singur ----
        window.evaluate_js("""
            window.__cereri = [];
            document.querySelector('#newNoteBtn').click();
            'ok'
        """)
        time.sleep(1.5)
        window.evaluate_js("""
            var ti = document.querySelector('#titleInput');
            ti.value = 'SCRISA AICI';
            ti.dispatchEvent(new Event('input', {bubbles: true}));
            'ok'
        """)
        time.sleep(2)
        out["are_schimbari_netrimise"] = window.evaluate_js(
            "(+localStorage.getItem('uninotes.sync-schimbat')) > "
            "(+localStorage.getItem('uninotes.sync-vazut'))")

        # plecarea din aplicatie trebuie sa trimita ce ai scris
        window.evaluate_js("""
            Object.defineProperty(document, 'hidden', {value: true, configurable: true});
            document.dispatchEvent(new Event('visibilitychange'));
            'ok'
        """)
        time.sleep(6)
        out["a_trimis_singur"] = citeste(window.evaluate_js(r"""
            (function () {
              var b = localStorage.getItem('__gist_fals');
              var g = b ? JSON.parse(b) : null;
              return JSON.stringify({
                cereri: window.__cereri,
                titluri_pe_cont: g ? g.db.notes.map(function (n) { return n.title; }) : null,
                la_zi: (+localStorage.getItem('uninotes.sync-schimbat')) <=
                       (+localStorage.getItem('uninotes.sync-vazut'))
              });
            })()
        """))

        # ---- 3. s-a scris in amandoua partile → nu se atinge nimic ----
        window.evaluate_js("""
            localStorage.setItem('uninotes.sync-vazut', '2000');
            localStorage.setItem('uninotes.sync-schimbat', '9000');
            localStorage.setItem('__gist_fals', %s);
            'ok'
        """ % json.dumps(pachet(["Alta, de pe alt dispozitiv"], 8000)))
        porneste_din_nou(window)
        time.sleep(5)
        out["la_ciocnire"] = citeste(window.evaluate_js(r"""
            (function () {
              return JSON.stringify({
                titluri: Array.prototype.slice.call(document.querySelectorAll('.note-card__title'))
                  .map(function (t) { return t.textContent.trim(); }),
                anunt: Array.prototype.slice.call(document.querySelectorAll('.toast'))
                  .map(function (t) { return t.textContent; }).join(' | '),
                stare: (document.querySelector('#syncStare') || {}).textContent || ''
              });
            })()
        """))

        out["eroare_final"] = window.evaluate_js("window.__eroare || ''")
    except Exception as exc:                                  # noqa: BLE001
        out["exceptie"] = repr(exc)
    finally:
        print("REZULTAT " + json.dumps(out, ensure_ascii=False))
        window.destroy()


def run():
    app.DATA_DIR = Path(tempfile.mkdtemp(prefix="uninotes-sinc-"))
    app.DATA_FILE = app.DATA_DIR / "notite.json"
    api = app.Api()
    window = webview.create_window(
        "UniNotes",
        url="http://127.0.0.1:%d/index.html?desktop=1" % app.start_local_server(),
        js_api=api,
        width=1320,
        height=860,
        background_color="#F5F7FB",
    )
    api._window = window
    webview.start(probe, window, gui="edgechromium", private_mode=False,
                  storage_path=str(app.DATA_DIR / ".fereastra"))


if __name__ == "__main__":
    run()
