# -*- coding: utf-8 -*-
"""
Modulo Storico e Consultazione: elenco scansioni, dettaglio con KPI,
consultazione raggruppata per file con coda di lavoro (Da fare /
Verificati), triage per file ed export XLSX.
"""

import datetime
import html as html_mod
import io

from flask import (Blueprint, flash, redirect, render_template, request,
                   send_file, session, url_for)
from markupsafe import Markup

from core import db, report

bp = Blueprint("storico", __name__)

QUALIFICHE = ["Da valutare", "Riservato", "Condivisibile"]
# La qualifica che marca il file come verificato (esce dalla coda "Da fare").
QUALIFICHE_VERIFICATO = {"Riservato", "Condivisibile"}
LIMITE_RIGHE = 1000
STATI_CODA = ("da_fare", "verificati", "tutti")


@bp.route("/")
def lista():
    conn = db.get_connection()
    scansioni = conn.execute(
        "SELECT s.*, "
        " (SELECT COUNT(*) FROM segnalazioni g WHERE g.scansione_id = s.id AND g.severita = 'alta') AS n_alta, "
        " (SELECT COUNT(*) FROM segnalazioni g WHERE g.scansione_id = s.id AND g.severita = 'media') AS n_media, "
        " (SELECT COUNT(*) FROM segnalazioni g WHERE g.scansione_id = s.id AND g.severita = 'bassa') AS n_bassa, "
        " (SELECT COUNT(*) FROM file_analizzati f WHERE f.scansione_id = s.id) AS n_file, "
        " (SELECT COUNT(*) FROM non_analizzati x WHERE x.scansione_id = s.id) AS n_non, "
        " (SELECT COUNT(*) FROM file_analizzati f WHERE f.scansione_id = s.id AND f.totale > 0) AS n_da_triage, "
        " (SELECT COUNT(*) FROM triage_file t WHERE t.scansione_id = s.id AND t.verificato = 1) AS n_verificati "
        "FROM scansioni s ORDER BY s.id DESC").fetchall()
    conn.close()
    return render_template("storico_lista.html", scansioni=scansioni)


def _evidenzia_contesto(contesto, testo_match):
    """Contesto HTML con il testo intercettato avvolto in <mark>."""
    esc = html_mod.escape(contesto or "")
    m = html_mod.escape(testo_match or "")
    if m:
        indice = esc.lower().find(m.lower())
        if indice >= 0:
            esc = (esc[:indice] + "<mark>" + esc[indice:indice + len(m)] +
                   "</mark>" + esc[indice + len(m):])
    return Markup(esc)


@bp.route("/<int:sid>")
def dettaglio(sid):
    conn = db.get_connection()
    scan = conn.execute("SELECT * FROM scansioni WHERE id = ?", (sid,)).fetchone()
    if scan is None:
        conn.close()
        flash("Scansione non trovata.", "errore")
        return redirect(url_for("storico.lista"))

    # KPI di riepilogo
    kpi = {
        "file": conn.execute("SELECT COUNT(*) FROM file_analizzati WHERE scansione_id = ?",
                             (sid,)).fetchone()[0],
        "non": conn.execute("SELECT COUNT(*) FROM non_analizzati WHERE scansione_id = ?",
                            (sid,)).fetchone()[0],
    }
    for sev in ("alta", "media", "bassa"):
        kpi[sev] = conn.execute(
            "SELECT COUNT(*) FROM segnalazioni WHERE scansione_id = ? AND severita = ?",
            (sid, sev)).fetchone()[0]
    kpi["totale"] = kpi["alta"] + kpi["media"] + kpi["bassa"]
    top_categorie = conn.execute(
        "SELECT categoria, COUNT(*) AS n FROM segnalazioni WHERE scansione_id = ? "
        "GROUP BY categoria ORDER BY n DESC LIMIT 5", (sid,)).fetchall()

    # Filtri: severita', categoria, nome file e stato della coda di lavoro
    f_severita = request.args.get("severita", "")
    f_categoria = request.args.get("categoria", "")
    f_file = request.args.get("file", "").strip()
    f_stato = request.args.get("stato", "da_fare")
    if f_stato not in STATI_CODA:
        f_stato = "da_fare"
    clausole, valori = ["scansione_id = ?"], [sid]
    if f_severita:
        clausole.append("severita = ?")
        valori.append(f_severita)
    if f_categoria:
        clausole.append("categoria = ?")
        valori.append(f_categoria)
    if f_file:
        clausole.append("file LIKE ?")
        valori.append("%" + f_file + "%")
    segnalazioni = conn.execute(
        "SELECT * FROM segnalazioni WHERE " + " AND ".join(clausole) +
        " ORDER BY CASE severita WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, file, id"
        " LIMIT %d" % (LIMITE_RIGHE + 1), valori).fetchall()
    troncate = len(segnalazioni) > LIMITE_RIGHE
    segnalazioni = segnalazioni[:LIMITE_RIGHE]

    # Triage per file della scansione
    triage_map = {t["file"]: t for t in conn.execute(
        "SELECT * FROM triage_file WHERE scansione_id = ?", (sid,))}

    # Raggruppamento per file (l'ordine delle segnalazioni e' gia' per
    # severita', quindi i file compaiono a partire dai piu' critici)
    gruppi_file = []
    indice_file = {}
    for s in segnalazioni:
        g = indice_file.get(s["file"])
        if g is None:
            t = triage_map.get(s["file"])
            g = {"file": s["file"],
                 "n_alta": 0, "n_media": 0, "n_bassa": 0, "n_tot": 0,
                 "triage": t,
                 "verificato": bool(t and t["verificato"]),
                 "qualifica": (t["qualifica"] if t else "Da valutare"),
                 "segnalazioni": []}
            indice_file[s["file"]] = g
            gruppi_file.append(g)
        g["n_" + s["severita"]] = g.get("n_" + s["severita"], 0) + 1
        g["n_tot"] += 1
        g["segnalazioni"].append(
            {"s": s, "contesto_html": _evidenzia_contesto(s["contesto"], s["testo_match"])})

    # Conteggi della coda (dopo i filtri, prima del commutatore di stato)
    n_verificati = sum(1 for g in gruppi_file if g["verificato"])
    conteggi = {"tutti": len(gruppi_file), "verificati": n_verificati,
                "da_fare": len(gruppi_file) - n_verificati}
    if f_stato == "da_fare":
        gruppi_file = [g for g in gruppi_file if not g["verificato"]]
    elif f_stato == "verificati":
        gruppi_file = [g for g in gruppi_file if g["verificato"]]
    for i, g in enumerate(gruppi_file, start=1):
        g["anchor"] = "file-%d" % i

    categorie = [r["categoria"] for r in conn.execute(
        "SELECT DISTINCT categoria FROM segnalazioni WHERE scansione_id = ? "
        "ORDER BY categoria", (sid,))]

    file_analizzati = conn.execute(
        "SELECT * FROM file_analizzati WHERE scansione_id = ? ORDER BY totale DESC, file",
        (sid,)).fetchall()
    non_analizzati = conn.execute(
        "SELECT * FROM non_analizzati WHERE scansione_id = ? ORDER BY file",
        (sid,)).fetchall()
    conn.close()
    return render_template("storico_dettaglio.html", scan=scan, kpi=kpi,
                           top_categorie=top_categorie,
                           gruppi_file=gruppi_file, conteggi=conteggi,
                           troncate=troncate, limite=LIMITE_RIGHE,
                           categorie=categorie,
                           file_analizzati=file_analizzati,
                           non_analizzati=non_analizzati,
                           qualifiche=QUALIFICHE,
                           f_severita=f_severita, f_categoria=f_categoria,
                           f_file=f_file, f_stato=f_stato)


@bp.route("/<int:sid>/triage", methods=["POST"])
def triage(sid):
    """Assegna o aggiorna la qualifica di un file (triage per file).

    Il validatore e la data di validazione vengono assegnati
    automaticamente dall'utente connesso. Le qualifiche Riservato e
    Condivisibile marcano il file come verificato (esce dalla coda);
    Da valutare lo riporta in coda.
    """
    file_ = request.form.get("file") or ""
    qualifica = request.form.get("qualifica") or "Da valutare"
    if qualifica not in QUALIFICHE:
        qualifica = "Da valutare"
    motivazione = (request.form.get("motivazione") or "").strip()
    vincolo = (request.form.get("vincolo") or "").strip()
    validatore = session.get("utente_nome", "")
    verificato = 1 if qualifica in QUALIFICHE_VERIFICATO else 0
    if not file_:
        flash("Richiesta di triage non valida.", "errore")
        return redirect(url_for("storico.dettaglio", sid=sid))
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO triage_file (scansione_id, file, qualifica, motivazione, "
        "vincolo, validatore, data, verificato) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(scansione_id, file) DO UPDATE SET "
        "qualifica = excluded.qualifica, motivazione = excluded.motivazione, "
        "vincolo = excluded.vincolo, validatore = excluded.validatore, "
        "data = excluded.data, verificato = excluded.verificato",
        (sid, file_, qualifica, motivazione, vincolo, validatore,
         datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), verificato))
    conn.commit()
    conn.close()
    if verificato:
        flash("File verificato come %s: %s." % (qualifica, file_), "ok")
    else:
        flash("File riportato in coda (Da valutare): %s." % file_, "ok")
    # Si torna alla consultazione conservando i filtri correnti.
    parametri = {"sid": sid}
    for campo in ("severita", "categoria", "file_filtro", "stato"):
        valore = (request.form.get("filtro_" + campo) or "").strip()
        if valore:
            parametri["file" if campo == "file_filtro" else campo] = valore
    return redirect(url_for("storico.dettaglio", **parametri))


@bp.route("/<int:sid>/elimina", methods=["POST"])
def elimina(sid):
    conn = db.get_connection()
    conn.execute("DELETE FROM scansioni WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
    flash("Scansione eliminata dallo storico (segnalazioni e triage compresi).", "ok")
    return redirect(url_for("storico.lista"))


@bp.route("/<int:sid>/export.xlsx")
def export_xlsx(sid):
    conn = db.get_connection()
    scan = conn.execute("SELECT * FROM scansioni WHERE id = ?", (sid,)).fetchone()
    if scan is None:
        conn.close()
        flash("Scansione non trovata.", "errore")
        return redirect(url_for("storico.lista"))
    wb = report.genera_report(conn, scan)
    conn.close()
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nome = "report_scansione_%d_%s.xlsx" % (
        sid, datetime.date.today().strftime("%Y%m%d"))
    return send_file(buf, as_attachment=True, download_name=nome,
                     mimetype="application/vnd.openxmlformats-officedocument"
                              ".spreadsheetml.sheet")
