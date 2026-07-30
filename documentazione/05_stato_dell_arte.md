# Stato dell'arte

*Risponde alla domanda: che cosa esiste oggi di Wikify, che cosa non è stato costruito e
quali indicatori orientano il seguito.*

## Che cosa esiste

L'applicazione è completa e in esercizio nella sua prima versione. È un'applicazione web
locale (Flask e SQLite, nessun servizio esterno) organizzata su un nucleo condiviso e
cinque moduli funzionali, ciascuno con le proprie tabelle e le proprie pagine.

| Ambito | Stato |
|---|---|
| Inventario e dashboard | Realizzato: mappa permanente dei file, riallineamento automatico all'apertura, indicatori dell'archivio |
| Classificazione base | Realizzato: dizionario dei pattern con costruzione guidata senza espressioni regolari, scansione deterministica, triage per file come coda di lavoro |
| Catalogo | Realizzato: entità logiche da criterio, arricchimento da fonti tabellari con relazione uno-a-molti e provenienza dei valori |
| Validazione AI | Realizzato: perimetro condivisibile, import severo delle bozze, coda per confidenza crescente, metriche di affidabilità |
| Connettore MCP | Realizzato: sei strumenti esposti, perimetro imposto lato server, sessioni di analisi con stima di token e costi |
| Archivio logico | Realizzato: tipologia da regole deterministiche, aggancio all'entità, riservatezza consolidata, export di consegna |
| Funzioni di servizio | Realizzate: anagrafica utenti con accesso tramite PIN, manutenzione e reset dell'archivio |

Alcuni numeri, utili a inquadrare la solidità di quanto esiste:

- **schema dati alla migrazione V7**, tutte le migrazioni additive: i database creati con le
  versioni precedenti si aggiornano all'avvio senza perdita di dati;
- **131 verifiche automatiche** nella suite, eseguite a ogni modifica del codice; tre di
  queste presidiano la coerenza fra i file che, per necessità funzionale, esistono in due
  punti del progetto (il contratto dell'agente e il dizionario dei pattern): se una copia
  divergesse dalla propria fonte di verità, la suite fallirebbe;
- **13 regole in 6 categorie** nel dizionario di partenza, inteso come seme dimostrativo e
  non come dizionario definitivo;
- **due formati di scambio dichiarati e versionati**: `wikify-bozza/1.0` per le proposte
  dell'agente, `wikify-archivio/1.0` per la consegna verso la fase successiva.

## Che cosa è stato provato, e con quale esito

La catena completa è stata percorsa su un archivio di prova reale di 389 MB: 95 file su 31
cartelle progetto, descritto nel documento [06](06_dataset_di_prova.md).

| Fase | Esito rilevato |
|---|---|
| Inventario | 95 file mappati, 31 cartelle progetto riconosciute, tempo trascurabile |
| Scansione dei contenuti | 95 file analizzati, nessun file illeggibile, circa cinque minuti |
| Segnalazioni | 1.339 su 67 file, distribuite su sei categorie del dizionario |
| Triage | 12 documenti qualificati riservati, 83 condivisibili |
| Catalogo | 31 entità generate; 19 progetti con più di un codice commerciale, a dimostrare la relazione uno-a-molti |
| Archivio logico | 95 documenti consolidati, 94% classificati, 99% agganciati a un'entità |
| Consegna | Export con 31 entità e 94 documenti, completo dei livelli di riservatezza |

Il 94% di copertura non è un difetto da correggere prima di mostrarlo: cinque documenti
usano una variante di nomenclatura che le regole di dimostrazione non prevedono. È
esattamente la funzione dell'indicatore: rendere visibile una lacuna e indicare dove
aggiungere una regola.

## Che cosa non è stato costruito

Tre assenze sono deliberate e vanno lette come decisioni di progetto.

**Non c'è ricerca semantica.** Un indice vettoriale costruito su un archivio non
classificato indicizzerebbe il disordine, e soprattutto restituirebbe risultati non
filtrabili per riservatezza: il filtro sui permessi va applicato prima del recupero, non a
valle sulla risposta. Prima serve l'archivio logico, che è ciò che questa versione consegna.

**Non c'è un knowledge graph.** Costruirlo su entità non ancora consolidate significherebbe
rifarlo: le entità esistono da poco e la loro completezza è ancora in corso di misurazione.

**Non c'è un motore agentico integrato.** L'infrastruttura è pronta, il connettore MCP
consente già a un agente esterno di lavorare sul solo perimetro condivisibile, ma
l'automazione della classificazione richiede prima di sapere quanto è accurata. Costruirla
adesso sarebbe un atto di fede.

## Gli indicatori che orientano il seguito

Le decisioni successive non dipendono da un giudizio di opportunità, ma da misure che
l'applicazione già raccoglie:

- **accuratezza per campo**: quante proposte dell'agente vengono confermate senza
  correzione, distinguendo le proposte sull'intero documento da quelle su sezioni;
- **correlazione fra confidenza ed esito**: se il modello riconosce quando non sa, la
  cascata fra un modello economico e uno più capace si giustifica; altrimenti no;
- **tempo mediano di validazione** per proposta e per cartella: è il costo del presidio
  umano, e dimensiona il lavoro a regime;
- **costo stimato per archivio**, calcolato dai caratteri letti e prodotti e dai prezzi
  impostati per ciascun modello;
- **copertura di classificazione e completezza per entità**: dicono se l'archivio è maturo
  per il livello semantico, o se serve un altro giro di regole.

Nessuna di queste misure è ancora disponibile su un volume significativo: il ciclo agentico
è stato collaudato, non esercitato su un campione ampio. È il primo passo del seguito.

## Aree di attenzione dichiarate

- **La riservatezza consolidata conserva due vocabolari.** Il triage usa "Riservato" e
  "Condivisibile", le proposte dell'agente usano "riservato", "condivisibile" e "misto". I
  due vocabolari non sono stati unificati per non modificare contratti già congelati:
  l'origine del valore resta tracciata, ma chi legge l'export deve tenerne conto.
- **La correzione manuale della riservatezza** è supportata dal dominio ma non ha ancora un
  punto di ingresso nell'interfaccia: in interfaccia si corregge la tipologia.
- **La tassonomia delle tipologie documentali** è quella dedotta in fase di analisi e attende
  conferma dal responsabile tecnico dell'archivio reale.
- **I PDF privi di testo** non vengono analizzati: non è previsto riconoscimento ottico dei
  caratteri. Sull'archivio di prova non se ne sono trovati, ma su un archivio storico reale
  è un'eventualità concreta.
