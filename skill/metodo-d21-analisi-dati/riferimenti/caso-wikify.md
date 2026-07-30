# Il caso Wikify: il metodo applicato per intero

Caso reale, condotto in diciotto sessioni di lavoro. Serve come esempio quando occorre
mostrare come si passa da una richiesta a un sistema, e soprattutto quali decisioni si
prendono lungo la strada.

## Il punto di partenza

Archivio storico di schede progetto di componentistica industriale (sonde di temperatura,
controller, porta sonda). Ogni cartella progetto contiene specifiche tecniche, manuali di
installazione e manutenzione, dati di sperimentazione, parametri di interconnessione, in
formati eterogenei. Un progetto alimenta uno o più articoli commerciali, e il legame è
mantenuto su un file XLS gestito a parte.

L'archivio è competenza dell'ufficio tecnico; l'ufficio commerciale ne ha bisogno di
continuo senza averne la competenza. Ogni richiesta commerciale diventa un'interruzione per
un tecnico e un'attesa per chi ha chiesto.

**La richiesta è arrivata già formulata come soluzione**: "serve un motore di ricerca",
"serve un'AI che risponda alle domande".

## Le decisioni prese, e il perché

**1. Riformulare in domande prima di progettare.** Dalla discovery è emerso che prevalgono
le ricerche esatte ("le specifiche di configurazione dell'articolo X"), con una coda di
domande esplorative e di confronto. Conseguenza: il livello necessario è il catalogo
strutturato, non l'indice semantico.

**2. Separare le tre dimensioni.** Strutturata (progetto, articolo, codici), documentale
(contenuti dei file), di governance (chi vede che cosa). Tenerle distinte ha evitato di
progettare un unico sistema che le confondeva.

**3. Riconoscere il requisito più strutturante.** I permessi sono **per informazione, non
per documento**: lo stesso manuale può contenere una sezione riservata. Da qui discende che
l'unità di gestione non è il file, che il documento va scomposto e classificato, e che il
filtro va applicato al momento del recupero. È il punto in cui la classificazione smette di
essere un'attività preparatoria e diventa il cuore del progetto.

**4. La domanda che ha cambiato l'ordine delle fasi.** Possiamo esporre questi documenti a
un agente AI? Nessuno in azienda sapeva con certezza che cosa contenessero. Decisione: il
non ancora qualificato si tratta come riservato, e si procede in due tempi: un **metodo A
deterministico** (scanner locale su pattern testuali, nessun contenuto che lascia il
computer) che bonifica il perimetro, e un **metodo B agentico** che opera solo su ciò che è
stato qualificato condivisibile. Con retroazione: ciò che l'agente scopre torna nel
dizionario dei pattern.

**5. Costruire uno strumento usabile da chi conosce il dominio.** Il primo scanner
funzionava ma richiedeva espressioni regolari: inutilizzabile da chi avrebbe dovuto usarlo.
Da qui un'applicazione locale con builder guidato e prova live, senza regex.

**6. Base modulare unica anziché strumenti separati.** Un nucleo condiviso e un modulo per
fase. Costo aggiuntivo stimato circa il 15%, ripagato dagli incroci tra le fasi.

**7. Imporre i vincoli, non raccomandarli.** Nel connettore che collega l'agente al sistema,
il perimetro condivisibile non è una regola scritta nelle istruzioni: è un vincolo del
server, che rifiuta la lettura dei file fuori perimetro.

**8. Rendere il documento un oggetto di prima classe.** Finché un documento non ha una
tipologia stabile, un legame esplicito con l'entità e una riservatezza consolidata,
l'archivio resta una cartella di file. L'ultimo modulo costruito consolida i tre attributi
per via deterministica, con precedenza tracciata: correzione manuale, poi validazione umana,
poi regola automatica; e ricostruzione idempotente, che non cancella mai il lavoro umano.

**9. Non costruire il livello semantico.** Niente RAG, niente knowledge graph, niente motore
agente integrato: senza archivio logico si indicizzerebbe il disordine, e senza metriche
l'automazione sarebbe un atto di fede. La consegna verso la fase successiva è un export
dichiarato e versionato, che porta con sé la qualifica di riservatezza.

## Che cosa se ne ricava, in generale

- Il sintomo dichiarato non è il requisito: lo sono le domande.
- Il vincolo di riservatezza, quasi mai sollevato dal committente, è spesso quello che
  decide l'architettura.
- Il deterministico precede l'agentico quando non si sa che cosa contengono i dati.
- Rinunciare a costruire, motivandolo, è una decisione progettuale: va dichiarata e
  argomentata, non subita.
- La maturità di un archivio si misura (copertura di classificazione, completezza per
  entità), non si percepisce.
