# Istruzioni operative per l'agente di rilevazione (Claude / Claude Code)

Procedura guidata per generare le bozze di classificazione del campione. Questo documento è pensato per essere dato in pasto a Claude o Claude Code (e diventerà parte della skill Wikify). Formato di output: v. `formato_bozze.md` (contratto congelato).

## Prerequisiti

1. L'app Wikify ha completato scansione e triage delle cartelle del campione: i file sono qualificati Riservato / Condivisibile.
2. È stato esportato dall'app il **perimetro condivisibile** (elenco dei file consultabili, file `perimetro_condivisibile.json`).
3. L'agente ha accesso in lettura alle cartelle del campione.

## Regole vincolanti (in ordine di priorità)

1. **Perimetro**: leggere ESCLUSIVAMENTE i file elencati nel perimetro condivisibile. I file non elencati non vanno aperti, nemmeno per "dare un'occhiata": vanno riportati in `file_esclusi_da_perimetro`.
2. **Evidenza obbligatoria**: ogni proposta cita posizione e testo letterale (max 300 caratteri) che la giustifica. Nessuna proposta senza fonte: in assenza di evidenza, la proposta non va emessa.
3. **Confidenza onesta**: la confidenza riflette il dubbio reale. Meglio 0.5 sincero che 0.9 di cortesia: la coda di revisione ordina per confidenza crescente e un valore gonfiato nasconde i casi che meritano attenzione umana.
4. **Tassonomie chiuse**: i valori proposti appartengono alle tassonomie del formato; ciò che non rientra va segnalato in `note_agente`, non forzato in una categoria.
5. **Nessuna modifica ai file**: accesso in sola lettura.

## Procedura per ogni cartella progetto

1. Leggere l'elenco file della cartella e incrociarlo col perimetro: costruire `file_esaminati` e `file_esclusi_da_perimetro`.
2. Per ogni file esaminabile, estrarre il testo e produrre le proposte:
   - `tipologia` (sempre, una per file);
   - `riservatezza` (sempre: condivisibile/riservato/misto; per i misti indicare la sezione di confine. Nota: si lavora su file già qualificati condivisibili dal triage, quindi una proposta "riservato" o "misto" è una segnalazione di possibile svista del Metodo A e va motivata con particolare cura);
   - `versione_ufficiale` (solo se nella cartella esistono più versioni dello stesso documento);
   - `forma_caratteristiche` (solo per i documenti che contengono caratteristiche tecniche).
3. Compilare il JSON secondo `formato_bozze.md`, un file per cartella, nome: `bozza_<cartella>.json`.
4. Non tentare di compilare la conoscenza tacita (sezione E delle schede): è riservata alla rilevazione umana.

## Dopo la generazione

Le bozze si importano nell'app (modulo Validazione AI) dove il responsabile tecnico le conferma o corregge. Le correzioni esportate dall'app vanno rilette dall'agente come esempi prima del lotto successivo: è il meccanismo di miglioramento continuo. Le eventuali proposte "riservato/misto" confermate dall'umano vanno anche ricondotte al dizionario dei pattern dello scanner (retroazione A←B).
