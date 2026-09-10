# Wikify

**Trasforma un archivio in una wiki.**

Wikify è un'applicazione locale che prende un archivio documentale disordinato e lo porta
allo stato di **archivio logico**: ogni documento riconducibile a un'entità del dominio,
con una tipologia dichiarata e un livello di riservatezza qualificato. È il presupposto,
oggi quasi sempre mancante, di qualunque sistema di consultazione intelligente.

Tutta l'elaborazione avviene sul computer di chi la esegue: nessun contenuto dell'archivio
lascia la macchina.

> Questo repository contiene la sola applicazione e le guide di installazione. La
> documentazione di analisi e di progetto, il materiale didattico e gli strumenti di
> lavoro restano fuori: non sono necessari per installare né per eseguire Wikify.

---

## Installazione

Requisito unico: **Python 3.9 o superiore**.

| Sistema | Guida |
| --- | --- |
| Mac | [Avvio su Mac](documentazione/07_avvio_mac.md) |
| Windows | [Avvio su Windows](documentazione/08_avvio_windows.md) |
| Linux (Ubuntu e derivate) | [Avvio su Linux](documentazione/10_avvio_linux.md) |

Le guide sono scritte per chi non ha familiarità con il terminale e coprono anche i
problemi frequenti. In forma sintetica, dalla cartella `app`:

```
python3 -m venv .venv
source .venv/bin/activate          # su Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
./avvia.sh                         # su Windows: avvia.bat
```

Il server parte su `http://127.0.0.1:5000` e il browser si apre da solo. Per usare una
porta diversa: `WIKIFY_PORT=5050 ./avvia.sh`.

## Dove risiedono i dati

I dati di lavoro (la base dati con inventario, esiti di scansione, triage, catalogo e
validazioni, la chiave di sessione, i file temporanei di import) risiedono in `dati/`
dentro la cartella di progetto, indicata dalla variabile d'ambiente
`ARCHIVIO_SMART_DATA` e valorizzata dagli script di avvio:

```
dati/lavoro/    i dati prodotti dall'uso reale (nasce al primo avvio)
dati/demo/      la base dati della dimostrazione guidata
```

La cartella `dati/` è esclusa dal repository: la separazione fra codice e dati resta, per
versionamento anziché per collocazione fisica. Per collocare i dati altrove, per esempio
su un disco dedicato, basta valorizzare la variabile prima dell'avvio:

```
ARCHIVIO_SMART_DATA=/srv/wikify/dati ./avvia.sh
```

Il database non va collocato su una condivisione di rete: SQLite non gestisce in modo
affidabile il blocco dei file su montaggi remoti.

## Che cosa contiene l'applicazione

Sette ambiti funzionali, in sequenza di dipendenza:

1. **Inventario e dashboard**: la mappa permanente dell'archivio, mantenuta a livello di
   filesystem e riallineata a ogni apertura. Nessun contenuto viene letto.
2. **Classificazione base**: il dizionario dei pattern con costruzione guidata senza
   espressioni regolari, la scansione deterministica dei contenuti e il triage per file,
   organizzato come coda di lavoro.
3. **Catalogo**: le entità logiche generate da un criterio e l'arricchimento da fonti
   tabellari esterne, con relazione uno-a-molti nativa e provenienza di ogni valore.
4. **Validazione AI**: il perimetro condivisibile, l'import severo delle bozze prodotte
   dall'agente, la coda di revisione ordinata per confidenza crescente, le metriche di
   affidabilità e il connettore MCP che impone il perimetro lato server.
5. **Archivio logico**: il consolidamento che rende il documento un oggetto di prima
   classe: tipologia, aggancio all'entità, riservatezza, e l'export che costituisce la
   consegna verso la fase successiva.
6. **Base deterministica**: le famiglie derivate dall'albero, gli articoli e la relazione
   famiglia/articolo ricavata dal listino, lingua e datazione dei documenti, il controllo
   di vigenza (quali documenti sono superati da note tecniche posteriori).
7. **Consulta**: la wiki. Una scheda per famiglia generata dai dati, con due profili
   (interno e condivisibile) e il corpus markdown pensato per i modelli linguistici.

Il menu dell'applicazione organizza queste funzioni in cinque sezioni per mestiere:
Conoscere, Strutturare, Sorvegliare, Estendere e consegnare, Consultare. A queste si
aggiungono le funzioni di servizio: anagrafica utenti con accesso tramite PIN,
manutenzione e reset dell'archivio.

## Che cosa Wikify non fa (e perché)

Non contiene ricerca semantica, non costruisce un knowledge graph e non integra un motore
agentico proprio. Non è un ritardo, è una decisione:

- un indice semantico costruito su un archivio non classificato indicizzerebbe il
  disordine, e restituirebbe risultati non filtrabili per riservatezza;
- un grafo su entità non ancora consolidate sarebbe da rifare;
- automatizzare la classificazione prima di aver misurato l'accuratezza dell'agente e il
  costo per archivio sarebbe un atto di fede.

Wikify porta l'archivio al punto in cui quei tre passi diventano possibili, e ne consegna
l'esito in un formato dichiarato: `wikify-archivio/1.1`.

---

*Soluzione realizzata a fini didattici e dimostrativi, non candidabile a software di
produzione. Prototipo generato e integrato con il supporto di sistemi AI generativi, sotto
la supervisione e l'architettura tecnica di Carlo Verdini (IT System Integrator & AI
Trainer).*
