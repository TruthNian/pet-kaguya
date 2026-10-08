"""Rejected old build can only produce explicit isolated regression outputs."""
import contextlib
import io
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build import historical_arguments


class HistoricalGuard(unittest.TestCase):
    def assert_denied(self, arguments):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            historical_arguments(arguments)
        self.assertEqual(result.exception.code, 2)

    def test_no_default_source_or_output_promotion(self):
        self.assert_denied([])
        self.assert_denied(['--out', str(ROOT/'work/regression')])
        self.assert_denied(['--historical-phase3'])

    def test_legacy_output_cannot_overwrite_production_or_sources(self):
        for destination in ['pet', 'sources/canonical', 'candidates/phase5/idle', 'work', 'work/../pet']:
            self.assert_denied(['--historical-phase3', '--out', str(ROOT/destination)])

    def test_explicit_isolated_historical_regression_is_allowed(self):
        args = historical_arguments(['--historical-phase3', '--out', str(ROOT/'work/regression')])
        self.assertEqual(args.out, (ROOT/'work/regression').resolve())


if __name__ == '__main__':
    unittest.main()
