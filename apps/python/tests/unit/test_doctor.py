from contextlib import contextmanager, redirect_stdout
from importlib.metadata import PackageNotFoundError
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from moopython import doctor


class DoctorTests(unittest.TestCase):
    def run_check(self, rows=None, error=None, missing=None):
        closed = []
        @contextmanager
        def connection(**kwargs):
            if error: raise error
            try:
                yield SimpleNamespace(snapshots=lambda codes: dict(rows=rows or [], missing_codes=missing or []))
            finally: closed.append(True)
        output = io.StringIO()
        with patch.object(doctor, 'version', return_value='test'), redirect_stdout(output):
            result = doctor.check(connection=connection)
        return result, output.getvalue(), closed

    def test_success_requires_a_real_quote_and_closes_connection(self):
        code, message, closed = self.run_check([dict(code='US.AAPL', last_price=100, update_time='2026-10-16 16:00:00')])
        self.assertEqual(code, 0)
        self.assertIn('US.AAPL：100', message)
        self.assertIn('2026-10-16', message)
        self.assertIn('还需单独注册', message)
        self.assertEqual(closed, [True])

    def test_port_or_permission_failure_is_not_reported_as_ready(self):
        for error in (ConnectionRefusedError('connection refused'), RuntimeError('quote permission denied')):
            code, message, _ = self.run_check(error=error)
            self.assertEqual(code, 1)
            self.assertIn(str(error), message)
            self.assertNotIn('真实行情请求成功', message)

    def test_missing_wrong_or_invalid_quote_is_not_success(self):
        variants = [[], [dict(code='US.OTHER', last_price=100)]]
        variants += [[dict(code='US.AAPL', last_price=p)] for p in (None, 0, -1, True, float('nan'), float('inf'))]
        for rows in variants:
            code, message, _ = self.run_check(rows)
            self.assertEqual(code, 1)
            self.assertNotIn('真实行情请求成功', message)

    def test_missing_package_reports_setup_before_network(self):
        output = io.StringIO()
        with patch.object(doctor, 'version', side_effect=PackageNotFoundError('mcp')), redirect_stdout(output):
            code = doctor.check(connection=lambda **k: self.fail('Network should not run'))
        self.assertEqual(code, 1)
        self.assertIn('./setup.sh', output.getvalue())


if __name__ == '__main__': unittest.main()
