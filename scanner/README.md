# Scanner deterministico di riservatezza (Metodo A)

Strumento della Fase 3 dell'assessment (v. `../assessment.md`). Elaborazione interamente locale: nessun contenuto lascia la macchina.

## Contenuto

| File | Ruolo |
|---|---|
| `scan_riservatezza.py` | Scanner: percorre l'archivio, applica i pattern, genera il report XLSX |
| `dizionario_pattern.yaml` | Dizionario dei pattern (13 regole di partenza, 6 categorie), da raffinare col responsabile tecnico |

## Prerequisiti

Python 3.9+ e:

```
pip install pyyaml openpyxl pypdf
```

## Uso

```
python scan_riservatezza.py --root "percorso/archivio" --out report_scansione.xlsx
```

Opzioni: `--dizionario` per un dizionario alternativo, `--contesto` per ampliare il testo di contesto attorno al match (default 80 caratteri).

## Formati gestiti

- **docx, xlsx/xlsm, pdf nativi, txt/csv/md/log/ini/cfg/json/xml**: analizzati
- **PDF scansionati**: marcati "valutare OCR" nel foglio Non analizzati
- **doc/xls/ppt legacy**: marcati "convertire o esaminare manualmente"

## Il report

Fogli: **Segnalazioni** (una riga per match, ordinate per severità, con posizione puntuale ed evidenza), **Riepilogo file**, **Riepilogo categorie**, **Non analizzati**, **Registro segregazione (bozza)** precompilato per il triage (menu a tendina Riservato/Condivisibile/Da valutare), **Parametri scansione**.

## Ciclo di raffinamento del dizionario

1. Prima scansione sul campione → triage del responsabile tecnico sul registro.
2. Falsi positivi ricorrenti → si abbassa la severità o si restringe il pattern.
3. Riservatezze sfuggite (emerse dal triage o, più avanti, dal Metodo B) → nuova regola nel dizionario.
4. Le voci `CLI-01`/`CLI-02` vanno adattate ai nomi cliente e ai formati commessa reali.

A regime lo scanner diventa il presidio di sicurezza della pipeline di ingestione: ogni nuovo documento vi passa prima di raggiungere l'indice accessibile all'AI.
