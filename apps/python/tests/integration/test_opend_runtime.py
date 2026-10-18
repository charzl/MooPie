"""The desktop dispatches the Python updater and reads its windowed JSON result."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QProcess
from moopython.runtime import OpenDRuntime


class OpenDRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def test_source_and_packaged_dispatch_use_python_and_report_windowed_errors(self):
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root); (directory/'opend.json').write_text(json.dumps({'version':'10.11.7108'}))
            for frozen in (False,True):
                with self.subTest(frozen=frozen):
                    runtime=OpenDRuntime(); runtime.directory=directory; messages=[]
                    runtime.status.connect(messages.append)
                    with patch('sys.platform','darwin'),patch('sys.frozen',frozen,create=True),patch.object(QProcess,'start') as start:
                        runtime.run('update')
                        arguments=start.call_args.args[1]
                        expected=['opend'] if frozen else ['-m','moopython.opend_manager']
                        self.assertEqual(arguments[:len(expected)],expected)
                        self.assertIn('--force',arguments)
                        self.assertIn('--output',arguments)
                        runtime.output.write_text(json.dumps({'error':'Signature rejected','messages':['Signature rejected']}))
                        runtime.process.finished.emit(1,QProcess.ExitStatus.NormalExit)
                        self.assertIsNone(runtime.process)
                        self.assertEqual(messages[-1],'Signature rejected')
                    runtime.workspace.cleanup(); runtime.deleteLater()
            self.app.processEvents()


if __name__=='__main__': unittest.main()
