# Schede operative

Strumenti da compilare con l'utente durante l'analisi. Vanno usati come traccia, non come
modulistica: se una voce non è nota, si dichiara che non è nota anziché riempirla.

---

## 1. Catalogo Dati (una riga per sorgente)

| Campo | Che cosa registrare |
|---|---|
| Sorgente | Nome con cui la chiamano davvero le persone, non quello del sistema |
| Proprietario | Chi risponde del contenuto, non chi amministra il server |
| Contenuto | Che cosa rappresenta, in una frase comprensibile a chi non la usa |
| Granularità | Qual è l'unità di una riga o di un documento |
| Aggiornamento | Con quale frequenza cambia, e per mano di chi |
| Chiavi | Come si lega alle altre sorgenti; se il legame è informale, dichiararlo |
| Qualità percepita | Di che cosa si fidano e di che cosa no le persone che la usano |
| Vincoli d'accesso | Chi può vederla, e se contiene informazioni a visibilità differenziata |

Segnale d'allarme ricorrente: la sorgente più importante è spesso un foglio di calcolo
tenuto da una sola persona, e non compare in nessun inventario ufficiale.

## 2. Catalogo Obiettivi (dal bisogno alla richiesta dati)

| Campo | Che cosa registrare |
|---|---|
| Domanda di business | Formulata come la porrebbe chi decide |
| Chi la pone | Ruolo e livello decisionale (operativo, tattico, strategico) |
| Frequenza | Quante volte a settimana o a mese si presenta |
| Costo attuale | Quanto tempo e quante persone impegna oggi rispondere |
| Informazioni necessarie | Che cosa bisogna sapere per rispondere |
| Dati che le producono | Quali sorgenti del Catalogo Dati le contengono |
| Divario | Che cosa manca: il dato, la relazione, l'accesso o la classificazione |

La colonna "divario" è quella che orienta la proposta: se manca la classificazione, nessun
motore di ricerca risolve il problema.

## 3. Dimensioni della qualità del dato

Accuratezza, completezza, coerenza fra fonti, tempestività, unicità, validità rispetto al
dominio ammesso. Per ciascuna: come la si misurerebbe, e quale valore sarebbe accettabile.
La qualità non è una proprietà del dato, ma del processo che lo produce.

## 4. Registro di segregazione (materiale documentale)

Per ogni documento o unità informativa:

| Campo | Valori |
|---|---|
| Qualifica | Riservato · Condivisibile · Da valutare |
| Motivazione | Perché, in una riga verificabile |
| Vincolo | Eventuale limite (cliente, NDA, ambito temporale) |
| Chi ha qualificato | Persona e data |

Regole di condotta:
- il non ancora qualificato si tratta come **riservato**;
- "Da valutare" non è una qualifica finale: resta in coda di lavoro;
- la qualifica è rivedibile, e ogni revisione aggiorna autore e data;
- il registro è il primo nucleo della tassonomia di riservatezza e la base del futuro
  filtro sui permessi in fase di recupero.

## 5. Checklist di fattibilità per un livello semantico (RAG / LLMwiki)

Da percorrere **prima** di promettere un assistente che risponde. Ogni "no" è un pezzo di
lavoro da fare prima, non un ostacolo da aggirare.

1. I documenti sono in formati da cui si estrae testo, o esistono scansioni senza OCR?
2. Esiste una tassonomia condivisa delle tipologie documentali?
3. Ogni documento è riconducibile a un'entità del dominio (progetto, prodotto, cliente)?
4. È noto che cosa contengono i documenti dal punto di vista della riservatezza?
5. I permessi sono per documento o per informazione? Nel secondo caso, chi ha stabilito il
   confine interno ai documenti?
6. Il filtro sui permessi può essere applicato **prima** del recupero, e non a valle?
7. Esiste una versione ufficiale quando lo stesso contenuto compare più volte?
8. Con quale frequenza il materiale cambia, e chi manterrà l'indice allineato?
9. Le risposte devono essere tracciabili alla fonte? Con quale livello di citazione?
10. Quanto costa un errore: fastidio, ritardo, o danno contrattuale?
11. Chi valuta la qualità delle risposte, con quale campione e con quale periodicità?
12. Esistono vincoli aziendali all'uso di servizi esterni su questo materiale, e chi decide?

## 6. Criteri per scegliere il livello architetturale

| Se prevalgono | Il livello sufficiente è | Segnale che si sta esagerando |
|---|---|---|
| Ricerche esatte su entità note | Catalogo strutturato + navigazione | Si progetta un indice vettoriale per trovare un manuale per codice |
| Domande esplorative sui contenuti | Retrieval semantico con filtro sui permessi | Si indicizza materiale non ancora classificato |
| Confronti fra entità tecniche | Estrazione strutturata degli attributi | Si chiede a un modello di sintetizzare ciò che si poteva tabellare |
| Nulla di tutto ciò è chiaro | Razionalizzazione: inventario e classificazione | Si sceglie la tecnologia prima delle domande |
