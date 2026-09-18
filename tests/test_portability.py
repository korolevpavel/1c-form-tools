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
from extract_form_modules import container_extract
from pack_form_modules import container_build

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
        (self.form / 'Module.bsl').write_bytes(b'\xef\xbb\xbf' + '// Оригинал\r\n'.encode('utf-8'))
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

    def test_real_commit_packs_case_variant_module_names(self):
        self.env['PYTHON'] = sys.executable
        self.git('rm', '--cached', '-r', 'Forms')
        (self.form / 'Module.bsl').unlink()
        for index, name in enumerate(['module.bsl', 'MODULE.BSL', 'mOdUlE.BsL']):
            with self.subTest(name=name):
                folder = self.repo / 'Forms' / str(index) / 'Ext'
                make_form(folder, '// Original\r\n')
                changed = b'\xef\xbb\xbf' + ('// ' + name + '\r\n').encode('utf-8')
                (folder / name).write_bytes(changed)
                self.git('add', str(folder.relative_to(self.repo)))
                self.git('commit', '-qm', 'Pack case variant')
                self.assertEqual(payloads(folder / 'Form.bin')['0/module'], changed)

    def test_incomplete_project_venv_does_not_fall_back(self):
        (self.tools / '.venv').mkdir()
        self.env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + self.env['PATH']
        before = (self.form / 'Form.bin').read_bytes()
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('project venv', result.stderr)
        self.assertEqual((self.form / 'Form.bin').read_bytes(), before)

    def test_broken_project_python_symlink_does_not_fall_back(self):
        folder = self.tools / '.venv/bin'
        folder.mkdir(parents=True)
        try:
            (folder / 'python').symlink_to(self.repo / 'deleted-python')
        except OSError as error:
            if os.name != 'nt':
                raise
            self.skipTest(f'Windows symlink privilege unavailable: {error}')
        self.env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + self.env['PATH']
        before = (self.form / 'Form.bin').read_bytes()
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('project venv', result.stderr)
        self.assertEqual((self.form / 'Form.bin').read_bytes(), before)

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
        selected = subprocess.run([self.bash, str(self.tools / 'run-python'), '-c',
            'import sys; print(sys.prefix)'], cwd=self.repo, env=self.env,
            capture_output=True, text=True, encoding='utf-8', check=True)
        self.assertEqual(Path(selected.stdout.strip()).resolve(), path.resolve())
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
