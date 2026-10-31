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

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/campionato.json'
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
    """Match only an unambiguous row containing both clubs AND an isolated score.

    Deliberately conservative until live HTML is inspected and parser validated.
    """
    soup = BeautifulSoup(html, 'html.parser')
    results = {}
    for row in soup.select('tr, .match-row, .risultato, .partita, .gara'):
        text = row.get_text(' ', strip=True)
        if not text:
            continue
        matched = [p for p in fixtures if norm(p['casa']) in norm(text) and norm(p['trasferta']) in norm(text)]
        if len(matched) != 1:
            continue
        # Require score in its own element; avoid interpreting calendar dates.
        candidates = []
        for el in row.select('td, .score, .punteggio, .risultato, strong'):
            score = parse_score(el.get_text(' ', strip=True))
            if score and score not in candidates:
                candidates.append(score)
        if len(candidates) == 1:
            results[matched[0]['id']] = candidates[0]
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture-html', type=Path, help='Use saved HTML of girone C to validate parsing offline')
    args = parser.parse_args()
    db = json.loads(DATA.read_text(encoding='utf-8'))
    updates = {}
    errors = []
    if args.fixture_html:
        html = args.fixture_html.read_text(encoding='utf-8')
        updates.update(extract(html, [p for p in db['partite'] if p['girone'] == 'C']))
    else:
        for group in CODES:
            try:
                resp = requests.get(url_for(group), headers=HEADERS, timeout=25)
                resp.raise_for_status()
                if len(resp.content) < 1000:
                    raise ValueError('Response too small for a results page')
                parsed = extract(resp.text, [p for p in db['partite'] if p['girone'] == group])
                updates.update(parsed)
                if not parsed and group == 'C':
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    print('DIAGNOSTICA FIP C: titolo=', soup.title.get_text(' ', strip=True) if soup.title else '(nessuno)')
                    print('DIAGNOSTICA FIP C: testo=', soup.get_text(' ', strip=True)[:1800])
                    print('DIAGNOSTICA FIP C: selettori=', {k: len(soup.select(k)) for k in ['tr', 'table', '.match-row', '.risultato', '.partita', '.gara', 'script']})
                print(f'Girone {group}: HTTP {resp.status_code}; extracted {len(parsed)} scores')
            except (requests.RequestException, ValueError) as exc:
                errors.append(f'{group}: {exc}')
    if not errors and not updates and dt.datetime.now(dt.timezone.utc).date() >= dt.date(2026, 10, 30):
        errors.append('Nessun punteggio riconosciuto dopo l avvio del campionato: verificare struttura FIP e parser')
    if errors:
        print('FIP request failed; leaving JSON unchanged:\n' + '\n'.join(errors), file=sys.stderr)
        return 1
    changed = 0
    for game in db['partite']:
        score = updates.get(game['id'])
        if score is not None and game['risultato'] != score:
            game['risultato'] = score
            changed += 1
    # A successful request is not proof that markup was parsed correctly.
    # Keep explicit validation status until real published scores are observed.
    if changed:
        db['ultimo_aggiornamento_fip'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        DATA.write_text(json.dumps(db, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'New/changed verified score pairs: {changed}. Unrecognized scores are not guessed.')
    # Trigger diagnostic refresh on script changes.
    return 0


if __name__ == '__main__':
    sys.exit(main())