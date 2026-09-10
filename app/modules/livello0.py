# -*- coding: utf-8 -*-
"""
Modulo Base deterministica (livello 0): ricostruzione della catena, controllo
di vigenza e riconciliazione fra archivio e listino.

La logica di dominio vive in core/livello0.py. Qui stanno solo le pagine, la
raccolta dei parametri e la presentazione delle misure.
"""

import os

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

from core import catalogo as cat
from core import db
from core import inventario as inv
from core import livello0 as l0

bp = Blueprint("livello0", __name__)


def _misure(conn):
    """Le misure correnti, senza ricostruire nulla."""
    return {
        "copertura": l0.misura_copertura(conn),
        "vigenza": l0.misura_vigenza(conn),
        "coerenza": l0.misura_coerenza_date(conn),
        "gruppi_incompleti": l0.gruppi_traduzione_incompleti(conn),
        "senza_lingua": conn.execute(
            "SELECT COUNT(*) FROM documenti WHERE stato = 'attivo' "
            "AND lingua = ''").fetchone()[0],
        "ultimo_listino": conn.execute(
            "SELECT i.nome_file, i.data FROM importazioni i "
            "JOIN tipi_entita t ON t.id = i.tipo_entita_id "
            "WHERE t.nome = ? ORDER BY i.id DESC LIMIT 1",
            (l0.TIPO_ARTICOLO,)).fetchone(),
    }


@bp.route("/", methods=["GET", "POST"])
def ricostruzione():
    """Esegue la catena del livello 0 e mostra le misure che ne derivano."""
    conn = db.get_connection()
    radice = db.get_impostazione(conn, inv.CHIAVE_RADICE, "")
    radice_ok = bool(radice) and os.path.isdir(radice)
    esito = None

    if request.method == "POST":
        if not radice_ok:
            flash("Impostare prima la cartella dell'archivio.", "errore")
        else:
            percorso_listino = None
            caricato = request.files.get("listino")
            if caricato and caricato.filename:
                estensione = os.path.splitext(caricato.filename)[1].lower()
                if estensione not in (".xlsx", ".xlsm"):
                    flash("Il listino va fornito in formato XLSX.", "errore")
                    conn.close()
                    return redirect(url_for("livello0.ricostruzione"))
                cartella = cat.cartella_temporanea()
                percorso_listino = os.path.join(cartella, caricato.filename)
                caricato.save(percorso_listino)
            try:
                esito = l0.ricostruisci(conn, radice, percorso_listino,
                                        utente=session.get("utente_nome", ""))
                flash("Ricostruzione completata.", "ok")
            except Exception as e:      # il messaggio va all'utente, non ai log
                flash("Ricostruzione non riuscita: %s" % e, "errore")
            finally:
                if percorso_listino and os.path.isfile(percorso_listino):
                    os.remove(percorso_listino)

    misure = _misure(conn)
    conn.close()
    return render_template("livello0_ricostruzione.html", radice=radice,
                           radice_ok=radice_ok, esito=esito, **misure)


@bp.route("/riconciliazione")
def riconciliazione():
    """Che cosa non ha trovato riscontro, nelle due direzioni."""
    conn = db.get_connection()
    copertura = l0.misura_copertura(conn)
    anomalie = [dict(r) for r in conn.execute(
        "SELECT a.tipo, a.riferimento, a.dettaglio, i.nome_file "
        "FROM anomalie_import a JOIN importazioni i "
        "ON i.id = a.importazione_id JOIN tipi_entita t "
        "ON t.id = i.tipo_entita_id WHERE t.nome = ? "
        "ORDER BY a.tipo, a.riferimento", (l0.TIPO_ARTICOLO,))]
    senza_entita = [dict(r) for r in conn.execute(
        "SELECT percorso_rel, ruolo_temporale FROM documenti "
        "WHERE stato = 'attivo' AND entita_id IS NULL "
        "ORDER BY percorso_rel")]
    gruppi = l0.gruppi_traduzione_incompleti(conn)
    coerenza = l0.misura_coerenza_date(conn)
    senza_lingua = [dict(r) for r in conn.execute(
        "SELECT percorso_rel FROM documenti WHERE stato = 'attivo' "
        "AND lingua = '' ORDER BY percorso_rel")]
    conn.close()
    return render_template("livello0_riconciliazione.html",
                           copertura=copertura, anomalie=anomalie,
                           senza_entita=senza_entita, gruppi=gruppi,
                           senza_lingua=senza_lingua, coerenza=coerenza)


@bp.route("/vigenza")
def vigenza():
    """Le segnalazioni di vigenza, ordinate per scarto decrescente."""
    conn = db.get_connection()
    misura = l0.misura_vigenza(conn)
    disposte = [dict(r) for r in conn.execute(
        "SELECT s.id, s.stato, s.nota, s.utente, s.data_disposizione, "
        "s.scarto_giorni, s.lingua, e.chiave AS entita, "
        "d.percorso_rel AS documento, c.percorso_rel AS causa "
        "FROM segnalazioni_vigenza s "
        "JOIN documenti d ON d.id = s.documento_id "
        "JOIN documenti c ON c.id = s.causa_documento_id "
        "LEFT JOIN entita e ON e.id = s.entita_id "
        "WHERE s.stato <> 'aperta' ORDER BY s.data_disposizione DESC")]
    conn.close()
    return render_template("livello0_vigenza.html", misura=misura,
                           disposte=disposte)


@bp.route("/vigenza/<int:seg_id>", methods=["POST"])
def disponi(seg_id):
    """Registra la disposizione umana su una segnalazione."""
    stato = request.form.get("stato") or ""
    nota = (request.form.get("nota") or "").strip()
    conn = db.get_connection()
    ok = l0.disponi_segnalazione(conn, seg_id, stato, nota,
                                 session.get("utente_nome", ""))
    conn.close()
    if ok:
        flash("Segnalazione marcata come «%s»." % stato, "ok")
    else:
        flash("Disposizione non riconosciuta.", "errore")
    return redirect(url_for("livello0.vigenza"))
