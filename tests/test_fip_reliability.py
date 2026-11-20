"""Retries, incomplete checks, unchanged data on failure and publication checks."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fip_common as common
import verify_published as publication


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UPDATER = load('reliability_updater', 'scripts/update_fip.py')
MONITOR = load('reliability_monitor', 'agente/monitor_fip.py')
HTML = (ROOT / 'tests/fixtures/fip-c-andata-2.html').read_text()
GAMES = [g for g in json.loads((ROOT / 'agente/calendario.json').read_text())['partite']
         if g['id'] in {'8703', '8704'}]


def response(html=HTML):
    return Mock(text=html, content=html.encode(), url='https://fip.it/risultati/')


class ReliabilityTests(unittest.TestCase):
    def test_transient_failure_retried(self):
        valid = response()
        with patch.object(common.requests, 'get', side_effect=[requests.Timeout(), valid]) as get, patch.object(common.time, 'sleep'):
            self.assertIs(common.fetch_page('url', {}), valid)
            self.assertEqual(get.call_count, 2)

    def test_incomplete_page_retried_then_validated(self):
        with patch.object(common.requests, 'get', side_effect=[response('bad'), response()]) as get, patch.object(common.time, 'sleep'):
            common.fetch_page('url', {}, lambda html: common.verify_round(html, GAMES, UPDATER.extract))
            self.assertEqual(get.call_count, 2)

    def test_retry_limit_and_failed_validation(self):
        with patch.object(common.requests, 'get', return_value=response()) as get, patch.object(common.time, 'sleep'):
            with self.assertRaisesRegex(ValueError, 'Codici gara assenti'):
                common.fetch_page('url', {}, lambda html: common.verify_round(html, [{**GAMES[0], 'id': '9999'}], UPDATER.extract))
            self.assertEqual(get.call_count, 3)

    def test_unpublished_points_allowed_but_published_unreadable_rejected(self):
        soup = BeautifulSoup(HTML, 'html.parser')
        for p in soup.select('.team__points'):
            p.string = ''
        self.assertEqual(common.verify_round(str(soup), GAMES, UPDATER.extract), {})
        soup.select_one('.team__points').string = 'unknown'
        with self.assertRaisesRegex(ValueError, 'pubblicato ma non verificabile'):
            common.verify_round(str(soup), GAMES, UPDATER.extract)

    def test_partial_check_keeps_previous_results_and_success_time(self):
        for module in (UPDATER, MONITOR):
            with self.subTest(reader=module.__name__), tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                root = Path(tmp)
                games = [{**g, 'data': '01/01/2020', 'risultato': None} for g in GAMES]
                games += [{**games[0], 'id': '9999', 'giornata': '3 andata'}]
                data = root / 'campionato.json'
                data.write_text(json.dumps({'partite': games, 'ultimo_controllo_fip': 'old-success'}))
                result = root / 'risultati.json'
                result.write_text(json.dumps({'partite': {'old': {'risultato': [7, 9]}}}))
                status = root / ('fip-stato.json' if module is UPDATER else 'stato.json')
                status.write_text(json.dumps({'ultimo_controllo_riuscito_utc': 'old-success'}))
                original_data, original_result = data.read_text(), result.read_text()
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(module, 'DATA', data))
                    stack.enter_context(patch.object(module, 'CODES', {'C': 86097}))
                    stack.enter_context(patch.object(module, 'fetch_page', side_effect=[response(), requests.Timeout('FIP unavailable')]))
                    stack.enter_context(patch('sys.argv', ['reader']))
                    if module is MONITOR:
                        stack.enter_context(patch.object(module, 'ROOT', root))
                        stack.enter_context(patch.object(module, 'RESULTS', result))
                        stack.enter_context(patch.object(module, 'STATE', status))
                    self.assertEqual(module.main(), 1)
                state = json.loads(status.read_text())
                self.assertEqual(state['esito'], 'parziale')
                self.assertEqual(state['giornate_attese'], 2)
                self.assertEqual(state['giornate_verificate'], 1)
                self.assertEqual(state['ultimo_controllo_riuscito_utc'], 'old-success')
                self.assertTrue(state['errori'])
                self.assertEqual(data.read_text(), original_data)
                self.assertEqual(result.read_text(), original_result)

    def test_complete_check_saves_verified_scores_and_success(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            data = Path(tmp) / 'campionato.json'
            games = [{**g, 'data': '01/01/2020', 'risultato': None} for g in GAMES]
            data.write_text(json.dumps({'partite': games}))
            with patch.object(UPDATER, 'DATA', data), patch.object(UPDATER, 'CODES', {'C': 86097}), patch.object(UPDATER, 'fetch_page', return_value=response()), patch.object(UPDATER, 'refresh_venues', return_value=(0, [])), patch('sys.argv', ['reader']):
                self.assertEqual(UPDATER.main(), 0)
            state = json.loads(data.with_name('fip-stato.json').read_text())
            self.assertEqual(state['esito'], 'ok')
            self.assertEqual(state['giornate_verificate'], state['giornate_attese'])
            self.assertIn('ultimo_controllo_riuscito_utc', state)
            self.assertEqual({g['id']: g['risultato'] for g in json.loads(data.read_text())['partite']}, {'8703': [6, 103], '8704': [69, 26]})

    def test_publication_detects_missing_and_wrong_scores(self):
        expected = {'partite': [{'id': '8703', 'risultato': [6, 103]}]}
        self.assertEqual(publication.compare(expected, expected), [])
        self.assertEqual(publication.compare(expected, {'partite': []}), ['8703'])
        self.assertEqual(publication.compare(expected, {'partite': [{'id': '8703', 'risultato': [22, 103]}]}), ['8703'])

    def test_workflows_never_skip_for_delayed_clock(self):
        for name in ('update.yml', 'agente-fip.yml'):
            source = (ROOT / '.github/workflows' / name).read_text()
            self.assertNotIn('local_time', source)
            self.assertNotIn('local.hour', source)
            self.assertIn('group: reba-fip-writes', source)
            self.assertIn('steps.check.outcome', source)


if __name__ == '__main__':
    unittest.main()
