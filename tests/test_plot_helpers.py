import ast
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class PlotHelperTests(unittest.TestCase):
    def test_moving_average_preserves_series_length(self):
        moving_average = self._load_function("moving_average")

        for length in [1, 2, 3, 8]:
            values = list(range(length))
            smoothed = moving_average(values, 3)

            self.assertEqual(length, len(smoothed))
            self.assertFalse(np.isnan(smoothed).any())

    def test_route_precipitation_bins_groups_dense_samples_into_hours(self):
        route_precipitation_bins = self._load_function("route_precipitation_bins")
        route_hourly = pd.DataFrame(
            {
                "time": pd.to_datetime(
                    [
                        "2026-05-02 08:00",
                        "2026-05-02 08:15",
                        "2026-05-02 08:45",
                        "2026-05-02 09:10",
                    ]
                ),
                "rain": [1.0, 2.0, 3.0, 4.0],
            }
        )

        bins = route_precipitation_bins(route_hourly)

        self.assertEqual(
            [
                pd.Timestamp("2026-05-02 08:30"),
                pd.Timestamp("2026-05-02 09:30"),
            ],
            bins["time"].tolist(),
        )
        self.assertEqual([2.0, 4.0], bins["rain"].tolist())
        self.assertEqual([0.0, 0.0], bins["showers"].tolist())

    @staticmethod
    def _load_function(name):
        tree = ast.parse((ROOT / "main.py").read_text())
        function_node = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
        module = ast.Module(body=[function_node], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {"pd": pd, "np": np}
        exec(compile(module, "main.py", "exec"), namespace)
        return namespace[name]


if __name__ == "__main__":
    unittest.main()
