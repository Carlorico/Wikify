# -*- coding: utf-8 -*-
"""
Modulo Consulta: la wiki delle famiglie (livello 0, fase D).

Le pagine qui presenti non calcolano nulla: leggono cio' che core/wiki.py
ha gia' derivato in modo deterministico dalla base dati. Il profilo di
default sulla scheda HTML e' "interno" (tutto visibile, marcato dove non
pubblico); il corpus e la scheda markdown sono pensati per un consumo
esterno o automatico e nascono a profilo "condivisibile"."""

from flask import Blueprint, Response, abort, render_template, request

from core import db
from core import wiki

bp = Blueprint("consulta", __name__)


def _profilo_richiesto(predefinito):
    profilo = request.args.get("profilo", predefinito)
    return profilo if profilo in wiki.PROFILI else predefinito


@bp.route("/")
def indice():
    """Le famiglie attive come card: chiave, numero di articoli, numero di
    documenti, numero di candidati ad aggiornamento."""
    conn = db.get_connection()
    famiglie = wiki.famiglie_attive(conn)
    conn.close()
    return render_template("consulta_indice.html", famiglie=famiglie)


@bp.route("/famiglia/<int:eid>")
def scheda(eid):
    """La scheda HTML della famiglia. Il profilo di partenza e' interno; il
    link «vista condivisibile» mostra la stessa scheda mascherata."""
    profilo = _profilo_richiesto(wiki.PROFILO_INTERNO)
    conn = db.get_connection()
    dati = wiki.scheda_famiglia(conn, eid, profilo)
    conn.close()
    if dati is None:
        abort(404)
    return render_template("consulta_scheda.html", scheda=dati)


@bp.route("/famiglia/<int:eid>.md")
def scheda_md(eid):
    """La singola scheda in markdown, a profilo condivisibile salvo
    richiesta esplicita di quello interno."""
    profilo = _profilo_richiesto(wiki.PROFILO_CONDIVISIBILE)
    conn = db.get_connection()
    testo = wiki.scheda_markdown(conn, eid, profilo)
    conn.close()
    if testo is None:
        abort(404)
    return Response(testo, mimetype="text/markdown")


@bp.route("/corpus.md")
def corpus():
    """Il corpus intero, a profilo condivisibile: il testo pensato per
    essere dato in pasto a un modello."""
    conn = db.get_connection()
    testo = wiki.corpus_markdown(conn, wiki.PROFILO_CONDIVISIBILE)
    conn.close()
    return Response(testo, mimetype="text/markdown")
