# REBA U13F — Dashboard Piemonte 2026/27

Sito statico a pagina unica. Aprire con un server locale, ad esempio `python3 -m http.server 8000` dalla cartella, quindi visitare `http://localhost:8000`.

## Stato
- Layout e navigazione single-page: pronti.
- 25 squadre e calendario da PDF FIP del 23/10/2026: importazione iniziale. **Verificata e corretta nella v03**: 100 gare, 20 per girone e 8 per squadra, con coppie casa/trasferta univoche.
- Classifiche e play-in: calcolati dai punteggi nel JSON; le regole di parità e l'eleggibilità play-in necessitano verifica sui comunicati FIP.
- Risultati live: **non ancora collegati**. Nessun punteggio è inventato.
- Per pubblicare su GitHub Pages: caricare i file di questa cartella nella root di un repository pubblico, poi Settings > Pages > Deploy from branch > main / root.
- Per automatizzare: identificare endpoint/pagine FIP, verificare condizioni di accesso e creare una GitHub Action che aggiorni `data/campionato.json`.

## Formato risultati
Ogni partita contiene `risultato: null`. Quando disponibile, impostare `risultato: [puntiCasa, puntiOspiti]`.

## Release v03.2 — 24/10/2026
- Consolidato archivio v03 e confrontato lo script FIP con GitHub `veyra-star/reba-u13`, ramo `main`: SHA Git blob identico `8f4604f800e8c8e7f9d41a69ee1b77d7c827ec37`.
- Lo script FIP non e stato modificato: il parser rimane da validare su risultati reali.
- Il workflow `update-fip.yml` e presente in questa release, ma assente nel repository GitHub al momento della verifica: nessuna automazione live confermata.
- La versione web su GitHub NON e stata aggiornata da questa operazione.

## Release v03 — 24/10/2026
- Corrette le associazioni delle gare 8725, 8730 e 8738 nel girone D.
- Ripristinate le sei gare 8741, 8744, 8746, 8750, 8751 e 8755 del girone E.
- Integrato app.js aggiornato (Elo e simulazione completa) e nuovo logo.
- Controllo automatico di integrità del calendario all’avvio.
- La sincronizzazione FIP resta da validare prima di considerarla operativa.
