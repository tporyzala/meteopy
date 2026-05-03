import ast
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class PlotHelperTests(unittest.TestCase):
    def test_moving_average_preserves_series_length(self):
        moving_average = self._load_moving_average()

        for length in [1, 2, 3, 8]:
            values = list(range(length))
            smoothed = moving_average(values, 3)

            self.assertEqual(length, len(smoothed))
            self.assertFalse(np.isnan(smoothed).any())

    @staticmethod
    def _load_moving_average():
        tree = ast.parse((ROOT / "main.py").read_text())
        function_node = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "moving_average"
        )
        module = ast.Module(body=[function_node], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {"pd": pd, "np": np}
        exec(compile(module, "main.py", "exec"), namespace)
        return namespace["moving_average"]


if __name__ == "__main__":
    unittest.main()
