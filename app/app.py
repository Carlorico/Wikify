#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archivio Smart: applicazione web locale per l'assessment di riservatezza
di un archivio documentale.

Avvio:  python app.py
Il server ascolta su http://127.0.0.1:5000 e il browser si apre da solo.
Tutta l'elaborazione avviene in locale: nessun contenuto lascia il computer.
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

# Consente l'avvio con "python app.py" da qualunque cartella corrente.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, redirect, render_template, url_for  # noqa: E402

from core import db  # noqa: E402
from core import inventario as inv  # noqa: E402
from modules.archivio import bp as archivio_bp  # noqa: E402
from modules.catalogo import bp as catalogo_bp  # noqa: E402
from modules.dizionario import bp as dizionario_bp  # noqa: E402
from modules.inventario import bp as inventario_bp  # noqa: E402
from modules.manutenzione import bp as manutenzione_bp  # noqa: E402
from modules.scansione import bp as scansione_bp  # noqa: E402
from modules.storico import bp as storico_bp  # noqa: E402
from modules.validazione import bp as validazione_bp  # noqa: E402
from modules import utenti as utenti_mod  # noqa: E402


def create_app():
    app = Flask(__name__)
    db.init_db()
    # Chiave di sessione persistente, generata al primo avvio in data/.
    app.secret_key = db.get_secret_key()

    app.register_blueprint(archivio_bp, url_prefix="/archivio")
    app.register_blueprint(catalogo_bp, url_prefix="/catalogo")
    app.register_blueprint(dizionario_bp, url_prefix="/dizionario")
    app.register_blueprint(inventario_bp, url_prefix="/inventario")
    app.register_blueprint(manutenzione_bp, url_prefix="/manutenzione")
    app.register_blueprint(scansione_bp, url_prefix="/scansione")
    app.register_blueprint(storico_bp, url_prefix="/storico")
    app.register_blueprint(validazione_bp, url_prefix="/validazione")
    app.register_blueprint(utenti_mod.bp, url_prefix="/utenti")

    # Tutte le pagine operative richiedono un utente connesso.
    app.before_request(utenti_mod.controllo_accesso)

    # ------------------------------------------------------------------
    # PER AGGIUNGERE UN NUOVO MODULO (es. inventario, verifica XLS,
    # validazione):
    #   1. creare modules/nomemodulo.py con un Blueprint chiamato "bp"
    #      (vedere modules/storico.py come esempio di struttura);
    #   2. importarlo qui:   from modules.nomemodulo import bp as nome_bp
    #   3. registrarlo:      app.register_blueprint(nome_bp, url_prefix="/nomemodulo")
    #   4. se servono nuove tabelle, accodare uno script alla lista
    #      MIGRAZIONI in core/db.py (verra' applicato al prossimo avvio);
    #   5. aggiungere la voce nel menu di templates/base.html.
    # ------------------------------------------------------------------

    @app.route("/")
    def home():
        """Dashboard: home dell'app con i KPI dell'inventario permanente."""
        conn = db.get_connection()
        radice = db.get_impostazione(conn, inv.CHIAVE_RADICE, "")
        radice_ok = bool(radice) and os.path.isdir(radice)
        n_mappa = conn.execute(
            "SELECT COUNT(*) FROM inventario_file").fetchone()[0]

        n_nuovi = 0
        n_scomparsi = 0
        n_da_classificare = 0
        kpi = None
        ultima_esecuzione = None
        if radice_ok and n_mappa > 0:
            # Check all'apertura, al massimo una volta ogni 10 minuti.
            n_nuovi = inv.check_se_necessario(conn, radice)
            kpi = inv.kpi_dashboard(conn)
            n_da_classificare = len(inv.da_classificare(conn, radice))
            n_scomparsi = conn.execute(
                "SELECT COUNT(*) FROM inventario_file WHERE stato = 'scomparso'"
            ).fetchone()[0]
            ultima_esecuzione = conn.execute(
                "SELECT * FROM inventario_esecuzioni ORDER BY id DESC LIMIT 1"
            ).fetchone()
        conn.close()
        return render_template(
            "home.html", radice=radice, radice_ok=radice_ok, n_mappa=n_mappa,
            n_nuovi=n_nuovi, n_scomparsi=n_scomparsi,
            n_da_classificare=n_da_classificare, kpi=kpi,
            ultima_esecuzione=ultima_esecuzione)

    return app


def _apri_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    app = create_app()
    threading.Timer(1.2, _apri_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
