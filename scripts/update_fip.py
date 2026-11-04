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


def url_for(group, ar, giornata):
    return BASE + '?' + urlencode({**PARAMS, 'codice_girone': CODES[group], 'codice_ar': ar, 'giornata': giornata})


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
        today = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).date()
        for group in CODES:
            fixtures = [p for p in db['partite'] if p['girone'] == group]
            rounds = {}
            for game in fixtures:
                m = re.fullmatch(r'(\d+)\s+(andata|ritorno)', game['giornata'], re.I)
                if not m:
                    errors.append(f'{group}: giornata sconosciuta per {game["id"]}')
                    continue
                if dt.datetime.strptime(game['data'], '%d/%m/%Y').date() <= today:
                    key = (1 if m.group(2).lower() == 'andata' else 0, int(m.group(1)))
                    rounds.setdefault(key, []).append(game)
            for (ar, giornata), selected in sorted(rounds.items()):
                try:
                    resp = requests.get(url_for(group, ar, giornata), headers=HEADERS, timeout=25)
                    resp.raise_for_status()
                    if len(resp.content) < 1000:
                        raise ValueError('Response too small for a results page')
                    page_text = BeautifulSoup(resp.text, 'html.parser').get_text(' ', strip=True)
                    if not any(re.search(r'(?<!\d)0*' + re.escape(str(int(p['id']))) + r'(?!\d)', page_text) for p in selected):
                        raise ValueError('No expected fixture IDs in round page')
                    parsed = extract(resp.text, selected)
                    for game_id, score in parsed.items():
                        if game_id in updates and updates[game_id] != score:
                            raise ValueError(f'Conflicting scores for {game_id}')
                        updates[game_id] = score
                    print(f'Girone {group}, giornata {giornata}, ar={ar}: HTTP {resp.status_code}; extracted {len(parsed)} scores')
                except (requests.RequestException, ValueError) as exc:
                    errors.append(f'{group} ar={ar} giornata={giornata}: {exc}')
        if not updates and today >= dt.date(2026, 10, 30):
            errors.append('Nessun punteggio verificato nelle giornate gia disputate')
    if errors:
        print('FIP request failed; leaving JSON unchanged:\n' + '\n'.join(errors), file=sys.stderr)
        return 1
    checked_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    changed = 0
    for game in db['partite']:
        score = updates.get(game['id'])
        if score is not None and game['risultato'] != score:
            game['risultato'] = score
            game['acquisito_il'] = checked_at
            changed += 1
    if changed:
        db['ultimo_aggiornamento_fip'] = checked_at
    # Only a successful live cycle across all five groups is a FIP check.
    # Offline fixture parsing must never advance this timestamp.
    if not args.fixture_html:
        db['ultimo_controllo_fip'] = checked_at
    if changed or not args.fixture_html:
        DATA.write_text(json.dumps(db, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'New/changed verified score pairs: {changed}. Unrecognized scores are not guessed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())