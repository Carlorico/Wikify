# Wikify: avvio passo passo su Linux (Ubuntu e derivate)

*Risponde alla domanda: come si installa e si avvia Wikify su una macchina Ubuntu, passo per passo.*

Guida operativa per installare ed eseguire Wikify su Ubuntu o su una
distribuzione derivata (Debian, Linux Mint, Pop!\_OS). I comandi si copiano
nel Terminale.

Tempo stimato: **15 minuti**, la maggior parte dei quali di attesa durante
l'installazione delle librerie.

> Tutta l'elaborazione avviene sulla macchina che la esegue. Nessun
> documento e nessun contenuto dell'archivio analizzato viene inviato su
> Internet.

---

## 1. Verificare la presenza di Python

Aprire il Terminale con `Ctrl + Alt + T` e copiare:

```
python3 --version
```

Serve `Python 3.9` o superiore. Su Ubuntu 20.04 e versioni successive
Python è già presente e la condizione è soddisfatta.

## 2. Installare i due pacchetti di sistema necessari

A differenza di Mac e Windows, su Ubuntu il modulo che crea gli ambienti
virtuali non è incluso nell'installazione di base e va aggiunto:

```
sudo apt update
sudo apt install -y python3-venv python3-pip
```

Il comando chiede la password dell'utente. È l'unico passaggio che
richiede privilegi di amministratore: tutto il resto avviene nella cartella
dell'utente.

## 3. Portare il progetto sulla macchina

**a) Con git**, se la macchina ha accesso a Internet e l'account è stato
abilitato al repository:

```
mkdir -p ~/applicazioni
cd ~/applicazioni
git clone <url del repository> Wikify
```

Se git non è presente: `sudo apt install -y git`.

> Il repository è privato: senza abilitazione nominale non è possibile
> scaricarlo da una pagina pubblica. GitHub non accetta più la password
> dell'account come credenziale da riga di comando: al momento del clone
> va incollato un **token di accesso personale** al posto della password.

**b) Con una copia trasferita a mano**, se la macchina non ha accesso a
Internet: copiare la cartella del progetto (per esempio da chiavetta USB) in
`~/applicazioni/Wikify`.

## 4. Preparare l'ambiente e installare le librerie

Le librerie necessarie sono quattro: Flask (il server web locale), pyyaml,
openpyxl per i file Excel, pypdf per la lettura dei PDF.

```
cd ~/applicazioni/Wikify/app
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Al termine il prompt mostra il prefisso `(.venv)`: è il segno che
l'ambiente virtuale è attivo. **Ogni volta** che si riapre il Terminale per
avviare Wikify occorre ripetere `source .venv/bin/activate` dopo essersi
spostati nella cartella `app`.

Se la macchina non ha accesso a Internet, le librerie vanno portate a mano:
su un computer connesso eseguire `python3 -m pip download -r requirements.txt -d pacchetti`,
copiare la cartella `pacchetti` sulla macchina di destinazione e installare
con `python3 -m pip install --no-index --find-links pacchetti -r requirements.txt`.

## 5. Avviare l'applicazione

```
chmod +x avvia.sh
./avvia.sh
```

Lo script indica la cartella dei dati, avvia il server in ascolto su
<http://127.0.0.1:5000> e prova ad aprire il browser predefinito. Se la
macchina è priva di interfaccia grafica, oppure se il browser non compare,
l'indirizzo va aperto a mano.

Per **chiudere** l'applicazione: tornare nel Terminale e premere
`Ctrl + C`. Finché quella finestra resta aperta, il server è in esecuzione.

Per usare una porta diversa dalla 5000:

```
WIKIFY_PORT=5050 ./avvia.sh
```

## 6. Primo utilizzo

1. **Creazione dell'utente**: alla prima apertura viene richiesto di creare
   un profilo con nome e PIN numerico di 4-6 cifre. Il PIN viene salvato
   solo in forma cifrata; va ricordato, perché serve a ogni accesso.
2. **Cartella archivio**: la dashboard chiede il percorso della cartella da
   analizzare. Per ottenerlo, aprire la cartella nel gestore file e usare
   `Ctrl + L`, che mostra il percorso completo da copiare. In alternativa,
   trascinare la cartella dentro la finestra del Terminale.
3. **Inventario iniziale**: il pulsante in dashboard percorre l'archivio e
   ne costruisce la mappa. Vengono letti soltanto i metadati dei file
   (nome, dimensione, data), mai il contenuto.
4. **Prima scansione**: dalla voce "Classificazione base", poi "Storico",
   poi "Nuova scansione". Qui i contenuti vengono letti, sempre e solo in
   locale, per cercare i pattern del dizionario.
5. **Triage**: nel dettaglio della scansione ogni file va qualificato come
   Riservato, Condivisibile o Da valutare. È il passaggio che stabilisce
   che cosa potrà essere mostrato a un agente AI e che cosa no.

## 7. Dove finiscono i dati

I dati di lavoro (database, chiave di sessione, file temporanei) risiedono
in `dati/lavoro`, **dentro** la cartella del progetto, creata al primo avvio:

```
applicazioni/
  Wikify/
    app/            il programma
    dati/lavoro/    i dati prodotti dal programma
```

I dati stanno dentro il progetto ma fuori dal repository, esclusi tramite
`.gitignore`: si aggiorna il programma con `git pull` senza toccarli, e non
entrano in alcuna copia condivisa. Lo script di avvio stampa il percorso
effettivo a ogni lancio, quindi in caso di dubbio si legge lì.

Per collocare i dati altrove, per esempio su un disco dedicato, basta
valorizzare la variabile prima dell'avvio:

```
ARCHIVIO_SMART_DATA=/srv/wikify/dati ./avvia.sh
```

Per azzerare tutto esiste la funzione "Manutenzione", poi "Reset archivio",
dentro l'applicazione; in alternativa si elimina la cartella `dati/lavoro`,
che viene ricreata vuota al successivo avvio.

## 8. Se l'archivio da analizzare è su una condivisione di rete

Wikify legge l'archivio in sola lettura, quindi una condivisione montata va
bene. Il **database**, invece, non deve stare su una condivisione: SQLite
non gestisce in modo affidabile il blocco dei file su montaggi di rete. Se
il progetto risiede su una condivisione, spostare i dati su disco locale con
la variabile del punto precedente.

Per montare una condivisione Windows:

```
sudo apt install -y cifs-utils
sudo mkdir -p /mnt/archivio
sudo mount -t cifs //server/condivisione /mnt/archivio -o username=NOME,ro
```

L'opzione `ro` monta in sola lettura: è una garanzia in più sul fatto che
l'archivio originale non venga modificato.

---

## Problemi frequenti

**"externally-managed-environment" durante l'installazione**
È il messaggio con cui Ubuntu 23.04 e successive impediscono di installare
librerie nel Python di sistema. Significa che l'ambiente virtuale del punto
4 non era attivo. Verificare la presenza del prefisso `(.venv)` nel prompt
e, se manca, eseguire `source .venv/bin/activate`. Non aggirare il blocco
con `--break-system-packages`: danneggia i pacchetti della distribuzione.

**"No module named venv" oppure "ensurepip is not available"**
Manca il pacchetto del punto 2: `sudo apt install -y python3-venv`.

**"Address already in use" (porta 5000 occupata)**
Un'altra copia di Wikify è già in esecuzione. Individuare il processo con
`ss -ltnp | grep 5000` e chiuderlo, oppure avviare su un'altra porta con
`WIKIFY_PORT=5050 ./avvia.sh`.

**"permission denied: ./avvia.sh"**
Il file non ha il permesso di esecuzione: `chmod +x avvia.sh`.

**"bad interpreter: No such file or directory" all'avvio dello script**
Il file è stato copiato da Windows e conserva i fine riga in formato
Windows. Si corregge con `sudo apt install -y dos2unix` seguito da
`dos2unix avvia.sh`.

**La pagina resta bianca oppure il browser non risponde**
Controllare che nel Terminale compaia `Running on http://127.0.0.1:5000` e
che non ci siano messaggi di errore. L'indirizzo `127.0.0.1` funziona solo
dalla macchina stessa: da un altro computer della rete la pagina non è
raggiungibile, ed è voluto.

**L'applicazione non trova la cartella archivio**
Verificare che il percorso sia completo (inizia con `/home/...` oppure
`/mnt/...`) e che l'utente abbia il permesso di lettura su quella cartella.
Su Linux le maiuscole contano: `Archivio` e `archivio` sono due percorsi
diversi.

**Permessi negati su una cartella montata da rete**
Il montaggio va fatto con un utente che abbia i diritti di lettura sulla
condivisione. Verificare con `ls /mnt/archivio` prima di indicare il
percorso a Wikify.
