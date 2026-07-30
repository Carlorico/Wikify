# Wikify

**Trasforma un archivio in una wiki.**

Wikify è un'applicazione locale che prende un archivio documentale disordinato e lo porta
allo stato di **archivio logico**: ogni documento riconducibile a un'entità del dominio,
con una tipologia dichiarata e un livello di riservatezza qualificato. È il presupposto —
oggi quasi sempre mancante — di qualunque sistema di consultazione intelligente.

Tutta l'elaborazione avviene sul computer di chi la esegue: nessun contenuto dell'archivio
lascia la macchina.

---

## Il problema da cui nasce

Un'azienda custodisce l'archivio storico delle proprie schede progetto: specifiche
tecniche, manuali, dati di sperimentazione, parametri di configurazione, in formati
eterogenei e distribuiti su migliaia di cartelle. L'archivio è competenza dell'ufficio
tecnico, ma serve continuamente all'ufficio commerciale, che non avendo la competenza per
consultarlo passa dai referenti tecnici. Ne deriva un collo di bottiglia: onere ricorrente
da una parte, attesa dall'altra.

La richiesta arriva di norma già tradotta in soluzione — "serve un motore di ricerca",
"serve un'AI che risponda alle domande". L'ipotesi da cui parte questo progetto è diversa:
il problema non è la mancanza di uno strumento di ricerca, ma il fatto che
**l'informazione non è mai stata razionalizzata**. Finché non si sa che cosa contengono i
documenti, qualunque motore cerca nel disordine — e nessuno può dire quali contenuti siano
esponibili a un servizio esterno.

## Come si legge questo progetto

I documenti in [documentazione/](documentazione/) sono numerati secondo l'ordine di
lettura. Si possono percorrere in sequenza: raccontano il progetto dal problema alla
consegna.

| # | Documento | Risponde alla domanda |
|---|---|---|
| 00 | [Percorso del workshop](documentazione/00_percorso_workshop.md) | Come si presenta e si prova il progetto in due ore |
| 01 | [Contesto e problema](documentazione/01_contesto_e_problema.md) | Da dove nasce, chi ne soffre, quali domande deve reggere l'archivio |
| 02 | [Requisiti e architettura](documentazione/02_requisiti_e_architettura.md) | Quali requisiti emergono e quale architettura ne consegue |
| 03 | [Riservatezza: metodo A e metodo B](documentazione/03_riservatezza_metodo_A_B.md) | Perché il deterministico precede l'agentico, e come si qualifica ciò che è condivisibile |
| 04 | [Progettazione dei moduli](documentazione/04_progettazione_moduli.md) | Come è progettato ciascun modulo, con schemi dati e viste |
| 05 | [Stato dell'arte](documentazione/05_stato_dell_arte.md) | Che cosa esiste oggi, in numeri, e che cosa non è stato costruito |
| 06 | [Dataset di prova](documentazione/06_dataset_di_prova.md) | Su quale archivio si esercita chi non ha il caso reale |
| 07 | [Avvio su Mac](documentazione/07_avvio_mac.md) | Come si installa e si avvia, passo per passo |
| 08 | [Avvio su Windows](documentazione/08_avvio_windows.md) | Come si installa e si avvia, passo per passo |

## Com'è fatto il progetto

| Cartella | Ruolo |
|---|---|
| [documentazione/](documentazione/) | I documenti di analisi e di progetto, numerati nell'ordine di lettura |
| [app/](app/) | L'applicazione web locale: Flask e SQLite, i cinque moduli funzionali, il connettore MCP e la suite di verifica. Il suo [README](app/README.md) è il manuale d'uso dettagliato |
| [scanner/](scanner/) | Lo scanner deterministico a riga di comando e il dizionario dei pattern: è la **fonte di verità** del dizionario, di cui l'applicazione conserva una copia di primo avvio |
| [agente/](agente/) | Il contratto con l'agente di rilevazione: formato delle bozze e istruzioni operative. È la **fonte di verità**; `app/docs_agente/` ne contiene la copia scaricabile dall'applicazione |
| [brand/](brand/) | Identità visuale: logo e note di marchio |
| [strumenti/](strumenti/) | Utilità di servizio, fra cui la preparazione del pacchetto da consegnare |

## Che cos'è già stato costruito

Cinque moduli funzionali, in sequenza di dipendenza:

1. **Inventario e dashboard** — la mappa permanente dell'archivio, mantenuta a livello di
   filesystem e riallineata a ogni apertura. Nessun contenuto viene letto.
2. **Classificazione base** — il dizionario dei pattern con costruzione guidata senza
   espressioni regolari, la scansione deterministica dei contenuti e il triage per file,
   organizzato come coda di lavoro.
3. **Catalogo** — le entità logiche generate da un criterio e l'arricchimento da fonti
   tabellari esterne, con relazione uno-a-molti nativa e provenienza di ogni valore.
4. **Validazione AI** — il perimetro condivisibile, l'import severo delle bozze prodotte
   dall'agente, la coda di revisione ordinata per confidenza crescente, le metriche di
   affidabilità e il connettore MCP che impone il perimetro lato server.
5. **Archivio logico** — il consolidamento che rende il documento un oggetto di prima
   classe: tipologia, aggancio all'entità, riservatezza, e l'export che costituisce la
   consegna verso la fase successiva.

A questi si aggiungono le funzioni di servizio: anagrafica utenti con accesso tramite PIN,
manutenzione e reset dell'archivio.

Lo stato in numeri, la lettura critica di ciò che manca e le metriche che orientano il
seguito sono nel documento [05](documentazione/05_stato_dell_arte.md).

## Come si avvia

Requisiti: Python 3.9 o superiore. Poi, dalla cartella `app`:

```
python3 -m pip install -r requirements.txt
./avvia.sh          # su Windows: avvia.bat
```

Il server parte su `http://127.0.0.1:5000` e il browser si apre da solo. La procedura
completa, pensata per chi non ha familiarità con il terminale, è nei documenti
[07](documentazione/07_avvio_mac.md) e [08](documentazione/08_avvio_windows.md).

## Dove risiedono i dati

I dati di lavoro — la base dati con inventario, esiti di scansione, triage, catalogo e
validazioni, la chiave di sessione, i file temporanei di import — **non stanno in questa
cartella**. Risiedono in `Wikify_dati`, cartella sorella, indicata dalla variabile
d'ambiente `ARCHIVIO_SMART_DATA` e valorizzata dagli script di avvio:

```
Wikify/         il progetto: codice e documentazione
Wikify_dati/    i dati prodotti dall'uso
```

La separazione è deliberata: consente di aggiornare o consegnare il progetto senza
trasferire alcun contenuto dell'archivio analizzato.

## Che cosa Wikify non fa (e perché)

Non contiene ricerca semantica, non costruisce un knowledge graph e non integra un motore
agentico proprio. Non è un ritardo, è una decisione:

- un indice semantico costruito su un archivio non classificato indicizzerebbe il
  disordine, e restituirebbe risultati non filtrabili per riservatezza;
- un grafo su entità non ancora consolidate sarebbe da rifare;
- automatizzare la classificazione prima di aver misurato l'accuratezza dell'agente e il
  costo per archivio sarebbe un atto di fede.

Wikify porta l'archivio al punto in cui quei tre passi diventano possibili, e ne consegna
l'esito in un formato dichiarato: `wikify-archivio/1.0`.

## Preparare la cartella da consegnare

Il progetto contiene anche materiale di lavoro interno, che non fa parte di ciò che si
condivide. Per ottenere il pacchetto da consegnare:

```
strumenti/prepara_condivisione.sh
```

Lo script produce una copia completa e funzionante del progetto — documentazione,
applicazione, scanner, contratto dell'agente, identità visuale — **escludendo** il
materiale interno, i dati di lavoro e le scorie tecniche. Il dettaglio di ciò che viene
escluso è dichiarato nello script stesso.

---

*Prototipo generato e integrato con il supporto di sistemi AI generativi, sotto la
supervisione e l'architettura tecnica di Carlo Verdini (IT System Integrator & AI
Trainer).*
