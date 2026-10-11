"""Publication must preserve a private draft until all evidence is verified."""
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / 'scripts/publish-release.py'
SPEC = importlib.util.spec_from_file_location('release_publication', SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = pathlib.Path(self.work.name)
        self.commit = 'a' * 40
        self.manifest = dict(schema=1, source_commit=self.commit,
                             sdk=dict(version='10.11.7108'), opend=dict(version='10.11.7108'),
                             release_tag='build-' + self.commit[:12] + '-sdk10.11.7108-opend10.11.7108')
        self.write('resolved-build.json', self.manifest)
        for client, prefix in zip(release.CLIENTS, ('python', 'swift-cpp')):
            image = self.root / (client + '-macos-arm64.dmg')
            image.write_bytes(b'x' * 4096 + b'koly' + b'\0' * 508)
            self.write(image.with_suffix('.validation.json').name,
                       dict(schema=1, file=image.name, size_bytes=image.stat().st_size,
                            sha256=release.digest(image), source_commit=self.commit,
                            sdk_version='10.11.7108', opend_version='10.11.7108',
                            mounted_verified=True, applications_link_verified=True,
                            client_signature_verified=True, official_opend_signature_verified=True))
            self.write(prefix + '-build.json', dict(app=client + '.app', architecture='arm64',
                       commit=self.commit, sdk_version='10.11.7108', opend_version='10.11.7108'))
            self.write(prefix + '-opend-smoke.json', dict(version='10.11.7108',
                       official_signature_verified=True, updater_bootstrap_verified=True,
                       official_gui_alive_seconds=5))
        self.calls = []
        self.assets = []
        self.env = patch.dict(os.environ, GITHUB_REPOSITORY='charzl/moomoo-clients')
        self.env.start()
        self.addCleanup(self.env.stop)

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data))

    def change(self, name, **values):
        data = json.loads((self.root / name).read_text())
        self.write(name, dict(data, **values))

    def gh(self, *args):
        self.calls.append(args)
        if args[0] == 'api':
            raise subprocess.CalledProcessError(1, args, stderr='HTTP 404 Not Found')
        if args[:2] == ('release', 'upload'):
            self.assets = [dict(name=pathlib.Path(p).name, size=pathlib.Path(p).stat().st_size)
                           for p in args[3:-1]]
        if args[:2] == ('release', 'view'):
            return json.dumps(dict(assets=self.assets)) if 'assets' in args else 'https://example.org/release'
        return ''

    def publish(self, call=None):
        return release.publish(self.root, self.commit, call or self.gh, min_bytes=1024)

    def test_python_preflight_without_performance_reports(self):
        manifest, files = release.preflight(self.root, self.commit, min_bytes=1024)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(len(files), 1)

    def test_actions_preserved_directory_layout_is_normalized(self):
        nested = self.root/'apps/python/dist'
        nested.mkdir(parents=True)
        for path in list(self.root.iterdir()):
            if path.is_file(): path.rename(nested/path.name)
        target = release.collect_artifacts(self.root)
        try:
            manifest, images = release.preflight(target, self.commit, min_bytes=1024)
            self.assertEqual(manifest, self.manifest)
            self.assertEqual(len(images), 1)
            self.assertTrue((nested/'resolved-build.json').exists())
        finally:
            import shutil
            shutil.rmtree(target)

    def test_identical_manifest_copies_are_accepted(self):
        nested = self.root/'artifacts'; nested.mkdir()
        (nested/'resolved-build.json').write_bytes((self.root/'resolved-build.json').read_bytes())
        target = release.collect_artifacts(self.root)
        try:
            release.preflight(target, self.commit, min_bytes=1024)
        finally:
            import shutil
            shutil.rmtree(target)

    def test_conflicting_artifacts_rejected(self):
        nested = self.root/'duplicate'; nested.mkdir()
        (nested/'resolved-build.json').write_text(json.dumps(dict(self.manifest, source_commit='b'*40)))
        with self.assertRaisesRegex(RuntimeError, 'Conflicting'):
            release.collect_artifacts(self.root)
        import shutil
        shutil.rmtree(self.root.with_name(self.root.name+'-normalized'))

    def test_missing_installer_never_contacts_github(self):
        (self.root / 'MooPython-macos-arm64.dmg').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing or truncated'):
            self.publish()
        self.assertEqual(self.calls, [])

    def test_corruption_rejected(self):
        image = self.root / 'MooPython-macos-arm64.dmg'
        data = bytearray(image.read_bytes()); data[0] = 0
        image.write_bytes(data)
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            self.publish()
        self.assertEqual(self.calls, [])

    def test_invalid_container_rejected(self):
        image = self.root / 'MooPython-macos-arm64.dmg'
        image.write_bytes(b'x' * 4608)
        with self.assertRaisesRegex(RuntimeError, 'Invalid DMG'):
            self.publish()

    def test_source_version_and_architecture_rejected(self):
        for field, value in (('commit', 'b' * 40), ('sdk_version', '10.12.1'), ('architecture', 'x86_64')):
            with self.subTest(field=field):
                original = (self.root / 'python-build.json').read_text()
                self.change('python-build.json', **{field: value})
                with self.assertRaises(RuntimeError):
                    self.publish()
                (self.root / 'python-build.json').write_text(original)
        self.assertEqual(self.calls, [])

    def test_signature_and_real_startup_evidence_required(self):
        self.change('MooPython-macos-arm64.validation.json', official_opend_signature_verified=False)
        with self.assertRaisesRegex(RuntimeError, 'validation incomplete'):
            self.publish()
        self.change('MooPython-macos-arm64.validation.json', official_opend_signature_verified=True)
        self.change('python-opend-smoke.json', official_gui_alive_seconds=0)
        with self.assertRaisesRegex(RuntimeError, 'startup validation missing'):
            self.publish()

    def test_upload_failure_leaves_draft(self):
        def fail(*args):
            if args[:2] == ('release', 'upload'):
                raise subprocess.CalledProcessError(1, args, stderr='Upload failed')
            return self.gh(*args)
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish(fail)
        self.assertTrue(any(c[:2] == ('release', 'create') and '--draft' in c for c in self.calls))
        self.assertFalse(any(c[:2] == ('release', 'edit') for c in self.calls))

    def test_missing_or_wrong_size_uploaded_asset_leaves_draft(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                self.calls.clear()
                def incorrect(*args):
                    result = self.gh(*args)
                    if args[:2] == ('release', 'view') and 'assets' in args:
                        assets = [dict(a) for a in self.assets]
                        if missing: assets.pop()
                        else: assets[0]['size'] += 1
                        return json.dumps(dict(assets=assets))
                    return result
                with self.assertRaisesRegex(RuntimeError, 'asset verification failed'):
                    self.publish(incorrect)
                self.assertFalse(any(c[:2] == ('release', 'edit') for c in self.calls))

    def test_existing_public_release_is_never_overwritten(self):
        def existing(*args):
            self.calls.append(args)
            return json.dumps(dict(draft=False))
        with self.assertRaisesRegex(RuntimeError, 'refusing overwrite'):
            self.publish(existing)
        self.assertEqual(len(self.calls), 1)

    def test_success_publishes_only_after_asset_verification(self):
        self.assertEqual(self.publish(), 'https://example.org/release')
        operations = [c[:2] for c in self.calls]
        self.assertLess(operations.index(('release', 'upload')), operations.index(('release', 'edit')))
        edit = operations.index(('release', 'edit'))
        self.assertEqual(self.calls[edit - 1][:2], ('release', 'view'))
        self.assertIn('--draft=false', self.calls[edit])
        self.assertEqual(sum(a['name'].endswith('.dmg') for a in self.assets), 1)
        self.assertEqual(sum(a['name'].endswith('.validation.json') for a in self.assets), 1)


if __name__ == '__main__':
    unittest.main()
