# Wikify — avvio passo passo su Mac

*Risponde alla domanda: come si installa e si avvia Wikify su un Mac, passo per passo.*

Guida operativa per installare ed eseguire Wikify sul proprio computer. Non
è richiesta alcuna competenza di programmazione: si tratta di copiare
alcuni comandi nel Terminale.

Tempo stimato: **15 minuti**, la maggior parte dei quali di attesa durante
l'installazione delle librerie.

> Tutta l'elaborazione avviene sul computer di chi la esegue. Nessun
> documento e nessun contenuto dell'archivio analizzato viene inviato su
> Internet.

---

## 1. Verificare la presenza di Python

Aprire il **Terminale**: `⌘ + Spazio`, digitare "Terminale", Invio.

Copiare e incollare:

```
python3 --version
```

- Se la risposta è `Python 3.9` o un numero superiore, si può proseguire.
- Se compare un errore o una richiesta di installare gli strumenti per
  sviluppatori, scaricare Python da <https://www.python.org/downloads/>
  (pulsante "Download for macOS"), aprire il file `.pkg` e completare
  l'installazione con le impostazioni predefinite. Chiudere e riaprire il
  Terminale, quindi ripetere il comando.

## 2. Scaricare il progetto

Il progetto viene distribuito dal docente, in una delle due forme seguenti.

**a) Copia ZIP ricevuta dal docente**: estrarre l'archivio ricevuto e
spostare la cartella ottenuta in `Documenti`, rinominandola `Wikify` se
necessario.

**b) Con git**, se si è stati abilitati al repository e `git --version`
risponde correttamente:

```
cd ~/Documents
git clone <url del repository fornito dal docente>
```

> Il repository è privato: senza l'abilitazione nominale o la copia ZIP
> ricevuta dal docente non è possibile scaricare il progetto autonomamente
> da una pagina pubblica.

## 3. Preparare l'ambiente e installare le librerie

Le librerie necessarie sono quattro: Flask (il server web locale), pyyaml,
openpyxl (per i file Excel) e pypdf (per la lettura dei PDF).

Conviene installarle in un **ambiente virtuale**, cioè una cartella isolata
che non interferisce con altri programmi Python già presenti:

```
cd ~/Documents/Wikify/app
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Al termine il prompt del Terminale mostra il prefisso `(.venv)`: è il segno
che l'ambiente è attivo. **Ogni volta** che in futuro si riaprirà il
Terminale per avviare Wikify occorrerà ripetere il comando `source
.venv/bin/activate` dopo essersi spostati nella cartella `app`.

## 4. Avviare l'applicazione

```
./avvia.sh
```

Lo script indica la cartella dei dati, avvia il server e apre il browser su
<http://127.0.0.1:5000>.

Se compare `permission denied`, autorizzare una volta sola l'esecuzione:

```
chmod +x avvia.sh
./avvia.sh
```

Per **chiudere** l'applicazione: tornare nel Terminale e premere
`Control + C`. Finché quella finestra resta aperta, il server è in
esecuzione.

## 5. Primo utilizzo

1. **Creazione dell'utente**: alla prima apertura viene richiesto di creare
   un profilo con nome e PIN numerico di 4-6 cifre. Il PIN viene salvato
   solo in forma cifrata; va ricordato, perché serve a ogni accesso.
2. **Cartella archivio**: la dashboard chiede il percorso della cartella da
   analizzare. Per ottenerlo comodamente, trascinare la cartella dal Finder
   dentro la finestra del Terminale: comparirà il percorso completo, da
   copiare e incollare nel campo. Si imposta una volta sola e resta
   modificabile.
3. **Inventario iniziale**: il pulsante in dashboard percorre l'archivio e
   ne costruisce la mappa. Vengono letti soltanto i metadati dei file
   (nome, dimensione, data), mai il contenuto.
4. **Prima scansione**: dalla voce "Classificazione base" → "Storico" →
   "Nuova scansione". Qui invece i contenuti vengono letti, sempre e solo
   in locale, per cercare i pattern del dizionario.
5. **Triage**: nel dettaglio della scansione ogni file va qualificato come
   Riservato, Condivisibile o Da valutare. È il passaggio che stabilisce
   cosa potrà essere mostrato a un agente AI e cosa no.

## 6. Dove finiscono i dati

I dati di lavoro (database, chiave di sessione, file temporanei) risiedono
in `Wikify_dati`, cartella **sorella** di `Wikify`, creata al primo avvio:

```
Documents/
  Wikify/         il programma
  Wikify_dati/    i dati prodotti dal programma
```

La separazione è voluta: consente di aggiornare il programma senza toccare
i dati e di escludere questi ultimi da qualsiasi copia condivisa. Per
azzerare tutto e ricominciare da capo esiste la funzione "Manutenzione" →
"Reset archivio" dentro l'applicazione; in alternativa si può eliminare la
cartella `Wikify_dati`, che verrà ricreata vuota al successivo avvio.

---

## Problemi frequenti

**"command not found: python3"**
Python non è installato oppure non è raggiungibile: rifare il punto 1
scaricando l'installatore dal sito ufficiale.

**La pagina del browser non si apre, oppure resta bianca**
Aprire manualmente <http://127.0.0.1:5000>. Se non risponde, controllare
che nella finestra del Terminale compaia `Running on http://127.0.0.1:5000`
e che non ci siano messaggi di errore.

**"Address already in use" (porta 5000 occupata)**
Due cause possibili. La prima: un'altra copia di Wikify è già in
esecuzione in un'altra finestra del Terminale — chiuderla con
`Control + C`. La seconda, tipica dei Mac: il **Ricevitore AirPlay**
occupa la porta 5000; si disattiva da Impostazioni di Sistema → Generali →
AirDrop e Handoff → "Ricevitore AirPlay".

**"externally-managed-environment" durante l'installazione**
È il messaggio con cui i Mac recenti impediscono di installare librerie nel
Python di sistema: significa che l'ambiente virtuale del punto 3 non era
attivo. Verificare la presenza del prefisso `(.venv)` nel prompt e, se
manca, eseguire `source .venv/bin/activate`.

**"Impossibile aprire perché proviene da uno sviluppatore non
identificato"**
Riguarda i file scaricati, non i comandi del Terminale. Se compare,
autorizzare da Impostazioni di Sistema → Privacy e sicurezza → "Apri
comunque".

**L'applicazione non trova la cartella archivio**
Verificare che il percorso sia completo (inizia con `/Users/...`) e che non
contenga virgolette residue dal trascinamento. Le cartelle su dischi
esterni o su condivisioni di rete possono richiedere autorizzazioni
aggiuntive in Privacy e sicurezza.
