"""Network and completeness checks shared by the two FIP readers."""
import re
import time

import requests
from bs4 import BeautifulSoup


def fetch_page(url, headers, validate=None, attempts=3):
    """Retry transient HTTP errors and incomplete pages, never guess results."""
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            if len(response.content) < 1000:
                raise ValueError('Risposta FIP troppo breve')
            if validate:
                validate(response.text)
            return response
        except (requests.RequestException, ValueError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)


def verify_round(html, games, extract):
    """Require every selected fixture and reject published but unreadable points."""
    cards = {}
    for card in BeautifulSoup(html, 'html.parser').select('.results-matches__match'):
        refs = card.select('.results-matches__match__info .ref')
        if len(refs) == 1 and re.fullmatch(r'[0-9]+', refs[0].get_text(strip=True)):
            cards.setdefault(int(refs[0].get_text(strip=True)), []).append(card)
    missing = [str(g['id']) for g in games if int(g['id']) not in cards]
    if missing:
        raise ValueError('Codici gara assenti: ' + ', '.join(missing))
    parsed = extract(html, games)
    for game in games:
        for card in cards[int(game['id'])]:
            points = card.select('.teams > .team .team__points')
            values = [p.get_text(strip=True) for p in points]
            # Two empty cells mean the federation has not published a result.
            if len(values) != 2:
                raise ValueError(f'Campi punteggio non riconosciuti: {game["id"]}')
            if any(values) and game['id'] not in parsed:
                raise ValueError(f'Punteggio pubblicato ma non verificabile: {game["id"]}')
    return parsed
