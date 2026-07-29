# -*- coding: utf-8 -*-
"""
Modulo Utenti: anagrafica (nome + PIN), accesso con sessione Flask,
pagina di benvenuto al primo avvio.

Il PIN (numerico, da 4 a 6 cifre) non viene mai salvato in chiaro:
si memorizza un hash PBKDF2 con sale casuale (solo libreria standard).
"""

import datetime
import hashlib
import hmac
import os
import re
import sqlite3

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

from core import db

bp = Blueprint("utenti", __name__)

PIN_VALIDO = re.compile(r"^\d{4,6}$")

# Endpoint raggiungibili senza login (oltre ai file statici).
ENDPOINT_LIBERI = {"utenti.accesso", "utenti.benvenuto", "utenti.crea_primo"}


# ----------------------------------------------------------------------
# Hash del PIN
# ----------------------------------------------------------------------

def hash_pin(pin, sale=None):
    """Restituisce 'sale$hash' (esadecimale) del PIN con PBKDF2-SHA256."""
    if sale is None:
        sale = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"),
                            bytes.fromhex(sale), 60000).hex()
    return sale + "$" + h


def verifica_pin(pin, memorizzato):
    """Confronta il PIN inserito con l'hash memorizzato."""
    try:
        sale, atteso = (memorizzato or "").split("$", 1)
        calcolato = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"),
                                        bytes.fromhex(sale), 60000).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calcolato, atteso)


# ----------------------------------------------------------------------
# Supporto: utente corrente e controllo di accesso
# ----------------------------------------------------------------------

def utente_corrente(conn):
    """Restituisce la riga dell'utente loggato e attivo, oppure None."""
    uid = session.get("utente_id")
    if not uid:
        return None
    return conn.execute("SELECT * FROM utenti WHERE id = ? AND attivo = 1",
                        (uid,)).fetchone()


def controllo_accesso():
    """Hook before_request: tutte le pagine operative richiedono il login."""
    endpoint = request.endpoint or ""
    if endpoint == "static" or endpoint in ENDPOINT_LIBERI:
        return None
    conn = db.get_connection()
    utente = utente_corrente(conn)
    if utente is not None:
        conn.close()
        return None
    session.pop("utente_id", None)
    session.pop("utente_nome", None)
    n_utenti = conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0]
    conn.close()
    if n_utenti == 0:
        return redirect(url_for("utenti.benvenuto"))
    return redirect(url_for("utenti.accesso"))


# ----------------------------------------------------------------------
# Accesso e uscita
# ----------------------------------------------------------------------

@bp.route("/accesso", methods=["GET", "POST"])
def accesso():
    conn = db.get_connection()
    n_utenti = conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0]
    if n_utenti == 0:
        conn.close()
        return redirect(url_for("utenti.benvenuto"))
    attivi = conn.execute(
        "SELECT id, nome FROM utenti WHERE attivo = 1 ORDER BY nome").fetchall()
    errore = None
    if request.method == "POST":
        uid = request.form.get("utente") or ""
        pin = (request.form.get("pin") or "").strip()
        riga = conn.execute("SELECT * FROM utenti WHERE id = ? AND attivo = 1",
                            (uid,)).fetchone() if uid.isdigit() else None
        if riga is not None and verifica_pin(pin, riga["pin"]):
            conn.close()
            session["utente_id"] = riga["id"]
            session["utente_nome"] = riga["nome"]
            flash("Accesso effettuato: benvenuto, %s." % riga["nome"], "ok")
            return redirect(url_for("home"))
        errore = "Utente o PIN non corretti. Riprovare."
    conn.close()
    return render_template("accesso.html", attivi=attivi, errore=errore)


@bp.route("/uscita")
def uscita():
    session.pop("utente_id", None)
    session.pop("utente_nome", None)
    flash("Sessione chiusa. Arrivederci.", "ok")
    return redirect(url_for("utenti.accesso"))


# ----------------------------------------------------------------------
# Cambio PIN dell'utente connesso
# ----------------------------------------------------------------------

@bp.route("/password", methods=["GET", "POST"])
def password():
    """Cambio del PIN dell'utente connesso: PIN attuale piu' nuovo PIN
    ripetuto due volte, stesse regole dell'anagrafica (4-6 cifre)."""
    if request.method == "POST":
        pin_attuale = (request.form.get("pin_attuale") or "").strip()
        pin_nuovo = (request.form.get("pin_nuovo") or "").strip()
        pin_conferma = (request.form.get("pin_conferma") or "").strip()
        conn = db.get_connection()
        utente = utente_corrente(conn)
        errore = None
        if utente is None:
            errore = "Sessione non valida: ripetere l'accesso."
        elif not verifica_pin(pin_attuale, utente["pin"]):
            errore = "Il PIN attuale non è corretto."
        elif not PIN_VALIDO.match(pin_nuovo):
            errore = "Il nuovo PIN deve essere numerico, da 4 a 6 cifre."
        elif pin_nuovo != pin_conferma:
            errore = "Il nuovo PIN e la conferma non coincidono."
        if errore:
            conn.close()
            return render_template("utenti_password.html", errore=errore)
        conn.execute("UPDATE utenti SET pin = ? WHERE id = ?",
                     (hash_pin(pin_nuovo), utente["id"]))
        conn.commit()
        conn.close()
        flash("PIN aggiornato correttamente.", "ok")
        return redirect(url_for("home"))
    return render_template("utenti_password.html", errore=None)


# ----------------------------------------------------------------------
# Primo avvio: benvenuto e creazione del primo utente
# ----------------------------------------------------------------------

@bp.route("/benvenuto")
def benvenuto():
    conn = db.get_connection()
    n_utenti = conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0]
    conn.close()
    if n_utenti > 0:
        return redirect(url_for("utenti.accesso"))
    return render_template("benvenuto.html", errore=None)


@bp.route("/benvenuto/crea", methods=["POST"])
def crea_primo():
    conn = db.get_connection()
    n_utenti = conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0]
    if n_utenti > 0:
        conn.close()
        return redirect(url_for("utenti.accesso"))
    nome = (request.form.get("nome") or "").strip()
    pin = (request.form.get("pin") or "").strip()
    errore = _valida(nome, pin)
    if errore:
        conn.close()
        return render_template("benvenuto.html", errore=errore)
    adesso = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    cur = conn.execute(
        "INSERT INTO utenti (nome, pin, attivo, data_creazione) VALUES (?, ?, 1, ?)",
        (nome, hash_pin(pin), adesso))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    session["utente_id"] = uid
    session["utente_nome"] = nome
    flash("Primo utente creato: benvenuto, %s." % nome, "ok")
    return redirect(url_for("home"))


# ----------------------------------------------------------------------
# Anagrafica: elenco, creazione, attivazione e disattivazione
# ----------------------------------------------------------------------

def _valida(nome, pin):
    if not nome:
        return "Indicare il nome dell'utente."
    if not PIN_VALIDO.match(pin):
        return "Il PIN deve essere numerico, da 4 a 6 cifre."
    return None


@bp.route("/anagrafica", methods=["GET", "POST"])
def anagrafica():
    conn = db.get_connection()
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        pin = (request.form.get("pin") or "").strip()
        errore = _valida(nome, pin)
        if errore is None:
            adesso = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            try:
                conn.execute(
                    "INSERT INTO utenti (nome, pin, attivo, data_creazione) "
                    "VALUES (?, ?, 1, ?)", (nome, hash_pin(pin), adesso))
                conn.commit()
                flash("Utente creato: %s." % nome, "ok")
            except sqlite3.IntegrityError:
                errore = "Esiste già un utente con questo nome."
        if errore:
            flash(errore, "errore")
        conn.close()
        return redirect(url_for("utenti.anagrafica"))
    elenco = conn.execute(
        "SELECT * FROM utenti ORDER BY attivo DESC, nome").fetchall()
    conn.close()
    return render_template("utenti_anagrafica.html", elenco=elenco)


@bp.route("/anagrafica/<int:uid>/stato", methods=["POST"])
def cambia_stato(uid):
    conn = db.get_connection()
    riga = conn.execute("SELECT * FROM utenti WHERE id = ?", (uid,)).fetchone()
    if riga is None:
        conn.close()
        flash("Utente non trovato.", "errore")
        return redirect(url_for("utenti.anagrafica"))
    if riga["attivo"] and uid == session.get("utente_id"):
        conn.close()
        flash("Non è possibile disattivare l'utente con cui si è connessi.", "errore")
        return redirect(url_for("utenti.anagrafica"))
    nuovo = 0 if riga["attivo"] else 1
    conn.execute("UPDATE utenti SET attivo = ? WHERE id = ?", (nuovo, uid))
    conn.commit()
    conn.close()
    flash("Utente %s %s." % (riga["nome"], "riattivato" if nuovo else "disattivato"), "ok")
    return redirect(url_for("utenti.anagrafica"))
