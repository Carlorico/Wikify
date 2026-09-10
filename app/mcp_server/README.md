# Server MCP di Wikify

Collega Claude / Claude Code all'app Wikify: espone gli strumenti del ciclo
agentico del modulo Validazione AI (perimetro condivisibile, lettura dei
file, consegna delle bozze, correzioni pregresse, avanzamento della
sessione), rispettando lo stesso vincolo di perimetro imposto dall'app.

Il server e' un processo separato dall'app Flask: usa direttamente i moduli
`core` e la stessa base dati (rispetta la variabile d'ambiente
`ARCHIVIO_SMART_DATA` se impostata), con connessioni SQLite brevi per
convivere con l'app aperta in parallelo.

## Installazione

```
cd mcp_server
python3 -m pip install -r requirements.txt
```

(La dipendenza `mcp`, l'SDK Python ufficiale per il Model Context Protocol,
resta confinata a questa cartella: l'app Flask non la richiede.)

## Strumenti esposti

| Strumento | Funzione | Vincolo |
|---|---|---|
| `ottieni_istruzioni` | Istruzioni per l'agente, formato bozze, tassonomie ammesse e impostazioni di analisi correnti | |
| `ottieni_incarico` | Apre (o recupera) la sessione di analisi e restituisce le cartelle assegnate con i file condivisibili | Solo cartelle con file condivisibili |
| `leggi_file` | Testo estratto di un file, con le posizioni | Rifiuto esplicito se il file non è nel perimetro assegnato alla sessione |
| `consegna_bozza` | Importa una bozza `wikify-bozza/1.0`, legata alla sessione | Stessa validazione severa dell'import manuale |
| `ottieni_correzioni` | Correzioni pregresse (esiti "corretta"/"caso nuovo"), come esempi | |
| `stato_sessione` | Avanzamento della sessione aperta; con `chiudi=true` la chiude | |

## Configurazione per Claude Code

Dal terminale, nella cartella del progetto in cui si vuole usare Wikify:

```
claude mcp add wikify \
  --env ARCHIVIO_SMART_DATA=/percorso/assoluto/Workshop/dati/lavoro \
  -- python3 /percorso/assoluto/Wikify/app/mcp_server/server.py
```

Sostituire i due percorsi con quelli reali sul proprio computer. La
variabile `ARCHIVIO_SMART_DATA` deve indicare la **stessa** cartella dati
usata dall'app (per impostazione predefinita `dati/lavoro`, cartella
sorella di `Wikify`: vedere "Cartella dei dati di lavoro" nel README
dell'app): senza di essa il server lavorerebbe su una base dati diversa,
non vedrebbe il perimetro condivisibile e le bozze consegnate non
comparirebbero nell'applicazione.

Verifica: `claude mcp list` deve mostrare `wikify` come server connesso;
in una sessione Claude Code, chiedere di chiamare lo strumento
`ottieni_istruzioni` per un primo controllo.

## Configurazione per l'app Claude Desktop

Aggiungere una voce nel file di configurazione MCP di Claude Desktop
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wikify": {
      "command": "python3",
      "args": ["/percorso/assoluto/app/mcp_server/server.py"],
      "env": {
        "ARCHIVIO_SMART_DATA": "/percorso/assoluto/Workshop/dati/lavoro"
      }
    }
  }
}
```

La chiave `env` deve indicare la cartella dati dell'app: se viene omessa,
il server ripiega su `app/data` e lavora su una base dati diversa da
quella dell'applicazione. Dopo la modifica, riavviare Claude Desktop.

## Note

- Il server legge e scrive la stessa base dati dell'app Flask (la cartella
  indicata da `ARCHIVIO_SMART_DATA`, in mancanza `app/data`): può restare
  aperto insieme all'app senza conflitti, grazie a connessioni SQLite brevi
  per ogni chiamata.
- L'import manuale dei file bozza dalla pagina "Perimetro e bozze" resta
  invariato: chi non usa Claude non perde nessuna funzionalità.
- Il server non modifica mai i file dell'archivio: `leggi_file` è a sola
  lettura, come le istruzioni per l'agente prescrivono.
