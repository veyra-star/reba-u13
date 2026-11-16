"""Regression coverage for both entry points using official FIP match cards."""
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'tests/fixtures/fip-c-andata-2.html').read_text()
FIXTURES = [g for g in json.loads((ROOT / 'agente/calendario.json').read_text())['partite']
            if g['id'] in {'8703', '8704'}]
MODULES = []
for path in ('scripts/update_fip.py', 'agente/monitor_fip.py'):
    spec = importlib.util.spec_from_file_location(path, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    MODULES.append(module)


def card(soup, ident='008703'):
    return next(c for c in soup.select('.results-matches__match')
                if c.select_one('.ref').get_text(strip=True) == ident)


class FipParserTests(unittest.TestCase):
    def check(self, html, expected, fixtures=FIXTURES):
        for module in MODULES:
            with self.subTest(entry=module.__name__), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.extract(str(html), fixtures), expected)

    def test_official_results_and_numeric_club_names(self):
        self.check(HTML, {'8703': [6, 103], '8704': [69, 26]})

    def test_missing_or_invalid_score_is_not_inferred(self):
        for value in ('', '-', 'rinviata', '15:00', '6 22', '1000', '-6'):
            with self.subTest(value=value):
                soup = BeautifulSoup(HTML, 'html.parser')
                card(soup).select_one('.team__points').string = value
                self.check(soup, {'8704': [69, 26]})

    def test_missing_score_field(self):
        soup = BeautifulSoup(HTML, 'html.parser')
        card(soup).select_one('.team__points').decompose()
        self.check(soup, {'8704': [69, 26]})

    def test_zero_score_and_unplayed_tie(self):
        soup = BeautifulSoup(HTML, 'html.parser')
        points = card(soup).select('.team__points')
        points[0].string = '0'
        self.check(soup, {'8703': [0, 103], '8704': [69, 26]})
        points[1].string = '0'
        self.check(soup, {'8704': [69, 26]})

    def test_conflicting_duplicate_id(self):
        soup = BeautifulSoup(HTML, 'html.parser')
        duplicate = copy.deepcopy(card(soup))
        duplicate.select_one('.team__points').string = '22'
        soup.append(duplicate)
        self.check(soup, {'8704': [69, 26]})

    def test_identical_duplicate_card(self):
        self.check(HTML + HTML, {'8703': [6, 103], '8704': [69, 26]})

    def test_wrong_id_and_reversed_teams(self):
        soup = BeautifulSoup(HTML, 'html.parser')
        card(soup).select_one('.ref').string = '18703'
        self.check(soup, {'8704': [69, 26]})
        soup = BeautifulSoup(HTML, 'html.parser')
        names = card(soup).select('.team__name')
        names[0].string, names[1].string = 'LAPOLISMILE', 'LETTERA 22 A.S.D.'
        self.check(soup, {'8704': [69, 26]})

    def test_sponsor_and_whitespace(self):
        soup = BeautifulSoup(HTML, 'html.parser')
        card(soup).select_one('.team__name').string = 'SPONSOR LETTERA 22 A.S.D.'
        card(soup).select_one('.team__points').string = '\n 6 \t'
        self.check(soup, {'8703': [6, 103], '8704': [69, 26]})

    def test_flat_text_is_not_a_score_source(self):
        text = BeautifulSoup(HTML, 'html.parser').get_text(' ', strip=True)
        self.check('<p>' + text + '</p>', {})

    def test_updater_offline_persists_results_without_claiming_live_check(self):
        updater = MODULES[0]
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data.json'
            db = {'partite': [{**g, 'risultato': None} for g in FIXTURES],
                  'ultimo_controllo_fip': 'previous-live-check'}
            data.write_text(json.dumps(db))
            argv = ['update_fip.py', '--fixture-html', str(ROOT / 'tests/fixtures/fip-c-andata-2.html')]
            with patch.object(updater, 'DATA', data), patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(updater.main(), 0)
                first = data.read_text()
                self.assertEqual(updater.main(), 0)
                self.assertEqual(first, data.read_text())
            result = json.loads(first)
            self.assertEqual(result['ultimo_controllo_fip'], 'previous-live-check')
            self.assertEqual({g['id']: g['risultato'] for g in result['partite']},
                             {'8703': [6, 103], '8704': [69, 26]})


if __name__ == '__main__':
    unittest.main()
