# Wikify — avvio passo passo su Windows

*Risponde alla domanda: come si installa e si avvia Wikify su Windows, passo per passo.*

Guida operativa per installare ed eseguire Wikify sul proprio computer. Non
è richiesta alcuna competenza di programmazione: si tratta di copiare
alcuni comandi nel Prompt dei comandi.

Tempo stimato: **15 minuti**, la maggior parte dei quali di attesa durante
l'installazione delle librerie.

> Tutta l'elaborazione avviene sul computer di chi la esegue. Nessun
> documento e nessun contenuto dell'archivio analizzato viene inviato su
> Internet.

---

## 1. Installare o verificare Python

Aprire il **Prompt dei comandi**: tasto Windows, digitare "cmd", Invio.

Copiare e incollare:

```
py --version
```

- Se la risposta è `Python 3.9` o un numero superiore, si può proseguire.
- Se compare un errore oppure si apre il Microsoft Store, scaricare Python
  da <https://www.python.org/downloads/> (pulsante "Download for Windows").
  Durante l'installazione **spuntare la casella "Add python.exe to PATH"**
  nella prima schermata: è il passaggio che viene dimenticato più spesso e
  che causa la maggior parte dei problemi successivi. Al termine chiudere e
  riaprire il Prompt, quindi ripetere il comando.

## 2. Scaricare il progetto

Il progetto viene distribuito dal docente, in una delle due forme seguenti.

**a) Copia ZIP ricevuta dal docente**: prima di estrarla, fare clic destro
sul file → Proprietà → se compare l'avviso "Il file proviene da un altro
computer", selezionare **Annulla blocco**. Estrarre quindi in `Documenti`
e rinominare la cartella `Wikify` se necessario.

**b) Con git**, se si è stati abilitati al repository e `git --version`
risponde correttamente:

```
cd %USERPROFILE%\Documents
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
cd %USERPROFILE%\Documents\Wikify\app
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

Al termine il prompt mostra il prefisso `(.venv)`: è il segno che
l'ambiente è attivo. **Ogni volta** che in futuro si riaprirà il Prompt per
avviare Wikify occorrerà ripetere il comando `.venv\Scripts\activate` dopo
essersi spostati nella cartella `app`.

Se compare il messaggio "l'esecuzione di script è disabilitata", si sta
usando PowerShell anziché il Prompt dei comandi: chiudere e riaprire
usando "cmd", dove il problema non si presenta.

## 4. Avviare l'applicazione

```
avvia.bat
```

Lo script indica la cartella dei dati, avvia il server e apre il browser su
<http://127.0.0.1:5000>.

Alla prima esecuzione Windows Defender può chiedere di autorizzare Python
ad accettare connessioni: è sufficiente consentire l'accesso sulle **reti
private**. Il server ascolta comunque solo sul computer locale.

Per **chiudere** l'applicazione: tornare nella finestra del Prompt e
premere `Ctrl + C`, oppure chiudere la finestra. Finché resta aperta, il
server è in esecuzione.

## 5. Primo utilizzo

1. **Creazione dell'utente**: alla prima apertura viene richiesto di creare
   un profilo con nome e PIN numerico di 4-6 cifre. Il PIN viene salvato
   solo in forma cifrata; va ricordato, perché serve a ogni accesso.
2. **Cartella archivio**: la dashboard chiede il percorso della cartella da
   analizzare. Per ottenerlo comodamente, aprire la cartella in Esplora
   file, fare clic nella barra degli indirizzi e copiare il percorso
   (es. `C:\Users\nome\Documenti\ArchivioProve`), quindi incollarlo nel
   campo. Si imposta una volta sola e resta modificabile.
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
Documenti\
  Wikify\         il programma
  Wikify_dati\    i dati prodotti dal programma
```

La separazione è voluta: consente di aggiornare il programma senza toccare
i dati e di escludere questi ultimi da qualsiasi copia condivisa. Per
azzerare tutto e ricominciare da capo esiste la funzione "Manutenzione" →
"Reset archivio" dentro l'applicazione; in alternativa si può eliminare la
cartella `Wikify_dati`, che verrà ricreata vuota al successivo avvio.

---

## Problemi frequenti

**"py non è riconosciuto come comando interno o esterno"**
Python non è installato oppure, più probabilmente, non è stata spuntata la
casella "Add python.exe to PATH" durante l'installazione. Rieseguire
l'installatore, scegliere "Modify" e attivare quell'opzione; in
alternativa, disinstallare e reinstallare facendo attenzione alla prima
schermata.

**Si apre il Microsoft Store invece di Python**
È l'alias di Windows: tasto Windows → "Gestisci alias di esecuzione app" →
disattivare le voci `python.exe` e `python3.exe`.

**La pagina del browser non si apre, oppure resta bianca**
Aprire manualmente <http://127.0.0.1:5000>. Se non risponde, controllare
che nella finestra del Prompt compaia `Running on http://127.0.0.1:5000` e
che non ci siano messaggi di errore.

**"Address already in use" (porta 5000 occupata)**
Un'altra copia di Wikify è già in esecuzione in un'altra finestra: chiuderla
con `Ctrl + C`. Se il problema persiste, riavviare il computer per liberare
la porta.

**L'installazione delle librerie si interrompe con errori di rete**
Le reti aziendali con proxy possono bloccare il download dei pacchetti. In
tal caso riprovare da una connessione diversa (es. hotspot del telefono).

**L'applicazione non trova la cartella archivio**
Verificare che il percorso sia completo (inizia con `C:\`) e che non
contenga virgolette residue dalla copia. Le cartelle su unità di rete
mappate possono dare problemi: conviene usare una copia locale.
