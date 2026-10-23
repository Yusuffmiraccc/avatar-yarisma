import unittest
from src.costing import calculate_ekp


class TestCosting(unittest.TestCase):
    def test_project_example(self):
        self.assertAlmostEqual(calculate_ekp(1076.0, 467.5, 85), 1543.5 / 85, places=8)

    def test_zero_output_rejected(self):
        with self.assertRaises(ValueError):
            calculate_ekp(100, 50, 0)

    def test_negative_cost_rejected(self):
        with self.assertRaises(ValueError):
            calculate_ekp(-1, 50, 5)


if __name__ == "__main__":
    unittest.main()
