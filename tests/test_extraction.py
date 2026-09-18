"""Synthetic containers only: no application code or proprietary form data."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_form_modules import process_directory, container_extract
from pack_form_modules import container_build, pack_module_into_bin

ROOT = Path(__file__).resolve().parents[1]


def make_form(folder, text):
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        payload = Path(temp) / '0'
        payload.mkdir()
        (payload / 'module').write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
        (payload / 'form').write_bytes(b'layout-fixture-must-not-change')
        container_build(temp, str(folder / 'Form.bin'), True)


def payloads(binary):
    with tempfile.TemporaryDirectory() as temp:
        container_extract(str(binary), temp, False, True)
        return {p.relative_to(temp).as_posix(): p.read_bytes()
                for p in Path(temp).rglob('*') if p.is_file()}


class ExtractionTests(unittest.TestCase):
    def test_line_endings_bom_and_repeated_round_trip(self):
        for original in ['А\r\nБ\r\n', 'А\nБ\n', 'А\r\nБ\nВ\rГ', '', 'Без перевода']:
            with self.subTest(text=repr(original)), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                make_form(folder, original)
                before = payloads(folder / 'Form.bin')
                expected = b'\xef\xbb\xbf' + original.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n').encode('utf-8')
                for _ in range(2):
                    self.assertEqual(process_directory(str(folder), force=True)['errors'], 0)
                    actual = (folder / 'Module.bsl').read_bytes()
                    self.assertEqual(actual, expected)
                    self.assertNotIn(b'\r\r\n', actual)
                    self.assertEqual(actual.count(b'\xef\xbb\xbf'), 1)
                    self.assertTrue(pack_module_into_bin(str(folder / 'Form.bin'), str(folder / 'Module.bsl')))
                    after = payloads(folder / 'Form.bin')
                    self.assertEqual(after['0/module'], expected)
                    self.assertEqual(after['0/form'], before['0/form'])


if __name__ == '__main__':
    unittest.main()
