# -*- coding: utf-8 -*-
"""
Estrazione del testo dai file (docx, xlsx, pdf, txt e simili).

Logica ripresa dallo scanner CLI gia' collaudato (scan_riservatezza.py).
Ogni estrattore restituisce una lista di coppie (posizione, testo).
Se il file non e' estraibile viene sollevata ValueError con il motivo
in italiano, che finisce nella tabella dei file non analizzati.
"""

import os
import re
import zipfile
from xml.etree import ElementTree as ET

import openpyxl

try:
    from pypdf import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

TEXT_EXT = {".txt", ".csv", ".md", ".log", ".ini", ".cfg", ".json", ".xml"}
LEGACY_EXT = {".doc", ".xls", ".ppt"}
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def estrai_txt(percorso):
    for codifica in ("utf-8", "latin-1"):
        try:
            with open(percorso, "r", encoding=codifica) as f:
                righe = f.readlines()
            return [("riga %d" % (i + 1), r.rstrip("\n"))
                    for i, r in enumerate(righe) if r.strip()]
        except UnicodeDecodeError:
            continue
    raise ValueError("codifica non riconosciuta")


def estrai_docx(percorso):
    """Estrae i paragrafi da un .docx leggendo direttamente l'XML."""
    out = []
    with zipfile.ZipFile(percorso) as z:
        obiettivi = [n for n in z.namelist()
                     if n == "word/document.xml"
                     or re.match(r"word/(header|footer)\d*\.xml", n)]
        for nome in obiettivi:
            root = ET.fromstring(z.read(nome))
            for i, p in enumerate(root.iter(NS_W + "p")):
                testo = "".join(t.text or "" for t in p.iter(NS_W + "t"))
                if testo.strip():
                    origine = "corpo" if nome == "word/document.xml" else os.path.basename(nome)
                    out.append(("%s, par. %d" % (origine, i + 1), testo))
    return out


def estrai_xlsx(percorso):
    out = []
    wb = openpyxl.load_workbook(percorso, read_only=True, data_only=True)
    for ws in wb.worksheets:
        for riga in ws.iter_rows():
            for cella in riga:
                if cella.value is not None and str(cella.value).strip():
                    out.append(("foglio '%s', cella %s" % (ws.title, cella.coordinate),
                                str(cella.value)))
    wb.close()
    return out


def estrai_pdf(percorso):
    if not HAS_PDF:
        raise ValueError("pypdf non installato (pip install pypdf)")
    reader = PdfReader(percorso)
    out = []
    for i, pagina in enumerate(reader.pages):
        testo = pagina.extract_text() or ""
        for j, riga in enumerate(testo.splitlines()):
            if riga.strip():
                out.append(("pag. %d, riga %d" % (i + 1, j + 1), riga))
    if not out:
        raise ValueError("nessun testo estraibile (possibile PDF scansionato: valutare OCR)")
    return out


def estrai(percorso):
    """Smista il file all'estrattore giusto in base all'estensione."""
    ext = os.path.splitext(percorso)[1].lower()
    if ext in TEXT_EXT:
        return estrai_txt(percorso)
    if ext == ".docx":
        return estrai_docx(percorso)
    if ext in (".xlsx", ".xlsm"):
        return estrai_xlsx(percorso)
    if ext == ".pdf":
        return estrai_pdf(percorso)
    if ext in LEGACY_EXT:
        raise ValueError("formato legacy: convertire in formato recente o esaminare manualmente")
    raise ValueError("formato non gestito dallo scanner")
