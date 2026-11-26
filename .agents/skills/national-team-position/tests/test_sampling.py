import io
import os
import runpy
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "national_team_position.py"


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.akshare = Mock()
        with patch.dict(sys.modules, {"akshare": self.akshare, "pandas": Mock()}):
            with patch.dict(os.environ):
                self.script = runpy.run_path(str(SCRIPT))

    def test_monthly_sampling_stays_inside_requested_range(self):
        sample_dates = self.script["sample_dates"]
        cases = [
            ("2026-01-25", "2026-01-30", []),
            ("2026-01-25", "2026-02-28", ["2026-02-15"]),
            ("2026-12-16", "2027-01-15", ["2027-01-15"]),
            ("2026-02-15", "2026-02-15", ["2026-02-15"]),
        ]
        for start, end, expected in cases:
            with self.subTest(start=start, end=end):
                dates = sample_dates(start, end, "monthly")
                self.assertEqual([date.date().isoformat() for date in dates], expected)

    def test_fallback_stops_at_requested_start(self):
        self.akshare.fund_etf_scale_sse.return_value = None
        with patch.object(self.script["time"], "sleep"), redirect_stdout(io.StringIO()):
            self.assertEqual(self.script["fetch_shares"]("2026-01-14", "2026-01-15", "monthly"), [])
        self.assertEqual(
            self.akshare.fund_etf_scale_sse.call_args_list,
            [call(date="20260115"), call(date="20260114")],
        )


if __name__ == "__main__":
    unittest.main()
