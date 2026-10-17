import importlib.util,json,pathlib,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('upstream',ROOT/'scripts/resolve-upstream.py');upstream=importlib.util.module_from_spec(spec);spec.loader.exec_module(upstream)
class UpstreamResolutionTests(unittest.TestCase):
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.directory.name);(self.root/'runtime').mkdir()
  self.sdk=dict(version='10.11.7108',python=dict(url='https://files.pythonhosted.org/sdk.tar.gz',sha256='b'*64))
  self.opend=dict(version='10.11.7108',url='https://softwaredownload.moomoo.com/moomoo_OpenD_10.11.7108_Mac.tar.gz',sha256='c'*64)
  (self.root/'runtime/sdk.json').write_text(json.dumps(self.sdk));(self.root/'runtime/opend.json').write_text(json.dumps(self.opend))
  self.root_patch=patch.object(upstream,'ROOT',self.root);self.root_patch.start();self.commit='d'*40
 def tearDown(self):self.root_patch.stop();self.directory.cleanup()
 def test_pinned_pull_request_resolution_has_no_network(self):
  with patch.object(upstream,'get_json',side_effect=AssertionError('network called')):
   result=upstream.resolve(False,self.commit)
  self.assertEqual(result['sdk'],self.sdk);self.assertEqual(result['opend'],self.opend)
 def test_unchanged_version_retains_known_hashes(self):
  with patch.object(upstream,'get_json',return_value={'info':{'version':'10.11.7108'}}),patch.object(upstream,'latest_opend',return_value='10.11.7108'),patch.object(upstream,'digest_url',side_effect=AssertionError('download called')):
   result=upstream.resolve(True,self.commit);upstream.fill_hashes(result)
  self.assertEqual(result['sdk']['python']['sha256'],'b'*64)
 def test_matching_new_release_resolves_python_sdk_and_opend(self):
  responses=[{'info':{'version':'11.0.7200'}},{'urls':[{'packagetype':'sdist','url':'https://files.pythonhosted.org/new-sdk.tar.gz','digests':{'sha256':'e'*64}}]}]
  with patch.object(upstream,'get_json',side_effect=responses),patch.object(upstream,'latest_opend',return_value='11.0.7200'),patch.object(upstream,'digest_url',return_value='f'*64):
   result=upstream.resolve(True,self.commit);upstream.fill_hashes(result)
  self.assertEqual(result['sdk']['version'],'11.0.7200');self.assertEqual(result['opend']['version'],'11.0.7200')
  self.assertEqual(set(result['sdk']),{'version','python'});self.assertEqual(result['sdk']['python']['sha256'],'e'*64)
 def test_downgrade_and_sdk_ahead_of_opend_are_rejected(self):
  for sdk,opend in [('10.10.7008','10.11.7108'),('10.11.7108','10.10.7008'),('11.0.7200','10.11.7108')]:
   with patch.object(upstream,'get_json',return_value={'info':{'version':sdk}}),patch.object(upstream,'latest_opend',return_value=opend):
    with self.assertRaises(RuntimeError):upstream.resolve(True,self.commit)
 def test_untrusted_sources_and_version_injection_are_rejected(self):
  for url in ['http://softwaredownload.moomoo.com/a','https://softwaredownload.moomoo.com.evil.example/a','https://files.pythonhosted.org@evil.example/a']:
   with self.assertRaises(ValueError):upstream.checked_url(url,{'softwaredownload.moomoo.com','files.pythonhosted.org'})
  for v in ['11.0.7200;rm','../11.0.7200','11.0.7200rc1']:
   with self.assertRaises(ValueError):upstream.version(v)
  with self.assertRaises(ValueError):upstream.tag_for('../bad', '11.0.7200','11.0.7200')
 def test_missing_or_yanked_python_release_is_rejected(self):
  for files in [[],[{'packagetype':'sdist','yanked':True}]]:
   with patch.object(upstream,'get_json',side_effect=[{'info':{'version':'11.0.7200'}},{'urls':files}]),patch.object(upstream,'latest_opend',return_value='11.0.7200'):
    with self.assertRaises(RuntimeError):upstream.resolve(True,self.commit)
 def test_invalid_artifact_checksum_is_rejected(self):
  item=dict(self.sdk);item['python']={**self.sdk['python'],'sha256':'wrong'}
  with self.assertRaises(ValueError):upstream.fill_hashes(dict(sdk=item,opend=self.opend))
