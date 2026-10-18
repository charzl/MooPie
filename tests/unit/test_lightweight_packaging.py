"""Prevent OpenD from silently returning to the Python installer."""
import importlib.util,json,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class LightweightPackagingTests(unittest.TestCase):
    def test_updater_only_build_never_prepares_or_copies_gateway(self):
        bundle=module('bundle-opend')
        with tempfile.TemporaryDirectory() as work:
            root=pathlib.Path(work);(root/'runtime').mkdir();(root/'runtime/opend.json').write_text('{}')
            app=root/'MooPie.app';dest=app/'Contents/Resources/OpenD';(dest/'moomoo_OpenD.app').mkdir(parents=True)
            (dest/'OpenDManager').write_text('stale helper')
            with patch.object(bundle,'ROOT',root),patch.object(bundle,'prepare',side_effect=AssertionError('gateway download forbidden')),patch.object(bundle,'run',side_effect=AssertionError('no compiler or subprocess required')),patch('sys.argv',['bundle-opend.py','--updater-only',str(app)]):
                bundle.main()
            self.assertFalse((dest/'moomoo_OpenD.app').exists());self.assertFalse((dest/'OpenDManager').exists());self.assertTrue((dest/'opend.json').is_file())
    def test_dmg_preflight_rejects_gateway_even_outside_expected_resource_path(self):
        package=module('package-dmg')
        with tempfile.TemporaryDirectory() as work:
            root=pathlib.Path(work);app=root/'MooPie.app';resources=app/'Contents/Resources';resources.mkdir(parents=True)
            (resources/'build-manifest.json').write_text('{}');(resources/'unexpected/moomoo_OpenD.app').mkdir(parents=True)
            with patch.object(package,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'must not bundle OpenD'):package.package(app,root/'installer.dmg',external_opend=True)
                run.assert_not_called()
