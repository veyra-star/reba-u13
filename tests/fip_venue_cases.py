"""Venue scope, official Info parsing, correction and failure regression tests."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import Mock
from bs4 import BeautifulSoup
import requests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('updater', ROOT / 'scripts/update_fip.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
HTML = (ROOT / 'tests/fixtures/fip-d-andata-3.html').read_text()
GAMES = json.loads((ROOT / 'data/campionato.json').read_text())['partite']
# Start with calendar inputs, independent of venues already synchronized on disk.
for game in GAMES:
    game.pop('campo_gioco', None)
GAME = copy.deepcopy(next(g for g in GAMES if g['id'] == '8726'))


class VenueTests(unittest.TestCase):
    def extract(self, html=HTML, game=None):
        return u.extract_venues(str(html), [game or GAME])

    def test_verified_saluggia_info(self):
        venue = self.extract()['8726']
        self.assertEqual(venue['nome'], 'Palazzetto Comunale')
        self.assertEqual(venue['indirizzo'], 'Via Ponte Rocca 4 13040 SALUGGIA (VC)')
        self.assertIn('query=Via+Ponte+Rocca+4+13040+SALUGGIA+%28VC%29', venue['maps_url'])

    def test_scope_excludes_other_games_and_bianco_alone(self):
        result = u.extract_venues(HTML, GAMES)
        self.assertEqual(set(result), {'8726'})
        for fields in ({'girone': 'C'}, {'trasferta': 'POLISPORTIVA REBA BIANCO'}, {'id': '18726'},
                       {'casa': GAME['trasferta'], 'trasferta': GAME['casa']}):
            self.assertEqual(self.extract(game={**GAME, **fields}), {})

    def test_missing_invalid_or_wrong_label_preserves_previous(self):
        for replacement in ('', 'Da definire', 'Palazzetto, Via Ponte Rocca 4', 'Palazzetto, 13040'):
            soup = BeautifulSoup(HTML, 'html.parser')
            for label in soup.select('.label'):
                if label.get_text(strip=True) == 'Campo di gioco':
                    label.parent.select_one('.value').string = replacement
            self.assertEqual(self.extract(soup), {})
        self.assertEqual(self.extract(HTML.replace('Campo di gioco', 'Arbitro')), {})

    def test_duplicates_and_conflicts(self):
        self.assertEqual(self.extract(HTML + HTML), self.extract())
        self.assertEqual(self.extract(HTML + HTML.replace('Via Ponte Rocca 4', 'Via Nuova 9')), {})
        self.assertEqual(self.extract(HTML + HTML.replace('Via Ponte Rocca 4', '')), {})

    def test_update_correction_idempotency_and_unrelated_fields(self):
        db = {'partite': [copy.deepcopy(GAME)], 'ultimo_controllo_fip': 'previous'}
        fetch = Mock(return_value=Mock(text=HTML))
        self.assertEqual(u.refresh_venues(db, fetch), (1, []))
        first = copy.deepcopy(db)
        self.assertEqual(u.refresh_venues(db, fetch), (0, []))
        self.assertEqual(db, first)
        fetch.return_value.text = HTML.replace('Via Ponte Rocca 4', 'Via Nuova 9')
        self.assertEqual(u.refresh_venues(db, fetch), (1, []))
        self.assertIn('Via Nuova 9', db['partite'][0]['campo_gioco']['indirizzo'])
        self.assertEqual({k:v for k,v in db['partite'][0].items() if k != 'campo_gioco'}, GAME)
        self.assertEqual(db['ultimo_controllo_fip'], 'previous')
        previous = copy.deepcopy(db)
        fetch.side_effect = requests.Timeout('unavailable')
        changed, errors = u.refresh_venues(db, fetch)
        self.assertEqual(changed, 0)
        self.assertTrue(errors)
        self.assertEqual(db, previous)

    def test_refresh_covers_all_eight_rounds_including_future(self):
        db = {'partite': copy.deepcopy(GAMES)}
        fetch = Mock(return_value=Mock(text=HTML))
        u.refresh_venues(db, fetch)
        self.assertEqual(fetch.call_count, 8)
        self.assertTrue(any('codice_ar=0' in call.args[0] for call in fetch.call_args_list))
        self.assertTrue(all('codice_girone=86098' in call.args[0] for call in fetch.call_args_list))
        self.assertEqual([g['id'] for g in db['partite'] if 'campo_gioco' in g], ['8726'])


if __name__ == '__main__':
    unittest.main()
