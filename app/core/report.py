# -*- coding: utf-8 -*-
"""
Generazione del report XLSX di una scansione, con lo stesso stile del
report dello scanner CLI (scan_riservatezza.py).

Fogli: Segnalazioni, Riepilogo file, Riepilogo categorie, Non analizzati,
Registro segregazione (con le qualifiche del triage per file),
Parametri scansione.

Tutti i valori scritti nelle celle passano da sanifica_cella(): i testi
estratti dai documenti possono contenere caratteri di controllo che
openpyxl rifiuta (IllegalCharacterError), superare il limite di 32767
caratteri per cella o iniziare per "=" (che openpyxl tratterebbe come
formula). La sanificazione rende l'export robusto in tutti questi casi.
"""

import datetime
import re

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

SEV_ORDER = {"alta": 0, "media": 1, "bassa": 2}
SEV_FILL = {
    "alta": PatternFill("solid", start_color="F4CCCC"),
    "media": PatternFill("solid", start_color="FCE5CD"),
    "bassa": PatternFill("solid", start_color="FFF2CC"),
}

# Limite di Excel per il contenuto di una singola cella.
MAX_CELLA = 32767
_SUFFISSO_TRONCA = " [troncato]"

# Caratteri non ammessi da openpyxl nelle celle: caratteri di controllo
# C0 (tranne tab, LF, CR), DEL, C1 e surrogati isolati.
_ILLEGALI = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]")


def sanifica_cella(valore):
    """Rende un valore sicuro per una cella openpyxl.

    - None diventa stringa vuota;
    - numeri e booleani passano invariati;
    - nei testi i caratteri di controllo vengono sostituiti con uno spazio;
    - i testi che iniziano per "=" vengono preceduti da un apostrofo,
      cosi' non vengono interpretati come formula;
    - i testi oltre 32767 caratteri vengono troncati con indicazione.
    """
    if valore is None:
        return ""
    if isinstance(valore, (int, float, bool)):
        return valore
    testo = str(valore)
    testo = _ILLEGALI.sub(" ", testo)
    if testo.startswith("="):
        testo = "'" + testo
    if len(testo) > MAX_CELLA:
        testo = testo[:MAX_CELLA - len(_SUFFISSO_TRONCA)] + _SUFFISSO_TRONCA
    return testo


def _append(ws, valori):
    """Accoda una riga al foglio sanificando ogni cella."""
    ws.append([sanifica_cella(v) for v in valori])


def _larghezze(ws, widths):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def genera_report(conn, scansione):
    """Costruisce e restituisce il Workbook openpyxl del report."""
    sid = scansione["id"]
    bold = Font(bold=True)
    wb = openpyxl.Workbook()

    segnalazioni = conn.execute(
        "SELECT * FROM segnalazioni WHERE scansione_id = ?", (sid,)).fetchall()
    ordinate = sorted(segnalazioni,
                      key=lambda s: (SEV_ORDER.get(s["severita"], 9), s["file"]))
    files = conn.execute(
        "SELECT * FROM file_analizzati WHERE scansione_id = ? ORDER BY totale DESC",
        (sid,)).fetchall()
    non_analizzati = conn.execute(
        "SELECT * FROM non_analizzati WHERE scansione_id = ? ORDER BY file",
        (sid,)).fetchall()

    # --- Segnalazioni ---
    ws = wb.active
    ws.title = "Segnalazioni"
    _append(ws, ["File", "Posizione", "Regola", "Categoria", "Severità",
                 "Testo intercettato", "Contesto"])
    for c in ws[1]:
        c.font = bold
    for s in ordinate:
        _append(ws, [s["file"], s["posizione"], s["regola_id"], s["categoria"],
                     s["severita"], s["testo_match"], s["contesto"]])
        ws.cell(row=ws.max_row, column=5).fill = SEV_FILL.get(s["severita"], PatternFill())
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _larghezze(ws, {"A": 55, "B": 22, "C": 9, "D": 18, "E": 9, "F": 30, "G": 70})

    # --- Riepilogo file ---
    ws = wb.create_sheet("Riepilogo file")
    _append(ws, ["File", "Formato", "Unità di testo", "Segnalazioni",
                 "Alta", "Media", "Bassa", "Esito"])
    for c in ws[1]:
        c.font = bold
    for f in files:
        _append(ws, [f["file"], f["formato"], f["unita_testo"], f["totale"],
                     f["n_alta"], f["n_media"], f["n_bassa"],
                     "DA TRIAGE" if f["totale"] else "nessun pattern (campionare a controllo)"])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _larghezze(ws, {"A": 55, "B": 9, "C": 13, "D": 13, "E": 7, "F": 7, "G": 7, "H": 34})

    # --- Riepilogo categorie ---
    ws = wb.create_sheet("Riepilogo categorie")
    _append(ws, ["Categoria", "Regole attive", "Segnalazioni", "File coinvolti"])
    for c in ws[1]:
        c.font = bold
    categorie = {}
    for r in conn.execute("SELECT categoria, COUNT(*) AS n FROM regole "
                          "WHERE attiva = 1 GROUP BY categoria"):
        categorie[r["categoria"]] = {"regole": r["n"], "n": 0, "files": set()}
    for s in segnalazioni:
        d = categorie.setdefault(s["categoria"], {"regole": 0, "n": 0, "files": set()})
        d["n"] += 1
        d["files"].add(s["file"])
    for cat, d in sorted(categorie.items(), key=lambda kv: -kv[1]["n"]):
        _append(ws, [cat, d["regole"], d["n"], len(d["files"])])
    _larghezze(ws, {"A": 24, "B": 13, "C": 13, "D": 14})

    # --- Non analizzati ---
    ws = wb.create_sheet("Non analizzati")
    _append(ws, ["File", "Motivo"])
    for c in ws[1]:
        c.font = bold
    for f in non_analizzati:
        _append(ws, [f["file"], f["motivo"]])
    _larghezze(ws, {"A": 55, "B": 60})

    # --- Registro segregazione (triage per file) ---
    ws = wb.create_sheet("Registro segregazione")
    _append(ws, ["File", "Segnalazioni", "Alta", "Media", "Bassa",
                 "Qualifica", "Motivazione", "Vincolo",
                 "Validatore", "Data validazione", "Stato"])
    for c in ws[1]:
        c.font = bold
    gruppi = conn.execute(
        "SELECT f.file, f.totale, f.n_alta, f.n_media, f.n_bassa, "
        "       t.qualifica, t.motivazione, t.vincolo, t.validatore, "
        "       t.data AS data_triage, t.verificato "
        "FROM file_analizzati f "
        "LEFT JOIN triage_file t ON t.scansione_id = f.scansione_id "
        "     AND t.file = f.file "
        "WHERE f.scansione_id = ? AND f.totale > 0 "
        "ORDER BY CASE WHEN t.verificato = 1 THEN 1 ELSE 0 END, "
        "         f.n_alta DESC, f.n_media DESC, f.file",
        (sid,)).fetchall()
    for g in gruppi:
        _append(ws, [g["file"], g["totale"], g["n_alta"], g["n_media"], g["n_bassa"],
                     g["qualifica"] or "Da valutare",
                     g["motivazione"] or "", g["vincolo"] or "",
                     g["validatore"] or "", g["data_triage"] or "",
                     "Verificato" if g["verificato"] else "Da fare"])
        sev = "alta" if g["n_alta"] else ("media" if g["n_media"] else "bassa")
        ws.cell(row=ws.max_row, column=1).fill = SEV_FILL.get(sev, PatternFill())
    # La convalida a elenco viene aggiunta solo se esistono righe di dati:
    # una DataValidation su intervallo vuoto produce file XLSX anomali.
    if ws.max_row > 1:
        dv = DataValidation(type="list",
                            formula1='"Riservato,Condivisibile,Da valutare"',
                            allow_blank=True)
        ws.add_data_validation(dv)
        dv.add("F2:F%d" % ws.max_row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _larghezze(ws, {"A": 55, "B": 12, "C": 7, "D": 7, "E": 7, "F": 15,
                    "G": 55, "H": 40, "I": 16, "J": 18, "K": 12})

    # --- Parametri scansione ---
    ws = wb.create_sheet("Parametri scansione")
    n_sev = {"alta": 0, "media": 0, "bassa": 0}
    for s in segnalazioni:
        n_sev[s["severita"]] = n_sev.get(s["severita"], 0) + 1
    for k, v in [
        ("Radice scansionata", scansione["radice"]),
        ("Etichetta", scansione["etichetta"] or ""),
        ("Data e ora", scansione["data"]),
        ("Stato", scansione["stato"]),
        ("Durata (secondi)", scansione["durata"] if scansione["durata"] is not None else ""),
        ("Regole applicate", scansione["n_regole"]),
        ("Caratteri di contesto", scansione["contesto"]),
        ("File analizzati", len(files)),
        ("File non analizzati", len(non_analizzati)),
        ("Segnalazioni totali", len(segnalazioni)),
        ("Severità alta", n_sev["alta"]),
        ("Severità media", n_sev["media"]),
        ("Severità bassa", n_sev["bassa"]),
        ("Report generato il", datetime.datetime.now().strftime("%d/%m/%Y %H:%M")),
        ("Nota", "Elaborazione interamente locale. Nessun contenuto trasmesso all'esterno."),
    ]:
        _append(ws, [k, v])
        ws.cell(row=ws.max_row, column=1).font = bold
    _larghezze(ws, {"A": 24, "B": 80})

    return wb
