# -*- coding: utf-8 -*-
"""
Modulo Dizionario: gestione delle regole di riservatezza con builder
guidato dei pattern (nessuna conoscenza di espressioni regolari richiesta),
prova live, export e import YAML compatibili con lo scanner CLI.
"""

import datetime
import html as html_mod
import json
import re

import yaml
from flask import (Blueprint, Response, flash, jsonify, redirect,
                   render_template, request, url_for)

from core import db

bp = Blueprint("dizionario", __name__)

TIPI = {
    "parola": "Parola o frase esatta",
    "varianti": "Elenco di varianti",
    "etichetta": "Etichetta seguita da valore",
    "codice": "Codice con formato",
    "predefinito": "Modello predefinito",
    "regex": "Espressione regolare (avanzato)",
}

SEVERITA = ["alta", "media", "bassa"]

PREDEFINITI = {
    "ip": ("Indirizzo IP", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "mac": ("Indirizzo MAC", r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
    "email": ("Indirizzo email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "url": ("URL", r"\bhttps?://[^\s<>\"']+"),
}

CLASSI = {"cifre": r"\d", "lettere": "[A-Za-z]", "alfanumerici": "[A-Za-z0-9]"}
CLASSI_LABEL = {"cifre": "cifre", "lettere": "lettere", "alfanumerici": "cifre o lettere"}


# ---------------------------------------------------------------------------
# Costruzione del pattern dai parametri del builder
# ---------------------------------------------------------------------------

def _bordo(testo, inizio=True):
    """Aggiunge \\b solo se il bordo del testo e' un carattere di parola."""
    ch = testo[0] if inizio else testo[-1]
    return r"\b" if (ch.isalnum() or ch == "_") else ""


def _escape_flessibile(testo):
    """Escape della regex, con spazi resi flessibili (uno o piu' spazi).

    Il testo viene spezzato sugli spazi e ogni parte viene escapata da sola:
    cosi' l'escape dello spazio (\\ ) non lascia backslash residui.
    """
    parti = testo.split()
    return r"\s+".join(re.escape(p) for p in parti)


def build_pattern(tipo, p):
    """Costruisce la regex dal tipo e dai parametri del form.

    Restituisce (pattern, None) oppure (None, messaggio_di_errore).
    """
    if tipo == "parola":
        testo = (p.get("testo") or "").strip()
        if not testo:
            return None, "Inserire la parola o frase da cercare."
        pattern = _bordo(testo) + _escape_flessibile(testo) + _bordo(testo, False)

    elif tipo == "varianti":
        righe = [r.strip() for r in (p.get("varianti") or "").splitlines() if r.strip()]
        if not righe:
            return None, "Inserire almeno una variante (una per riga)."
        pattern = r"\b(" + "|".join(_escape_flessibile(r) for r in righe) + r")\b"

    elif tipo == "etichetta":
        etichetta = (p.get("etichetta") or "").strip()
        if not etichetta:
            return None, "Inserire l'etichetta (es. password, cliente, commessa)."
        pattern = _bordo(etichetta) + _escape_flessibile(etichetta) + r"\s*[:=]?\s*\S+"

    elif tipo == "codice":
        prefisso = (p.get("prefisso") or "").strip()
        if not prefisso:
            return None, "Inserire il prefisso fisso del codice (es. C-)."
        try:
            n1 = int(p.get("blocco1_n") or 0)
        except (TypeError, ValueError):
            return None, "La lunghezza del primo blocco deve essere un numero."
        if n1 < 1 or n1 > 30:
            return None, "La lunghezza del primo blocco deve essere tra 1 e 30."
        t1 = p.get("blocco1_tipo") or "cifre"
        pattern = _bordo(prefisso) + re.escape(prefisso) + CLASSI.get(t1, r"\d") + "{%d}" % n1
        n2_grezzo = str(p.get("blocco2_n") or "").strip()
        if n2_grezzo and n2_grezzo != "0":
            try:
                n2 = int(n2_grezzo)
            except ValueError:
                return None, "La lunghezza del secondo blocco deve essere un numero."
            if n2 < 1 or n2 > 30:
                return None, "La lunghezza del secondo blocco deve essere tra 1 e 30."
            separatore = p.get("separatore") or ""
            t2 = p.get("blocco2_tipo") or "cifre"
            pattern += re.escape(separatore) + CLASSI.get(t2, r"\d") + "{%d}" % n2
        pattern += r"\b"

    elif tipo == "predefinito":
        modello = p.get("modello") or ""
        if modello not in PREDEFINITI:
            return None, "Scegliere un modello predefinito dall'elenco."
        pattern = PREDEFINITI[modello][1]

    elif tipo == "regex":
        pattern = (p.get("regex") or "").strip()
        if not pattern:
            return None, "Inserire l'espressione regolare."

    else:
        return None, "Tipo di regola non riconosciuto."

    try:
        re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return None, "Espressione non valida: %s" % e
    return pattern, None


def _parametri_da_form(sorgente, tipo):
    """Estrae dal form (o dal JSON) i soli parametri pertinenti al tipo."""
    chiavi = {
        "parola": ["testo"],
        "varianti": ["varianti"],
        "etichetta": ["etichetta"],
        "codice": ["prefisso", "blocco1_tipo", "blocco1_n",
                   "separatore", "blocco2_tipo", "blocco2_n"],
        "predefinito": ["modello"],
        "regex": ["regex"],
    }.get(tipo, [])
    return {k: (sorgente.get(k) or "") for k in chiavi}


def _evidenzia(testo, rx):
    """Testo di prova con i match avvolti in <mark> (HTML gia' escapato)."""
    parti, pos, n = [], 0, 0
    for m in rx.finditer(testo):
        if m.start() == m.end():
            continue
        parti.append(html_mod.escape(testo[pos:m.start()]))
        parti.append("<mark>" + html_mod.escape(m.group(0)) + "</mark>")
        pos = m.end()
        n += 1
        if n >= 500:
            break
    parti.append(html_mod.escape(testo[pos:]))
    return "".join(parti), n


# ---------------------------------------------------------------------------
# Rotte
# ---------------------------------------------------------------------------

@bp.route("/")
def lista():
    conn = db.get_connection()
    clausole, valori = [], []
    f_categoria = request.args.get("categoria", "")
    f_severita = request.args.get("severita", "")
    f_stato = request.args.get("stato", "")
    f_testo = request.args.get("q", "").strip()
    if f_categoria:
        clausole.append("categoria = ?")
        valori.append(f_categoria)
    if f_severita:
        clausole.append("severita = ?")
        valori.append(f_severita)
    if f_stato == "attive":
        clausole.append("attiva = 1")
    elif f_stato == "disattivate":
        clausole.append("attiva = 0")
    if f_testo:
        clausole.append("(codice LIKE ? OR descrizione LIKE ? OR note LIKE ? OR pattern LIKE ?)")
        valori += ["%" + f_testo + "%"] * 4
    where = (" WHERE " + " AND ".join(clausole)) if clausole else ""
    regole = conn.execute("SELECT * FROM regole" + where + " ORDER BY codice", valori).fetchall()
    categorie = [r["categoria"] for r in
                 conn.execute("SELECT DISTINCT categoria FROM regole ORDER BY categoria")]
    n_attive = conn.execute("SELECT COUNT(*) FROM regole WHERE attiva = 1").fetchone()[0]
    conn.close()
    return render_template("dizionario_lista.html", regole=regole, categorie=categorie,
                           tipi=TIPI, n_attive=n_attive,
                           f_categoria=f_categoria, f_severita=f_severita,
                           f_stato=f_stato, f_testo=f_testo)


def _salva_regola(conn, rid=None):
    """Validazione e salvataggio dal form. Restituisce (ok, messaggio_errore)."""
    codice = (request.form.get("codice") or "").strip()
    if not codice:
        return False, "Il codice della regola è obbligatorio (es. CRED-04)."
    categoria = (request.form.get("categoria_nuova") or "").strip() \
        or (request.form.get("categoria") or "").strip()
    if not categoria:
        return False, "Indicare la categoria (sceglierla dall'elenco o crearne una nuova)."
    severita = request.form.get("severita") or "media"
    if severita not in SEVERITA:
        severita = "media"
    tipo = request.form.get("tipo") or "regex"
    if tipo not in TIPI:
        return False, "Tipo di regola non riconosciuto."
    parametri = _parametri_da_form(request.form, tipo)
    pattern, errore = build_pattern(tipo, parametri)
    if errore:
        return False, errore
    descrizione = (request.form.get("descrizione") or "").strip()
    note = (request.form.get("note") or "").strip()
    attiva = 1 if request.form.get("attiva") else 0
    adesso = datetime.datetime.now().isoformat(timespec="seconds")

    doppione = conn.execute("SELECT id FROM regole WHERE codice = ?", (codice,)).fetchone()
    if doppione and (rid is None or doppione["id"] != rid):
        return False, "Esiste già una regola con codice %s: scegliere un codice diverso." % codice

    if rid is None:
        conn.execute(
            "INSERT INTO regole (codice, categoria, descrizione, tipo, parametri, "
            "pattern, severita, note, attiva, creata, modificata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (codice, categoria, descrizione, tipo, json.dumps(parametri),
             pattern, severita, note, attiva, adesso, adesso))
    else:
        conn.execute(
            "UPDATE regole SET codice = ?, categoria = ?, descrizione = ?, tipo = ?, "
            "parametri = ?, pattern = ?, severita = ?, note = ?, attiva = ?, modificata = ? "
            "WHERE id = ?",
            (codice, categoria, descrizione, tipo, json.dumps(parametri),
             pattern, severita, note, attiva, adesso, rid))
    conn.commit()
    return True, None


@bp.route("/nuova", methods=["GET", "POST"])
def nuova():
    conn = db.get_connection()
    if request.method == "POST":
        ok, errore = _salva_regola(conn)
        if ok:
            conn.close()
            flash("Regola salvata nel dizionario.", "ok")
            return redirect(url_for("dizionario.lista"))
        flash(errore, "errore")
    categorie = [r["categoria"] for r in
                 conn.execute("SELECT DISTINCT categoria FROM regole ORDER BY categoria")]
    conn.close()
    return render_template("dizionario_form.html", regola=None, parametri={},
                           categorie=categorie, tipi=TIPI, severita=SEVERITA,
                           predefiniti=PREDEFINITI, classi=CLASSI_LABEL,
                           form=request.form if request.method == "POST" else None)


@bp.route("/<int:rid>/modifica", methods=["GET", "POST"])
def modifica(rid):
    conn = db.get_connection()
    regola = conn.execute("SELECT * FROM regole WHERE id = ?", (rid,)).fetchone()
    if regola is None:
        conn.close()
        flash("Regola non trovata.", "errore")
        return redirect(url_for("dizionario.lista"))
    if request.method == "POST":
        ok, errore = _salva_regola(conn, rid)
        if ok:
            conn.close()
            flash("Regola aggiornata.", "ok")
            return redirect(url_for("dizionario.lista"))
        flash(errore, "errore")
    try:
        parametri = json.loads(regola["parametri"] or "{}")
    except ValueError:
        parametri = {}
    categorie = [r["categoria"] for r in
                 conn.execute("SELECT DISTINCT categoria FROM regole ORDER BY categoria")]
    conn.close()
    return render_template("dizionario_form.html", regola=regola, parametri=parametri,
                           categorie=categorie, tipi=TIPI, severita=SEVERITA,
                           predefiniti=PREDEFINITI, classi=CLASSI_LABEL,
                           form=request.form if request.method == "POST" else None)


@bp.route("/<int:rid>/toggle", methods=["POST"])
def toggle(rid):
    conn = db.get_connection()
    conn.execute("UPDATE regole SET attiva = 1 - attiva, modificata = ? WHERE id = ?",
                 (datetime.datetime.now().isoformat(timespec="seconds"), rid))
    conn.commit()
    conn.close()
    return redirect(url_for("dizionario.lista", **request.args))


@bp.route("/<int:rid>/elimina", methods=["POST"])
def elimina(rid):
    conn = db.get_connection()
    conn.execute("DELETE FROM regole WHERE id = ?", (rid,))
    conn.commit()
    conn.close()
    flash("Regola eliminata dal dizionario.", "ok")
    return redirect(url_for("dizionario.lista"))


@bp.route("/api/prova", methods=["POST"])
def prova():
    """Prova live: costruisce il pattern e evidenzia i match nel testo di esempio."""
    dati = request.get_json(silent=True) or {}
    tipo = dati.get("tipo") or "regex"
    parametri = _parametri_da_form(dati.get("parametri") or {}, tipo)
    pattern, errore = build_pattern(tipo, parametri)
    if errore:
        return jsonify({"ok": False, "errore": errore})
    testo = dati.get("testo") or ""
    rx = re.compile(pattern, re.IGNORECASE)
    evidenza, n = _evidenzia(testo, rx)
    return jsonify({"ok": True, "pattern": pattern, "n": n, "html": evidenza})


@bp.route("/export.yaml")
def export_yaml():
    """Esporta le regole attive in YAML, compatibile con lo scanner CLI."""
    conn = db.get_connection()
    righe = conn.execute("SELECT * FROM regole WHERE attiva = 1 ORDER BY codice").fetchall()
    conn.close()
    dati = {"regole": [{"id": r["codice"], "categoria": r["categoria"],
                        "descrizione": r["descrizione"] or "",
                        "pattern": r["pattern"], "severita": r["severita"],
                        "note": r["note"] or ""} for r in righe]}
    testo = yaml.safe_dump(dati, allow_unicode=True, sort_keys=False,
                           default_flow_style=False, width=1000)
    intestazione = ("# Dizionario dei pattern di riservatezza, esportato da Wikify\n"
                    "# il %s. Compatibile con scan_riservatezza.py (opzione --dizionario).\n\n"
                    % datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    return Response(intestazione + testo, mimetype="application/x-yaml",
                    headers={"Content-Disposition":
                             "attachment; filename=dizionario_pattern.yaml"})


@bp.route("/importa", methods=["GET", "POST"])
def importa():
    if request.method == "POST":
        f = request.files.get("file_yaml")
        if f is None or not f.filename:
            flash("Selezionare un file YAML da importare.", "errore")
            return redirect(url_for("dizionario.importa"))
        try:
            dati = yaml.safe_load(f.read().decode("utf-8")) or {}
        except Exception as e:
            flash("File YAML non leggibile: %s" % e, "errore")
            return redirect(url_for("dizionario.importa"))
        regole = dati.get("regole")
        if not isinstance(regole, list):
            flash("Il file non contiene la sezione 'regole' attesa.", "errore")
            return redirect(url_for("dizionario.importa"))
        conn = db.get_connection()
        adesso = datetime.datetime.now().isoformat(timespec="seconds")
        nuove = aggiornate = scartate = 0
        for r in regole:
            if not isinstance(r, dict):
                scartate += 1
                continue
            codice = str(r.get("id") or "").strip()
            pattern = str(r.get("pattern") or "")
            if not codice or not pattern:
                scartate += 1
                continue
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error:
                scartate += 1
                continue
            esistente = conn.execute("SELECT id FROM regole WHERE codice = ?",
                                     (codice,)).fetchone()
            if esistente:
                conn.execute(
                    "UPDATE regole SET categoria = ?, descrizione = ?, tipo = 'regex', "
                    "parametri = ?, pattern = ?, severita = ?, note = ?, modificata = ? "
                    "WHERE id = ?",
                    (r.get("categoria", "generale"), r.get("descrizione", "") or "",
                     json.dumps({"regex": pattern}), pattern,
                     r.get("severita", "media"), r.get("note", "") or "",
                     adesso, esistente["id"]))
                aggiornate += 1
            else:
                conn.execute(
                    "INSERT INTO regole (codice, categoria, descrizione, tipo, parametri, "
                    "pattern, severita, note, attiva, creata, modificata) "
                    "VALUES (?, ?, ?, 'regex', ?, ?, ?, ?, 1, ?, ?)",
                    (codice, r.get("categoria", "generale"),
                     r.get("descrizione", "") or "",
                     json.dumps({"regex": pattern}), pattern,
                     r.get("severita", "media"), r.get("note", "") or "",
                     adesso, adesso))
                nuove += 1
        conn.commit()
        conn.close()
        flash("Import completato: %d nuove, %d aggiornate, %d scartate."
              % (nuove, aggiornate, scartate), "ok")
        return redirect(url_for("dizionario.lista"))
    return render_template("dizionario_importa.html")
