# -*- coding: utf-8 -*-
"""
Modulo Manutenzione: pagina di conferma e azione di reset dell'archivio.

Il reset è protetto da doppia conferma: la parola RESET digitata in un
campo dedicato e il PIN dell'utente connesso (verificato con lo stesso
hash usato per l'accesso). La cancellazione delle righe e il VACUUM
finale vivono in core/manutenzione.py.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core import db
from core import demo
from core import manutenzione as manut
from modules import utenti as utenti_mod

bp = Blueprint("manutenzione", __name__)

PAROLA_CONFERMA = "RESET"


@bp.route("/reset", methods=["GET", "POST"])
def reset():
    """Pagina di conferma del reset (GET) ed esecuzione (POST)."""
    if request.method == "POST":
        conferma = (request.form.get("conferma") or "").strip()
        pin = (request.form.get("pin") or "").strip()
        dopo = (request.form.get("dopo") or "pulita").strip()
        conn = db.get_connection()
        utente = utenti_mod.utente_corrente(conn)
        errore = None
        if conferma != PAROLA_CONFERMA:
            errore = "Parola di conferma non corretta: digitare RESET per procedere."
        elif utente is None or not utenti_mod.verifica_pin(pin, utente["pin"]):
            errore = "PIN non corretto."
        if errore:
            conn.close()
            return render_template("manutenzione_reset.html", errore=errore,
                                   demo_disponibile=demo.disponibile())
        conteggi = manut.reset_archivio(conn)
        # Il reset pulito riporta sempre la modalità demo a "0": una nuova
        # composizione, se richiesta, la rimette a "1" dentro demo.componi.
        db.set_impostazione(conn, demo.CHIAVE_DEMO_ATTIVA, "0")
        conn.close()
        manut.vacuum_db()
        totale = sum(conteggi.values())

        if dopo == "demo" and demo.disponibile():
            conn = db.get_connection()
            demo.componi(conn)
            conn.close()
            flash("Reset dell'archivio completato: %d righe eliminate "
                  "complessivamente. Modalità demo ricomposta." % totale, "ok")
            return redirect(url_for("home", demo="avviata"))

        if dopo == "demo":
            flash("L'Archivio Demo non è disponibile in questa installazione: "
                  "il reset ha prodotto un'istanza pulita.", "errore")
        flash("Reset dell'archivio completato: %d righe eliminate complessivamente."
              % totale, "ok")
        return redirect(url_for("home"))
    return render_template("manutenzione_reset.html", errore=None,
                           demo_disponibile=demo.disponibile())
