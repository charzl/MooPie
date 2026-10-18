"""Installer policy, atomic selection, locking and the headless Python entry point."""
import copy
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from moopython import opend_manager as runtime


class PolicyTests(unittest.TestCase):
    def test_numeric_versions_and_untrusted_redirects(self):
        self.assertTrue(runtime.newer('10.11.7108','10.9.6908'))
        self.assertFalse(runtime.newer('10.11.7108','10.11.7108'))
        for value in ('../x','10.11.7108/../../x','10.11','10.-1.3','10.11.7;rm','10.11.٧'):
            with self.subTest(value=value),self.assertRaises(ValueError): runtime.parts(value)
        for url in ('http://softwaredownload.moomoo.com/moomoo_OpenD_10.11.7108_Mac.tar.gz',
                    'https://evil.example/moomoo_OpenD_10.11.7108_Mac.tar.gz',
                    'https://softwaredownload.moomoo.com.evil.example/moomoo_OpenD_10.11.7108_Mac.tar.gz',
                    'https://www.moomoo.com/403'):
            with self.subTest(url=url),self.assertRaises(ValueError): runtime.version_from_redirect('Location: '+url)
        version=runtime.version_from_redirect('HTTP/2 302\r\nlocation: https://softwaredownload.futunn.com/Futu_OpenD_10.11.7108_Mac.tar.gz\r\n')
        self.assertEqual(runtime.download_url(version),'https://softwaredownload.moomoo.com/moomoo_OpenD_10.11.7108_Mac.tar.gz')

    def test_selection_switch_rollback_and_failed_validation_are_atomic(self):
        with tempfile.TemporaryDirectory() as root:
            store=runtime.Store(root); accept=lambda path: None
            store.activate('10.10.7008',accept); store.activate('10.11.7108',accept)
            before=store.read()
            self.assertEqual(before['previous'],'10.10.7008')
            def reject(path): raise ValueError('Signature rejected')
            with self.assertRaises(ValueError): store.rollback(reject)
            with self.assertRaises(ValueError): store.activate('10.12.7208',reject)
            store.activate('10.9.6908',accept)
            self.assertEqual(store.read(),before)
            store.rollback(accept); self.assertEqual(store.read()['current'],'10.10.7008')
            store.rollback(accept); self.assertEqual(store.read()['current'],'10.11.7108')
            contents=(Path(root)/'selection.json').read_bytes()
            with patch.object(Path,'replace',side_effect=OSError('Disk failure')):
                with self.assertRaises(OSError): store.save(dict(current='10.12.7208'))
            self.assertEqual((Path(root)/'selection.json').read_bytes(),contents)
            self.assertEqual(sorted(p.name for p in Path(root).iterdir()),['selection.json'])

    def test_existing_selection_timestamp_and_version_remain_compatible(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'selection.json'
            original=dict(current='10.11.7108',previous='10.10.7008',lastCheck=800000000)
            path.write_text(json.dumps(original))
            state=runtime.Store(root).read()
            self.assertEqual(state['last_check'],1778307200)
            self.assertEqual(json.loads(path.read_text()),original)

    def test_app_dispatch_accepts_the_headless_opend_command(self):
        entry=Path(__file__).resolve().parents[2]/'main.py'
        result=subprocess.run([sys.executable,str(entry),'opend','--help'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('--metadata',result.stdout)

    def test_windowed_result_protocol_reports_errors_without_stdout(self):
        with tempfile.TemporaryDirectory() as root,patch.object(sys,'platform','win32'),patch.object(sys,'stdout',None):
            output=Path(root)/'result.json'
            self.assertEqual(runtime.main(['--output',str(output)]),1)
            result=json.loads(output.read_text())
            self.assertIn('only available on macOS',result['error'])
            self.assertEqual(result['messages'],[result['error']])


@unittest.skipIf(os.name=='nt','macOS manager uses POSIX file locking')
class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(); self.root=Path(self.directory.name)
    def tearDown(self): self.directory.cleanup()

    def test_lock_excludes_another_manager_and_releases_after_exit(self):
        with runtime.Manager(self.root):
            with self.assertRaisesRegex(RuntimeError,'另一客户端'): runtime.Manager(self.root)
        with runtime.Manager(self.root): pass

    def test_invalid_checksum_stops_before_network_or_selection(self):
        with runtime.Manager(self.root) as manager,patch.object(runtime,'command',side_effect=AssertionError('No network')):
            for checksum in ('','z'*64,'a'*63):
                with self.assertRaises(ValueError): manager.ensure_installed('10.11.7108',checksum)
            self.assertIsNone(manager.store.read())

    def test_signature_version_and_architecture_are_required(self):
        app=self.root/'gateway.app'; (app/'Contents').mkdir(parents=True)
        info=dict(CFBundleIdentifier='com.moomoo.opend',CFBundleShortVersionString='10.11.7108')
        (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        with runtime.Manager(self.root) as manager,patch.object(runtime,'command',return_value='arm64 x86_64') as run:
            manager.validate(app,'10.11.7108')
            self.assertEqual(run.call_args_list[0].args[0],'/usr/bin/codesign')
            self.assertIn('='+runtime.REQUIREMENT,run.call_args_list[0].args)
            with self.assertRaisesRegex(ValueError,'version mismatch'): manager.validate(app,'0.0.0')
            run.side_effect=RuntimeError('Signature rejected')
            with self.assertRaisesRegex(RuntimeError,'Signature'): manager.validate(app)
            run.side_effect=None;run.return_value='other'
            with self.assertRaisesRegex(ValueError,'architecture'): manager.validate(app)

    def test_running_gateway_is_reused_without_launch_or_kill(self):
        with runtime.Manager(self.root) as manager:
            manager.store.save(dict(current='10.11.7108'))
            with patch.object(runtime,'running_bundle_paths',return_value=[Path('/Applications/moomoo_OpenD.app')]),patch.object(runtime,'command',side_effect=AssertionError('Do not launch or kill')):
                manager.launch()

    def test_current_version_is_reused_offline_and_update_checks_are_throttled(self):
        with runtime.Manager(self.root) as manager:
            manager.store.save(dict(current='10.11.7108',last_check=runtime.time.time()))
            with patch.object(manager,'validate'),patch.object(manager,'install',side_effect=AssertionError('No download')):
                manager.ensure_installed('10.11.7108','a'*64,allow_download=False)
                self.assertIn('24 小时',manager.update())
            before=copy.deepcopy(manager.store.read())
            with patch.object(runtime,'command',side_effect=RuntimeError('Network down')):
                with self.assertRaisesRegex(RuntimeError,'保留 OpenD'): manager.update(force=True)
            self.assertEqual(manager.store.read()['current'],before['current'])

    def test_bad_download_preserves_selection_and_cleans_staging(self):
        with runtime.Manager(self.root) as manager:
            manager.store.save(dict(current='10.10.7008'))
            def command(executable,*args):
                self.assertEqual(executable,'/usr/bin/curl')
                Path(args[args.index('--output')+1]).write_bytes(b'wrong archive')
                return ''
            with patch.object(runtime,'running_bundle_paths',return_value=[]),patch.object(runtime,'command',side_effect=command):
                with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'): manager.install('10.11.7108','a'*64)
            self.assertEqual(manager.store.read()['current'],'10.10.7008')
            self.assertFalse(list(self.root.glob('staging-*')))


@unittest.skipUnless(sys.platform=='darwin' and os.environ.get('MOOMOO_OPEND_UPDATE_ACCEPTANCE')=='1',
                     'Opt in to download the genuine official OpenD archive')
class OfficialUpdateAcceptanceTests(unittest.TestCase):
    def test_official_download_validation_cached_reselection_and_failed_rollback(self):
        with tempfile.TemporaryDirectory(prefix='opend-update-') as root,runtime.Manager(root) as manager:
            manager.store.save(dict(current='0.0.0'))
            manager.update(force=True)
            selected=manager.store.read()
            self.assertTrue(runtime.newer(selected['current'],'0.0.0'))
            manager.validate(manager.store.app(selected['current']),selected['current'])
            self.assertEqual(selected['previous'],'0.0.0')
            manager.store.save(dict(current='0.0.0',previous=selected['current']))
            self.assertIn('已校验并选中',manager.update(force=True))
            with self.assertRaises((OSError,ValueError,RuntimeError)):
                manager.store.rollback(manager.validate)
            self.assertEqual(manager.store.read()['current'],selected['current'])
            self.assertFalse(list(Path(root).glob('staging-*')))


if __name__=='__main__': unittest.main()
