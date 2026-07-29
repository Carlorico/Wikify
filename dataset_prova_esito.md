# Esito costituzione del dataset di prova — Wikify

Resoconto operativo della costituzione dell'archivio di prova previsto dal piano descritto in `dataset_prova.md`, sezione "Piano di costituzione del campione". L'archivio è stato realizzato in `Workshop/Wikify_archivio_prova/`, cartella sorella di `Wikify/` e deliberatamente esclusa dal repository, in coerenza con la natura non ridistribuibile dei documenti scaricati.

## Dimensione e composizione dell'archivio

- **Dimensione totale**: 390 MB, ampiamente al di sotto sia della soglia di allerta (450 MB) sia del tetto assoluto (500 MB) indicati come vincolo operativo.
- **File scaricati**: 76 su 77 tentativi (un solo insuccesso, cfr. sezione dedicata) — ben al di sotto del tetto di 200 file.
- **Composizione per tipo**:
  - PDF: 76 (documentazione tecnica Immergas)
  - DOCX: 6 (`verbale_collaudo_simulato.docx`)
  - XLSX: 7 (1 `progetti_articoli.xlsx` + 6 `parametri_configurazione_cliente.xlsx`)
  - TXT: 8 (6 `note_tecniche.txt` + 2 file di log tecnico del processo di acquisizione, `_download_log.txt` e `_extractability_log.txt`, utili per tracciabilità ma non pensati come materiale d'aula)

Il download è stato condotto in modo sequenziale, con pausa di circa un secondo tra una richiesta e l'altra, senza percorrere ricorsivamente il sito ma limitandosi alle due pagine di categoria Immergas ("manuali uso caldaie" e "schede tecniche caldaie") e ai PDF da esse collegati per le quattro serie di interesse.

## Albero delle cartelle (sintetico, primi due livelli)

```
Wikify_archivio_prova/
├── progetti_articoli.xlsx
├── _download_log.txt, _extractability_log.txt
├── _scansioni_escluse/            (vuota: nessun PDF escluso)
├── Immergas_ARES/                 (7 cartelle progetto)
│   ├── ARES_18-25/
│   ├── ARES_18-25_CS/
│   ├── ARES_CONDENSING_32_ErP/
│   ├── ARES_PRO/
│   ├── ARES_TEC_150-900/
│   ├── ARES_TEC_200-900/
│   └── NUOVA_ARES/
├── Immergas_EOLO/                 (7 cartelle progetto)
│   ├── EOLO_ECO/, EOLO_STAR/, EOLO_MAIOR/, EOLO_SUPERIOR/
│   ├── EOLO_EXTRA/, EOLO_MINI/, SUPER_EOLO/
├── Immergas_VICTRIX/               (9 cartelle progetto)
│   ├── VICTRIX_24-32_TT/, VICTRIX_26_PLUS/, VICTRIX_INTRA/, VICTRIX_MAIOR/
│   ├── VICTRIX_OMNIA/, VICTRIX_SUPERIOR/, VICTRIX_TERA/, VICTRIX_EXA/, VICTRIX_PRO/
└── Immergas_ZEUS/                  (8 cartelle progetto)
    ├── ZEUS_ECO/, ZEUS_MINI/, ZEUS_24-28/, ZEUS_EXTRA/
    ├── ZEUS_MAIOR/, ZEUS_SUPERIOR/, VICTRIX_ZEUS/, ZEUS_catalogo/
```

In totale **31 cartelle progetto**, ciascuna contenente da 1 a 4 documenti (manuale d'uso, scheda tecnica, libretto installatore/tecnico), coerentemente con l'eterogeneità documentale attesa.

## Esito del controllo di estraibilità testuale

Il controllo è stato condotto con `pypdf` su tutti i 76 PDF scaricati, estraendo il testo delle prime tre pagine e applicando la soglia indicativa di 200 caratteri complessivi.

- **PDF estraibili**: 76 su 76 (100%).
- **PDF esclusi**: nessuno. La cartella `_scansioni_escluse/` è stata predisposta come da piano, ma è risultata vuota: la conferma, già ipotizzata nel documento di analisi sulla base di un campione di due soli documenti, si è quindi estesa senza eccezioni all'intero perimetro di 76 file. Il valore minimo di caratteri estratti registrato è stato 311 (catalogo tecnico di gamma ZEUS, documento sintetico), comunque superiore alla soglia.

## Popolamento di `progetti_articoli.xlsx`

Il file è stato costruito manualmente a partire dai nomi dei modelli effettivamente rilevati nelle due pagine di categoria Immergas, con colonne `id_progetto`, `serie`, `codice_commerciale`, `tipo_prodotto`, `anno_documento`, `note`.

- **Righe totali**: 55
- **Progetti distinti** (cartella progetto): 31
- **Codici commerciali**: 54 valori non vuoti, tutti distinti tra loro
- **Progetti con più di un codice commerciale**: 19 su 31 (61%) — è la relazione 1:N richiesta per dimostrare l'arricchimento cartella→articoli. Esempi: `ARES_18-25` → ARES-18, ARES-25; `VICTRIX_MAIOR` → VICTRIX-MAIOR-28-35-TT, VICTRIX-MAIOR-35-TT-PLUS; `ZEUS_SUPERIOR` → ZEUS-SUPERIOR-24-28-32-kW, ZEUS-24-27-SUPERIOR.
- La colonna `anno_documento` è stata lasciata sistematicamente vuota: nessuno dei documenti selezionati riportava in modo affidabile un anno in etichetta o nel nome file, e si è preferito non stimarlo. Analogamente, la cella `codice_commerciale` del catalogo tecnico di gamma ZEUS è stata lasciata vuota, trattandosi di un documento di gamma non riferito a un singolo articolo (annotato in `note`).

## File simulati con contenuti sensibili

Inseriti in **8 cartelle progetto** (nel range 6-8 richiesto), distribuite sulle quattro serie, con distribuzione bilanciata tra "entrambi i file" e "un solo file":

| Cartella | Verbale collaudo | Parametri configurazione |
|---|---|---|
| Immergas_ARES/ARES_18-25_CS | ✓ | ✓ |
| Immergas_ARES/ARES_PRO | ✓ | |
| Immergas_EOLO/EOLO_ECO | ✓ | ✓ |
| Immergas_EOLO/EOLO_MAIOR | | ✓ |
| Immergas_VICTRIX/VICTRIX_OMNIA | ✓ | ✓ |
| Immergas_VICTRIX/VICTRIX_SUPERIOR | ✓ | |
| Immergas_ZEUS/ZEUS_SUPERIOR | ✓ | ✓ |
| Immergas_ZEUS/VICTRIX_ZEUS | | ✓ |

Ogni file riporta in testa la dicitura "Documento sintetico generato a scopo didattico — dati non reali" e non contiene nomi di persone o aziende realmente esistenti (nominativi e ragioni sociali sono palesemente inventati). I verbali includono matricole fittizie, nome di un tecnico, riferimento a un cliente di fantasia ed esito di collaudo; i file di parametri includono indirizzi IP di esempio, credenziali fittizie e un indirizzo email su dominio `example.com`.

Per la varietà di formato, sono stati aggiunti **6 file `note_tecniche.txt`** (soglia minima richiesta: 5) nelle cartelle `ARES_CONDENSING_32_ErP`, `EOLO_STAR`, `VICTRIX_26_PLUS`, `VICTRIX_TERA`, `ZEUS_MINI`, `ZEUS_MAIOR`, con brevi annotazioni plausibili sul modello.

## Documenti e pagine saltati

- **1 PDF non scaricato**: `IMMERGAS-libretto-istruzioni-caldaia-a-gas-EOLO-EXTRA-28-KW.pdf` (cartella `EOLO_EXTRA`) — risposta HTTP 404, link presente in pagina ma file non più disponibile sul server. Non si è insistito con tentativi ripetuti, come da indicazione operativa; la cartella `EOLO_EXTRA` resta comunque popolata con la relativa scheda tecnica.
- Le due pagine di categoria («manuali uso caldaie Immergas» e «schede tecniche caldaie Immergas») sono state raggiunte con l'estensione `.html`, non `.php`: un primo tentativo con `.php` ha restituito 404 e non è stato ripetuto oltre la verifica dell'estensione corretta.
- Non sono state visitate pagine oltre queste due e i PDF da esse direttamente collegati: nessuna navigazione ricorsiva del sito.

## Aree di attenzione residue

- **Naming non sempre univoco tra le due pagine di origine**: per alcune cartelle (es. `ARES_18-25`, `NUOVA_ARES`) il libretto istruzioni o la scheda tecnica reperibili in pagina "schede tecniche" usano la dicitura "NUOVA ARES" anziché "ARES", pur riferendosi verosimilmente alla stessa linea commerciale. È un'eco fedele di quanto già segnalato nel piano circa l'eterogeneità di naming del sito; l'abbinamento cartella-documento in questi casi è stato fatto per prossimità di modello, non per identità letterale di codice, ed è annotato in `note` dove rilevante.
- **Relazione progetto↔articolo ricostruita manualmente**: come previsto dal piano, il file `progetti_articoli.xlsx` non discende da un export gestionale ma da una lettura diretta delle pagine di serie; resta quindi un margine di soggettività nella scelta di quali varianti di modello considerare "codici commerciali" distinti rispetto a semplici rinominazioni dello stesso prodotto.
- **Contenuti sensibili interamente simulati**: come ipotizzato nel piano, il linguaggio e la distribuzione dei dati fittizi nei verbali e nei parametri di configurazione potrebbero risultare più regolari e meno "naturali" di quanto si riscontrerebbe in un caso reale, con un possibile margine di artificiosità nell'esercizio sullo scanner di riservatezza rispetto al caso d'uso originario.
- **Questione legale non chiusa**: resta di competenza di Carlo la decisione se e come citare la fonte (schede-tecniche.it) nel materiale d'aula, dato che il sito ripubblica documentazione di proprietà dei produttori senza licenza dichiarata, pur non vietandone esplicitamente un prelievo limitato a fini didattici.
- **File di log tecnico in radice archivio**: `_download_log.txt` e `_extractability_log.txt` sono stati mantenuti nella radice dell'archivio per tracciabilità del processo; non sono pensati come materiale d'esercitazione e possono essere rimossi o spostati se si desidera un archivio "pulito" per la sola esercitazione d'aula.

---

## Adeguamento della struttura (29/07/2026)

L'archivio è stato riorganizzato dopo la costituzione, per allinearlo al modello dati di
Wikify: l'applicazione considera **cartella progetto il primo livello sotto la radice**,
mentre la struttura iniziale collocava i progetti al secondo livello, sotto la serie. Con
l'impianto originario si sarebbero generate quattro entità (le serie) anziché trentuno
(i progetti), snaturando l'analogia con l'archivio del committente.

Interventi eseguiti:

- le 31 cartelle progetto sono state portate al primo livello, conservando il nome
  (`ARES_18-25`, `EOLO_MINI`, `VICTRIX_TT`, …); le quattro cartelle di serie, rimaste vuote,
  sono state rimosse. La serie resta ricavabile dal prefisso del nome e, in modo esplicito,
  dalla colonna `serie` del file tabellare;
- la colonna `id_progetto` di `progetti_articoli.xlsx` è stata riscritta di conseguenza
  (55 righe aggiornate): non più `Immergas_ARES/ARES_18-25`, ma `ARES_18-25`;
- i due file di log di processo (`_download_log.txt`, `_extractability_log.txt`) sono stati
  spostati in `Workshop/Wikify_archivio_prova_log/`: dentro l'archivio sarebbero stati
  inventariati come documenti, falsando i conteggi;
- la cartella `_scansioni_escluse/`, rimasta vuota, è stata eliminata.

## Collaudo dell'archivio con Wikify (29/07/2026)

L'archivio è stato percorso per intero dall'applicazione, su base dati temporanea. Esito:
**20 verifiche superate su 22**; le due non superate corrispondono a soglie di controllo
troppo rigide e non a difetti, come chiarito sotto.

| Fase | Esito |
|---|---|
| Inventario | 95 file mappati, 31 cartelle progetto riconosciute, istantaneo |
| Formati | 76 pdf, 7 xlsx, 6 txt, 6 docx |
| Scansione | 95 file analizzati, **nessun file non analizzabile**, 303 secondi |
| Segnalazioni | 1.339 su 67 file — configurazione 1.030, cliente 207, credenziali 37, interconnessione 30, marcature esplicite 29, sperimentazione 6 |
| Documenti simulati | tutti e 12 intercettati dallo scanner |
| Entità | 31 generate dalle cartelle progetto |
| Arricchimento | 117 valori agganciati; **19 progetti con più codici commerciali** (relazione 1:N dimostrata) |
| Consolidamento | 95 documenti, 89 classificati (94%), 94 agganciati, 12 riservati |
| Export | JSON con 31 entità e 94 documenti (45 KB); XLSX (11 KB) |

### Le due soglie non superate, e cosa raccontano

- **Copertura di classificazione al 94%**: sei documenti non intercettati dalle sei regole
  di dimostrazione. Cinque sono PDF con una variante di nomenclatura non prevista
  (`manuale_tecnico_*`, `catalogo_tecnico_ZEUS`), il sesto è `progetti_articoli.xlsx`, che
  risiede alla radice e non appartiene ad alcun progetto. È esattamente ciò per cui
  l'indicatore esiste: rende visibile la lacuna e invita ad aggiungere una regola. In aula
  è materiale prezioso, e si consiglia di **non** correggerlo in anticipo.
- **Aggancio alle entità 94 su 95**: l'unico documento non agganciato è ancora
  `progetti_articoli.xlsx`, che sta fuori dalle cartelle progetto. Comportamento corretto:
  nel dominio reale il file di mapping vive anch'esso fuori dall'archivio.

### Una nota sulle anomalie di import

L'import del file tabellare registra 47 anomalie, tutte di tipo `duplicato_esatto`: sono i
valori di `serie` e `tipo_prodotto` che si ripetono sulle righe dello stesso progetto,
mentre solo `codice_commerciale` varia. Non è un difetto del file: è la deduplicazione che
lavora e distingue l'attributo realmente 1:N dagli attributi costanti. Vale la pena
mostrarlo in aula, perché è il tipo di segnalazione che a prima vista allarma e che invece
va letta.

### Un dato utile per la conduzione dell'aula

La scansione di 95 file per 390 MB ha richiesto **circa cinque minuti** su un portatile
recente: va previsto nei tempi dell'esercitazione, oppure va fatta eseguire agli studenti
su un sottoinsieme di cartelle.
