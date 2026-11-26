import unittest
from pathlib import Path
from unittest.mock import patch

from crawler import scrape


class CrawlerTests(unittest.TestCase):
    def test_exclusions_match_whole_words_and_literal_phrases(self):
        terms = ('Calamity', 'Super Mod', 'Mod+')
        for title in ('Betsy (cAlAmItY)', 'A Super Mod guide', 'Mod+ (guide)'):
            with self.subTest(title=title):
                self.assertTrue(scrape._is_excluded(title, terms))
        for title in ('Supercalamity', 'Calamityblade', 'Super Modded', 'Mod guide'):
            with self.subTest(title=title):
                self.assertFalse(scrape._is_excluded(title, terms))

    def test_invalid_config_is_rejected(self):
        cases = ('[anything]', 'categories: [', 'categories: {bosses: null}',
                 'categories: {../outside: "Category:Boss NPCs"}',
                 'categories: {bosses: "Category:Boss NPCs"}\nexclude_title_terms: false',
                 'categories: {bosses: "Category:Boss NPCs"}\nexclude_title_terms: [""]')
        for contents in cases:
            with self.subTest(contents=contents), patch.object(Path, 'read_text', return_value=contents):
                with self.assertRaisesRegex(SystemExit, 'categories.yaml'):
                    scrape.load_config()

    def test_pagination_forwards_cursor_and_stops_at_limit(self):
        calls = []

        def response(params, context=''):
            calls.append(params.copy())
            if len(calls) == 1:
                return {
                    'query': {'categorymembers': [{'title': f'Boss {i}'} for i in range(20)]},
                    'continue': {'continue': '-||', 'cmcontinue': 'next-page'},
                }
            return {'query': {'categorymembers': [{'title': 'Betsy'}, {'title': 'Unused'}]}}

        with patch.object(scrape, 'request_api', side_effect=response):
            titles = scrape.list_category_members('Category:Boss NPCs', 21)
        self.assertEqual(titles, [f'Boss {i}' for i in range(20)] + ['Betsy'])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]['cmlimit'], 20)
        self.assertEqual(calls[1], {**calls[0], 'continue': '-||', 'cmcontinue': 'next-page'})


if __name__ == '__main__':
    unittest.main()
