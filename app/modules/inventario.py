# -*- coding: utf-8 -*-
"""
Modulo Inventario: impostazione della cartella archivio, inventario
iniziale, check di allineamento e integrazione dei file nuovi.

Le viste sono azioni POST richiamate dalla dashboard (che resta la home
dell'app, in app.py); il calcolo vive in core/inventario.py.
"""

import os

from flask import Blueprint, flash, redirect, request, url_for

from core import db
from core import inventario as inv

bp = Blueprint("inventario", __name__)


def _radice_valida(conn):
    """Radice archivio impostata ed esistente, altrimenti None."""
    radice = db.get_impostazione(conn, inv.CHIAVE_RADICE, "")
    if radice and os.path.isdir(radice):
        return radice
    return None


@bp.route("/imposta-radice", methods=["POST"])
def imposta_radice():
    """Salva (o aggiorna) il percorso radice dell'archivio."""
    percorso = (request.form.get("radice") or "").strip().strip('"')
    percorso = os.path.abspath(os.path.expanduser(percorso)) if percorso else ""
    if not percorso:
        flash("Indicare il percorso della cartella archivio.", "errore")
        return redirect(url_for("home"))
    if not os.path.isdir(percorso):
        flash("Cartella non trovata: %s. Verificare il percorso." % percorso,
              "errore")
        return redirect(url_for("home"))
    conn = db.get_connection()
    db.set_impostazione(conn, inv.CHIAVE_RADICE, percorso)
    conn.close()
    flash("Cartella archivio impostata: %s." % percorso, "ok")
    return redirect(url_for("home"))


@bp.route("/iniziale", methods=["POST"])
def iniziale():
    """Esegue l'inventario iniziale (solo metadati, nessuna lettura dei
    contenuti)."""
    conn = db.get_connection()
    radice = _radice_valida(conn)
    if radice is None:
        conn.close()
        flash("Impostare prima la cartella archivio.", "errore")
        return redirect(url_for("home"))
    n = inv.inventario_iniziale(conn, radice)
    conn.close()
    flash("Inventario iniziale completato: %d file mappati." % n, "ok")
    return redirect(url_for("home"))


@bp.route("/ricontrolla", methods=["POST"])
def ricontrolla():
    """Check immediato filesystem / mappa, su richiesta esplicita."""
    conn = db.get_connection()
    radice = _radice_valida(conn)
    if radice is None:
        conn.close()
        flash("Impostare prima la cartella archivio.", "errore")
        return redirect(url_for("home"))
    n_nuovi, n_scomparsi = inv.esegui_check(conn, radice)
    conn.close()
    if n_nuovi or n_scomparsi:
        flash("Check completato: %d file nuovi non mappati, %d scomparsi."
              % (n_nuovi, n_scomparsi), "ok")
    else:
        flash("Check completato: la mappa è allineata al filesystem.", "ok")
    return redirect(url_for("home"))


@bp.route("/integra", methods=["POST"])
def integra():
    """Integra nella mappa i file nuovi rilevati dal check."""
    conn = db.get_connection()
    radice = _radice_valida(conn)
    if radice is None:
        conn.close()
        flash("Impostare prima la cartella archivio.", "errore")
        return redirect(url_for("home"))
    n_nuovi, n_scomparsi = inv.integra_nuovi(conn, radice)
    conn.close()
    if n_nuovi:
        flash("Mappa aggiornata: %d file integrati nell'inventario." % n_nuovi,
              "ok")
    else:
        flash("Nessun file nuovo da integrare: la mappa era già allineata.", "ok")
    return redirect(url_for("home"))
