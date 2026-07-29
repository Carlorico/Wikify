# -*- coding: utf-8 -*-
"""
Modulo Scansione: form di lancio, esecuzione in thread e pagina di
avanzamento con polling JSON.
"""

import os

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)

from core import db
from core import inventario as inv
from core import scansione as motore

bp = Blueprint("scansione", __name__)


@bp.route("/", methods=["GET"])
def nuova():
    conn = db.get_connection()
    n_attive = conn.execute("SELECT COUNT(*) FROM regole WHERE attiva = 1").fetchone()[0]
    # Il percorso viene proposto precompilato con la cartella archivio
    # impostata in dashboard (resta modificabile per la singola scansione).
    percorso = (request.args.get("percorso", "")
                or db.get_impostazione(conn, inv.CHIAVE_RADICE, ""))
    conn.close()
    return render_template("scansione_nuova.html", n_attive=n_attive,
                           percorso=percorso,
                           etichetta="", contesto=80)


@bp.route("/avvia", methods=["POST"])
def avvia():
    percorso = (request.form.get("percorso") or "").strip().strip('"')
    etichetta = (request.form.get("etichetta") or "").strip()
    try:
        contesto = int(request.form.get("contesto") or 80)
    except ValueError:
        contesto = 80
    contesto = max(20, min(contesto, 400))

    percorso = os.path.abspath(os.path.expanduser(percorso)) if percorso else ""
    conn = db.get_connection()
    n_attive = conn.execute("SELECT COUNT(*) FROM regole WHERE attiva = 1").fetchone()[0]
    conn.close()

    errore = None
    if not percorso:
        errore = "Indicare il percorso della cartella da scansionare."
    elif not os.path.isdir(percorso):
        errore = "Cartella non trovata: %s. Verificare il percorso." % percorso
    elif n_attive == 0:
        errore = "Nessuna regola attiva nel dizionario: attivarne almeno una prima di avviare."
    if errore:
        flash(errore, "errore")
        return render_template("scansione_nuova.html", n_attive=n_attive,
                               percorso=request.form.get("percorso", ""),
                               etichetta=etichetta, contesto=contesto)

    scan_id = motore.avvia_scansione(percorso, etichetta, contesto)
    return redirect(url_for("scansione.avanzamento", sid=scan_id))


@bp.route("/avanzamento/<int:sid>")
def avanzamento(sid):
    conn = db.get_connection()
    scan = conn.execute("SELECT * FROM scansioni WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if scan is None:
        flash("Scansione non trovata.", "errore")
        return redirect(url_for("scansione.nuova"))
    return render_template("scansione_avanzamento.html", scan=scan)


@bp.route("/api/stato/<int:sid>")
def stato(sid):
    """Stato di avanzamento per il polling della pagina."""
    info = motore.stato_progress(sid)
    if info is not None:
        risposta = {"id": sid, "stato": info.get("stato", "in corso"),
                    "totali": info.get("totali", 0),
                    "processati": info.get("processati", 0),
                    "corrente": info.get("corrente", ""),
                    "errore": info.get("errore", "")}
        return jsonify(risposta)
    # Nessun avanzamento in memoria (es. server riavviato): si legge il DB.
    conn = db.get_connection()
    scan = conn.execute("SELECT * FROM scansioni WHERE id = ?", (sid,)).fetchone()
    if scan is None:
        conn.close()
        return jsonify({"id": sid, "stato": "inesistente"}), 404
    n_file = conn.execute("SELECT COUNT(*) FROM file_analizzati WHERE scansione_id = ?",
                          (sid,)).fetchone()[0]
    n_non = conn.execute("SELECT COUNT(*) FROM non_analizzati WHERE scansione_id = ?",
                         (sid,)).fetchone()[0]
    conn.close()
    stato_db = scan["stato"]
    if stato_db == "in corso":
        # Il thread non esiste piu': la scansione risulta interrotta.
        stato_db = "interrotta"
    return jsonify({"id": sid, "stato": stato_db,
                    "totali": n_file + n_non, "processati": n_file + n_non,
                    "corrente": "", "errore": ""})
