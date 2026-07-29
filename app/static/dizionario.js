/* Builder del dizionario: mostra i campi del tipo scelto e gestisce la prova live. */

(function () {
  const selettoreTipo = document.getElementById("tipo");
  if (!selettoreTipo) return;

  function mostraCampiTipo() {
    document.querySelectorAll(".campi-tipo").forEach(function (blocco) {
      blocco.style.display = (blocco.dataset.tipo === selettoreTipo.value) ? "" : "none";
    });
  }
  selettoreTipo.addEventListener("change", mostraCampiTipo);
  mostraCampiTipo();

  function raccogliParametri() {
    const parametri = {};
    ["testo", "varianti", "etichetta", "prefisso", "blocco1_tipo", "blocco1_n",
     "separatore", "blocco2_tipo", "blocco2_n", "modello", "regex"].forEach(function (k) {
      const campo = document.getElementById("p_" + k);
      if (campo) parametri[k] = campo.value;
    });
    return parametri;
  }

  const btn = document.getElementById("btn-prova");
  btn.addEventListener("click", async function () {
    const esito = document.getElementById("esito-prova");
    const errore = document.getElementById("errore-prova");
    esito.style.display = "none";
    errore.style.display = "none";
    try {
      const risposta = await fetch(PROVA_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipo: selettoreTipo.value,
          parametri: raccogliParametri(),
          testo: document.getElementById("testo-prova").value
        })
      });
      const dati = await risposta.json();
      if (!dati.ok) {
        errore.textContent = dati.errore || "Errore nella costruzione della regola.";
        errore.style.display = "";
        return;
      }
      document.getElementById("prova-pattern").textContent = dati.pattern;
      document.getElementById("prova-conteggio").textContent =
        dati.n === 0 ? "Nessuna corrispondenza nel testo di esempio."
                     : (dati.n === 1 ? "1 corrispondenza trovata."
                                     : dati.n + " corrispondenze trovate.");
      document.getElementById("prova-evidenza").innerHTML =
        dati.html || "<em>(testo di esempio vuoto)</em>";
      esito.style.display = "";
    } catch (e) {
      errore.textContent = "Errore di comunicazione con il server locale: " + e;
      errore.style.display = "";
    }
  });
})();
