"""Synthetic containers only: no application code or proprietary form data."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

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


class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = os.environ.get('FORM_TOOLS_TEST_BASH') or shutil.which('bash')
        if not cls.bash:
            raise RuntimeError('Bash is required (Git Bash on Windows)')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='form tools ')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.tools = self.repo / '.1c-tools'
        self.tools.mkdir()
        for name in ['run-python', 'pack_form_modules.py', 'requirements.txt']:
            shutil.copy2(ROOT / name, self.tools / name)
        self.env = dict(os.environ)
        self.env.pop('PYTHON', None)
        self.env['PYTHONUTF8'] = '1'
        self.git('init', '-q')
        self.git('config', 'user.name', 'Form Tools Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.git('config', 'core.quotePath', 'true')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', '.git/hooks')
        shutil.copy2(ROOT / 'pre-commit', self.repo / '.git/hooks/pre-commit')
        (self.repo / '.git/hooks/pre-commit').chmod(0o755)
        self.form = self.repo / 'Forms/Тестовая форма/Ext'
        make_form(self.form, '// Оригинал\r\n')
        process_directory(str(self.form))
        self.git('add', 'Forms')

    def git(self, *args, check=True):
        return subprocess.run(['git', *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, encoding='utf-8', errors='replace', check=check)

    def hook(self):
        return subprocess.run([self.bash, str(ROOT / 'pre-commit')], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')

    def test_real_commit_packs_edited_module_with_spaces_and_cyrillic(self):
        self.env['PYTHON'] = sys.executable
        original = (self.form / 'Form.bin').read_bytes()
        changed = b'\xef\xbb\xbf' + '// Изменено\r\n'.encode('utf-8')
        (self.form / 'Module.bsl').write_bytes(changed)
        self.git('add', 'Forms')
        self.git('commit', '-qm', 'Pack test')
        self.assertNotEqual((self.form / 'Form.bin').read_bytes(), original)
        self.assertEqual(payloads(self.form / 'Form.bin')['0/module'], changed)
        self.assertEqual(self.git('status', '--porcelain', '--', 'Forms').stdout, '')

    def test_project_venv_without_activation(self):
        path = self.tools / '.venv'
        venv.EnvBuilder(with_pip=False, system_site_packages=True).create(path)
        # A nested venv does not inherit packages from the invoking venv.
        # Expose already-installed test dependencies without network access.
        python = path / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        site_dir = subprocess.check_output([str(python), '-c',
            'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip()
        import v8unpack
        import tqdm
        dependency_dirs = {str(Path(m.__file__).resolve().parent.parent) for m in (v8unpack, tqdm)}
        (Path(site_dir) / 'test-dependencies.pth').write_text('\n'.join(dependency_dirs) + '\n', encoding='utf-8')
        self.env.pop('VIRTUAL_ENV', None)
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_path_fallback(self):
        self.env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + self.env['PATH']
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_override_does_not_fall_back(self):
        self.env['PYTHON'] = str(self.repo / 'missing python')
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cannot run Python', result.stderr)
        self.assertNotIn('v8unpack is unavailable', result.stderr)

    def test_missing_dependency(self):
        path = self.repo / 'isolated python'
        venv.EnvBuilder(with_pip=False).create(path)
        self.env['PYTHON'] = str(path / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('v8unpack is unavailable', result.stderr)
        self.assertIn('-m pip install', result.stderr)

    def test_partial_staging_is_rejected_without_changing_binary(self):
        self.env['PYTHON'] = sys.executable
        before = (self.form / 'Form.bin').read_bytes()
        with (self.form / 'Module.bsl').open('ab') as stream:
            stream.write(b'// unstaged\r\n')
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Stage all changes', result.stderr)
        self.assertEqual((self.form / 'Form.bin').read_bytes(), before)

    def test_managed_form_does_not_require_python(self):
        self.git('rm', '--cached', '-r', 'Forms')
        managed = self.repo / 'Managed/Form/Module.bsl'
        managed.parent.mkdir(parents=True)
        managed.write_bytes(b'// managed')
        self.git('add', 'Managed')
        self.env['PYTHON'] = 'does-not-exist'
        self.assertEqual(self.hook().returncode, 0)


if __name__ == '__main__':
    unittest.main()
