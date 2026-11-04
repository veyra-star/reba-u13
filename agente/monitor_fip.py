#!/usr/bin/env python3
"""Conservative FIP updater. Never invent a score; fail closed on unknown markup.

Usage: python scripts/update_fip.py [--fixture-html path]
Fixture mode permits testing an archived FIP HTML page without network access.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'calendario.json'
RESULTS = ROOT / 'risultati.json'
STATE = ROOT / 'stato.json'
BASE = 'https://fip.it/risultati/'
CODES = dict(zip('ABCDE', range(86095, 86100)))
PARAMS = dict(group='campionati-regionali', regione_codice='PI', comitato_codice='RPI', sesso='F', codice_campionato='U13/F', codice_fase='1')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; RebaU13Results/0.2; public sports results reader)'}


def url_for(group):
    return BASE + '?' + urlencode({**PARAMS, 'codice_girone': CODES[group]})


def parse_score(text):
    # Score pairs must be explicitly delimited, not dates or hours.
    m = re.fullmatch(r'\s*(\d{1,3})\s*[-–:]\s*(\d{1,3})\s*', text)
    if not m:
        return None
    a, b = map(int, m.groups())
    return [a, b] if a != b else None


def norm(text):
    return re.sub(r'[^A-Z0-9]', '', text.upper())


def extract(html, fixtures):
    """Extract a result from the unique FIP fixture ID, independent of sponsors.

    The ID anchors the record; the score must be immediately before the
    match date/time and each score must follow a recognizable team name.
    """
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    results = {}
    date_time = re.compile(
        r'\s+\d{1,2}\s+[A-Za-zÀ-ÿ]+\s+\d{4}\s+\d{1,2}:\d{2}\s*$',
        re.I,
    )

    def significant_tokens(name):
        return [t for t in re.findall(r'[A-Z0-9]+', name.upper())
                if len(t) >= 3 and t not in {'ASD', 'SSD', 'SSDRL', 'BASKET', 'POLISPORTIVA'}]

    def team_matches(label, name):
        normalized = norm(label)
        tokens = significant_tokens(name)
        return bool(tokens) and sum(t in normalized for t in tokens) >= max(1, len(tokens) - 1)

    for game in fixtures:
        ident = re.escape(str(int(game['id'])))
        candidates = set()
        for marker in re.finditer(rf'(?<!\d)0*{ident}(?!\d)', text):
            prefix = text[max(0, marker.start() - 250):marker.start()]
            date = date_time.search(prefix)
            if not date:
                continue
            body = prefix[:date.start()]
            # The away score is the last number immediately before the date.
            away_score = re.search(r'\s+(\d{1,3})\s*$', body)
            if not away_score:
                continue
            before_away = body[:away_score.start()]
            # Identify the home score, allowing a sponsor or suffix in the
            # FIP club names. A club number (e.g. 2020) is not a score.
            for home_score in re.finditer(r'\s+(\d{1,3})\s+', before_away):
                home_label = before_away[max(0, home_score.start() - 110):home_score.start()]
                away_label = before_away[home_score.end():]
                if not team_matches(home_label, game['casa']):
                    continue
                if not team_matches(away_label, game['trasferta']):
                    continue
                score = (int(home_score.group(1)), int(away_score.group(1)))
                if score[0] != score[1]:
                    candidates.add(score)
        if len(candidates) == 1:
            results[game['id']] = list(next(iter(candidates)))
            print(f'FIP game {game["id"]}: {results[game["id"]]}')
        elif len(candidates) > 1:
            print(f'WARNING: conflicting scores for game {game["id"]}: {sorted(candidates)}')
        elif re.search(rf'(?<!\d)0*{ident}(?!\d)', text):
            print(f'WARNING: game {game["id"]} present but no verified score')
    return results


def main():
    fixtures = json.loads(DATA.read_text(encoding='utf-8'))['partite']
    old = json.loads(RESULTS.read_text(encoding='utf-8'))
    state = json.loads(STATE.read_text(encoding='utf-8'))
    updates = {}
    errors = []
    checked_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    diagnostics = {}
    for group in CODES:
        try:
            resp = requests.get(url_for(group), headers=HEADERS, timeout=25)
            resp.raise_for_status()
            if len(resp.content) < 1000:
                raise ValueError('Risposta FIP troppo breve')
            group_games = [p for p in fixtures if p['girone'] == group]
            text = BeautifulSoup(resp.text, 'html.parser').get_text(' ', strip=True)
            if not any(re.search(rf'(?<!\\d)0*{re.escape(str(int(p["id"])))}(?!\\d)', text) for p in group_games):
                raise ValueError('Nessun codice partita noto trovato')
            # Diagnostica limitata ai codici gara noti: non salva HTML completo.
            snippets = []
            for game in group_games:
                game_id = str(int(game['id']))
                match = re.search(r'(?<!\\d)0*' + re.escape(game_id) + r'(?!\\d)', text)
                if match:
                    snippets.append({'id': game_id, 'contesto': text[max(0,match.start()-180):match.end()+35]})
                if len(snippets) >= 4:
                    break
            diagnostics[group] = {'lunghezza':len(text),'codici_trovati':len(snippets),'esempi':snippets}
            print('DIAGNOSTICA FIP', group, json.dumps({'lunghezza':len(text),'codici_trovati':len(snippets),'esempi':snippets}, ensure_ascii=False))
            updates.update({str(k):v for k,v in extract(resp.text, group_games).items()})
            print(f'Girone {group}: HTTP {resp.status_code}')
        except (requests.RequestException, ValueError) as exc:
            errors.append(f'{group}: {exc}')
    if not errors and not updates:
        errors.append('Nessun punteggio riconosciuto: verifica non valida')
    (ROOT / 'diagnostica.json').write_text(json.dumps({'tentativo_utc':checked_at,'gironi':diagnostics,'errori':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    state['ultimo_tentativo_utc'] = checked_at
    state['errori'] = errors
    if errors:
        state['esito'] = 'errore'
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('FIP verification failed: ' + '; '.join(errors), file=sys.stderr)
        return 1
    previous = old.get('partite', {})
    changed = 0
    for game in fixtures:
        score = updates.get(str(game['id']))
        if score is None:
            continue
        key = str(game['id'])
        entry = {**game, 'risultato': score}
        if previous.get(key) != entry:
            previous[key] = entry
            changed += 1
    RESULTS.write_text(json.dumps({'fonte':'FIP Piemonte - monitor indipendente', 'partite':previous}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    state.update({'esito':'ok','ultimo_controllo_riuscito_utc':checked_at,'nuovi_o_modificati':changed,'totale_risultati':len(previous)})
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Verifica riuscita: {len(updates)} punteggi verificati, {changed} modifiche')
    return 0

if __name__ == '__main__':
    sys.exit(main())
