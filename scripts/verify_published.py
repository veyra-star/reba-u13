#!/usr/bin/env python3
"""Verify scores actually served by GitHub Pages after a data commit."""
import argparse
import json
import time
from pathlib import Path
import requests


def compare(expected, actual):
    live = {str(g['id']): g.get('risultato') for g in actual['partite']}
    return [str(g['id']) for g in expected['partite']
            if live.get(str(g['id'])) != g.get('risultato')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempts', type=int, default=18)
    args = parser.parse_args()
    expected = json.loads((Path(__file__).resolve().parents[1] / 'data/campionato.json').read_text())
    for attempt in range(args.attempts):
        try:
            r = requests.get('https://veyra-star.github.io/reba-u13/data/campionato.json',
                             params={'verification': time.time_ns()},
                             headers={'Cache-Control': 'no-cache'}, timeout=20)
            r.raise_for_status()
            missing = compare(expected, r.json())
            if not missing:
                print('Pubblicazione verificata: tutti i punteggi coincidono con il sito.')
                return 0
            print('Pubblicazione non ancora allineata: ' + ', '.join(missing))
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            print(f'Pubblicazione non verificabile: {exc}')
        if attempt + 1 < args.attempts:
            time.sleep(10)
    print('ERRORE: dati GitHub salvati, pubblicazione del sito non confermata.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
