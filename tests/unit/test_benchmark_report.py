import importlib.util, json, pathlib, tempfile, unittest
path=pathlib.Path(__file__).resolve().parents[2]/'scripts/compare-benchmarks.py'
spec=importlib.util.spec_from_file_location('compare',path); compare=importlib.util.module_from_spec(spec); spec.loader.exec_module(compare)
class ReportValidationTests(unittest.TestCase):
 def test_missing_implementation_is_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   with self.assertRaisesRegex(AssertionError,'Both benchmark'): compare.compare(root,pathlib.Path(root)/'result.md')
 def test_mismatched_fixture_is_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   for name,hash_value in [('python-qt','a'),('swiftui-cpp','b')]:
    pathlib.Path(root,f'{name}-benchmark.json').write_text(json.dumps(dict(implementation=name,fixture_sha256=hash_value)))
   with self.assertRaisesRegex(AssertionError,'Fixture mismatch'): compare.compare(root,pathlib.Path(root)/'result.md')
 def test_mismatched_workload_is_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   for name,frames in [('python-qt',120),('swiftui-cpp',60)]:
    pathlib.Path(root,f'{name}-benchmark.json').write_text(json.dumps(dict(implementation=name,fixture_sha256='same',workload=dict(frames=frames))))
   with self.assertRaisesRegex(AssertionError,'Workload mismatch'): compare.compare(root,pathlib.Path(root)/'result.md')
if __name__=='__main__': unittest.main()
