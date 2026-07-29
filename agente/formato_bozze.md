# Formato bozze agente — versione 1.0 (congelato il 26/07/2026)

Contratto di scambio tra l'agente di rilevazione (Claude / Claude Code) e il modulo Validazione AI dell'app Wikify. Un file JSON per cartella progetto esaminata. L'app rifiuta all'import ogni proposta priva di evidenza.

## Struttura

```json
{
  "formato": "wikify-bozza/1.0",
  "cartella_progetto": "P-0045_Sonda_TX100",
  "chiave_entita": "P-0045",
  "generato_da": "claude-code",
  "data_generazione": "2026-07-26T15:30:00",
  "perimetro": {
    "file_esaminati": ["manuale_installazione_TX100.docx", "taratura_TX100.xlsx"],
    "file_esclusi_da_perimetro": ["config_avanzata.pdf"]
  },
  "proposte": [
    {
      "file": "manuale_installazione_TX100.docx",
      "sezione": "intero documento",
      "campo": "tipologia",
      "valore_proposto": "manuale_installazione",
      "confidenza": 0.92,
      "evidenza": {
        "posizione": "corpo, par. 1",
        "citazione": "Manuale di installazione Sonda TX100"
      }
    }
  ],
  "note_agente": ["eventuali osservazioni libere, mai obbligatorie"]
}
```

## Regole dei campi

| Campo | Regole |
|---|---|
| `formato` | Fisso `wikify-bozza/1.0`; l'app rifiuta versioni sconosciute |
| `cartella_progetto` | Nome cartella di primo livello, come da inventario |
| `chiave_entita` | Chiave dell'entità Catalogo se definita, altrimenti null |
| `perimetro` | Autodichiarazione dell'agente: cosa ha esaminato e cosa ha saltato perché fuori dal perimetro condivisibile |
| `campo` | Uno di: `tipologia`, `riservatezza`, `versione_ufficiale`, `forma_caratteristiche` |
| `valore_proposto` | Vincolato per campo, v. tassonomie sotto |
| `confidenza` | Decimale 0-1, dichiarata dall'agente; guida l'ordinamento della coda di revisione |
| `evidenza.posizione` | Riferimento puntuale nello stile dello scanner ("corpo, par. 3", "foglio 'Taratura', cella B2", "pag. 2, riga 5") |
| `evidenza.citazione` | Testo letterale dal documento (max 300 caratteri) che giustifica la proposta. **Obbligatoria: senza citazione la proposta viene scartata all'import** |
| `sezione` | "intero documento" oppure il riferimento della porzione (per proposte su parti) |

## Tassonomie dei valori

**`tipologia`** (dalla scheda di rilevazione dell'assessment):
`specifica_tecnica`, `manuale_installazione`, `manuale_manutenzione`, `parametri_interconnessione`, `dati_sperimentazione`, `configurazione`, `disegno_schema`, `corrispondenza`, `altro`

**`riservatezza`**: `condivisibile`, `riservato`, `misto` (con `sezione` valorizzata per indicare dove sta il confine)

**`versione_ufficiale`**: nome del file candidato ufficiale quando esistono versioni multiple; la proposta va sul file candidato, l'evidenza spiega il criterio (data, nome, contenuto)

**`forma_caratteristiche`**: `tabellare`, `prosa`, `mista` (riferita a dove stanno le caratteristiche tecniche chiave)

## Versionamento

Ogni modifica al formato incrementa la versione (`wikify-bozza/1.1`, ...) e va registrata qui con data e motivo. L'app dichiara le versioni che sa importare.
