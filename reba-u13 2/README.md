# REBA U13F — Dashboard Piemonte 2026/27

Sito statico a pagina unica. Aprire con un server locale, ad esempio `python3 -m http.server 8000` dalla cartella, quindi visitare `http://localhost:8000`.

## Stato
- Layout e navigazione single-page: pronti.
- 25 squadre e calendario da PDF FIP del 23/10/2026: importazione iniziale. **Da verificare: sei gare del girone E non sono state riconosciute dall'estrazione testuale automatica**. Gli altri quattro gironi contano 20 gare ciascuno.
- Classifiche e play-in: calcolati dai punteggi nel JSON; le regole di parità e l'eleggibilità play-in necessitano verifica sui comunicati FIP.
- Risultati live: **non ancora collegati**. Nessun punteggio è inventato.
- Per pubblicare su GitHub Pages: caricare i file di questa cartella nella root di un repository pubblico, poi Settings > Pages > Deploy from branch > main / root.
- Per automatizzare: identificare endpoint/pagine FIP, verificare condizioni di accesso e creare una GitHub Action che aggiorni `data/campionato.json`.

## Formato risultati
Ogni partita contiene `risultato: null`. Quando disponibile, impostare `risultato: [puntiCasa, puntiOspiti]`.
