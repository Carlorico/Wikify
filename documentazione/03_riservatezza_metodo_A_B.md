# Riservatezza: il metodo A e il metodo B

*Risponde alla domanda: come si è deciso se, e a quali condizioni, i contenuti dell'archivio
potessero essere mostrati a un agente basato su intelligenza artificiale, e come questa
decisione ha riordinato le fasi del progetto.*

## La domanda che ha fermato il percorso previsto

Il piano operativo originario prevedeva che un agente esaminasse un campione di cartelle progetto, proponesse una classificazione documentale e una prima valutazione di riservatezza, e che un responsabile tecnico validasse le proposte attraverso un'interfaccia dedicata. Prima di avviare questo esame, tuttavia, si è imposta una domanda preliminare, tanto semplice quanto dirimente: possiamo esporre questi documenti a un agente AI?

Non era una domanda retorica. Non essendo ancora nota la natura né la riservatezza reale dei contenuti dell'archivio, non era possibile assumere che fossero condivisibili con un servizio esterno, per quanto affidabile. Il problema, per come si presentava, era circolare: per classificare la riservatezza di un contenuto occorrerebbe leggerlo, ma leggerlo con un agente presuppone di averne già valutato la condivisibilità. Nessuna delle due condizioni può essere soddisfatta per prima senza l'altra, se si resta su un unico metodo.

## La regola prudenziale

Prima ancora di introdurre una soluzione tecnica, si è fissato un principio di cautela che vale indipendentemente da qualunque scanner o agente: ciò che non è ancora stato qualificato si tratta come riservato. In altri termini, il default è la non condivisibilità: un documento entra nel perimetro accessibile all'agente solo dopo una qualifica esplicita, non per assenza di obiezioni. Questa regola, semplice da enunciare, è il cardine su cui si è costruita l'intera sequenza descritta di seguito.

## Il metodo A: deterministico

Il metodo A è una scansione algoritmica, scritta in Python ed eseguita interamente in locale, che rileva pattern testuali riconducibili a informazioni riservate (parametri di configurazione, credenziali di interconnessione, riferimenti a clienti specifici, marcature esplicite come "riservato") e li segnala in un report puntuale, con evidenza e posizione. Nessun contenuto lascia il perimetro aziendale: è condizione necessaria perché il metodo possa operare prima ancora che la riservatezza sia nota.

I pregi e i limiti del metodo A vanno dichiarati senza reticenze, perché condizionano l'uso che se ne può fare. È totalmente riproducibile (stesso input, stesso output, verificabile in ogni momento) e quindi pienamente auditabile.

Per contro, riconosce solo ciò che il dizionario dei pattern gli ha insegnato a cercare: il rischio di falsi negativi sul non previsto è concreto, mentre i falsi positivi, pur frequenti su pattern generici, restano economici da scartare in fase di revisione umana. Richiede un costo di avvio, costruire il dizionario dei pattern insieme al responsabile tecnico, e un costo di manutenzione nel tempo, ma quel dizionario, una volta costruito, resta un asset di sicurezza permanente, riutilizzabile ben oltre l'occasione che lo ha originato.

## Il metodo B: agentico

Il metodo B è l'esame assistito da un agente con validazione umana, previsto fin dal piano originario: comprende il contesto, non solo la forma, ed è quindi in grado di cogliere una riservatezza implicita che il metodo A, vincolato ai pattern noti, non può vedere.

Il prezzo di questa capacità va dichiarato con altrettanta onestà: i contenuti letti dall'agente vengono comunque trasmessi a un modello linguistico, un'esposizione mitigabile in prospettiva ricorrendo a modelli eseguiti in locale; l'esito non è deterministico e richiede tracciamento; il metodo è pronto all'uso ma richiede una governance della condivisione che il metodo A, per costruzione, non richiede. È il metodo B, del resto, a prototipare la futura pipeline di classificazione a regime, ed è per questo che il suo costo si giustifica.

## Un confronto onesto fra i due metodi

Nessuno dei due metodi è preferibile in assoluto: la tabella seguente mette a confronto gli stessi criteri sui due approcci, così da rendere esplicito perché la soluzione adottata sia la loro sequenza e non la scelta dell'uno o dell'altro.

| Criterio | Metodo A (deterministico) | Metodo B (agentico) |
|---|---|---|
| Esposizione dei dati | Nessuna: elaborazione locale | Contenuti trasmessi al modello linguistico, mitigabile con modelli on-premise |
| Riproducibilità | Totale, auditabile | Non deterministica, richiede tracciamento |
| Capacità di rilevazione | Solo pattern noti a priori | Coglie riservatezza implicita e casi non previsti |
| Falsi negativi | Rischio alto sul non previsto | Rischio più basso, ma non azzerato |
| Falsi positivi | Frequenti ma economici da scartare | Più rari, motivati con evidenza citata |
| Costo di avvio | Costruire il dizionario dei pattern | Pronto all'uso, ma richiede governance della condivisione |
| Costo di manutenzione | Dizionario da mantenere nel tempo | Prompt e tassonomie da raffinare |
| Valore aggiuntivo | Asset di sicurezza permanente | Prototipo della futura pipeline di classificazione |

## La sequenza, non l'alternativa

I due metodi non sono in competizione: presidiano rischi diversi, e per questo la soluzione adottata li dispone in sequenza anziché sceglierne uno solo. Il metodo A è lo strumento giusto quando l'errore da evitare è l'esposizione: meglio un falso positivo di troppo che un dato riservato condiviso per errore. Il metodo B è lo strumento giusto quando l'errore da evitare è una classificazione povera: meglio comprendere il contesto che applicare regole cieche. La sequenza operativa adottata è la seguente:

1. costruzione del dizionario dei pattern con il responsabile tecnico, a partire da un'ipotesi di ciò che è certamente riservato (parametri di configurazione, credenziali di interconnessione, riferimenti a clienti, dati di sperimentazione non pubblicati);
2. scansione deterministica del metodo A sul campione, con report per file, pattern rilevato, posizione e contesto; nessun contenuto lascia il perimetro;
3. triage del responsabile tecnico sul report: ogni segnalazione viene marcata Riservato o Condivisibile; anche i file privi di segnalazioni vengono campionati a controllo, per stimare i falsi negativi del dizionario;
4. segregazione progressiva, secondo la regola prudenziale: ciò che non è ancora stato qualificato resta trattato come riservato;
5. esame agentico del metodo B, condotto esclusivamente sui materiali che il triage ha qualificato come condivisibili;
6. retroazione: i casi in cui il metodo B individua indizi di riservatezza sfuggiti al metodo A vengono ricondotti al dizionario dei pattern, che si arricchisce a ogni ciclo.

Questa retroazione merita un'osservazione a parte: il dizionario dei pattern non è un artefatto statico prodotto una volta e poi congelato. È un asset che matura nel tempo proprio grazie al confronto con il metodo B, che intercetta ciò che le regole non avevano ancora previsto e lo restituisce sotto forma di nuova regola. I due metodi, in questo senso, non solo coesistono: si migliorano a vicenda.

## Il registro di segregazione

L'artefatto centrale di questa fase è il registro di segregazione, alimentato progressivamente man mano che le informazioni vengono qualificate. Non è un sottoprodotto dell'assessment: è il primo nucleo della tassonomia di riservatezza del progetto, e la base con cui verrà configurata in futuro la separazione degli accessi del sistema finale.

Per ciascun riferimento puntuale (file, foglio, capitolo, intervallo di righe) il registro riporta:

- la **qualifica** assegnata: Riservato, Condivisibile o Da valutare;
- la **motivazione**, cioè il criterio applicato dal responsabile tecnico nell'attribuirla;
- l'eventuale **vincolo** specifico, ad esempio una visibilità riservata a un singolo cliente;
- il **tracciamento** di data e validatore, indispensabile per poter risalire a chi ha deciso cosa e quando.

Questa struttura non è un dettaglio amministrativo: è ciò che rende il registro riutilizzabile come base dati per il futuro filtro degli accessi, non solo come verbale di una decisione presa una volta.

## Il perimetro imposto, non raccomandato

Un ultimo principio, maturato nel corso del progetto, merita di essere reso esplicito perché ne segna l'evoluzione più significativa: il rispetto del perimetro condivisibile non può essere affidato a un'istruzione rivolta all'agente, per quanto ben scritta.

Nella prima versione del metodo B il perimetro era descritto in un documento di istruzioni che l'agente era tenuto a rispettare: una raccomandazione, non un vincolo strutturale. Per quanto l'agente fosse istruito con cura, la garanzia restava affidata alla sua condotta, non a un impedimento reale.

L'evoluzione successiva ha spostato questo vincolo dentro l'infrastruttura stessa: è il punto di accesso ai contenuti a rifiutare fisicamente la lettura di un file fuori perimetro, indipendentemente dal comportamento dichiarato dall'agente. Non è più una regola che l'agente promette di rispettare, ma una condizione che non ha fisicamente la possibilità di violare.

Il principio che ne risulta è generale e vale oltre il caso specifico: la sicurezza dell'informazione non va delegata alla buona condotta di chi la consulta, va imposta da chi la eroga. È un principio che rimane valido indipendentemente da quale agente, o quale futura evoluzione tecnologica, verrà collegato all'archivio.
