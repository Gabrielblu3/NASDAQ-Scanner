"""Tests for the multiplicative devig module (prediction_terminal/devig.py).

The whole point of devig is that fair probabilities sum to exactly 1 while the book's
quoted probabilities sum to more. These tests pin that invariant, the ratio-preservation
property, and the fail-loud behavior on garbage input. All offline.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prediction_terminal"))

from devig import devig_multiplicative, fair_pair, overround  # noqa: E402


def _p(american: float) -> float:
    """American odds -> implied prob, mirroring the adapter, so tests read like real lines."""
    if american >= 100:
        return 100.0 / (american + 100.0)
    return (-american) / ((-american) + 100.0)


class TestOverround:
    def test_standard_minus110_two_way_has_positive_vig(self):
        # A -110/-110 line: each side ~0.5238, sum ~1.0476 -> ~4.76% hold.
        vig = overround([_p(-110), _p(-110)])
        assert vig == pytest.approx(0.0476, abs=1e-3)

    def test_fair_market_has_zero_overround(self):
        assert overround([0.5, 0.5]) == pytest.approx(0.0)


class TestMultiplicativeDevig:
    def test_fair_probs_sum_to_one(self):
        fair = devig_multiplicative([_p(-110), _p(-110)])
        assert sum(fair) == pytest.approx(1.0)

    def test_symmetric_line_devigs_to_fifty_fifty(self):
        fa, fb = fair_pair(_p(-110), _p(-110))
        assert fa == pytest.approx(0.5)
        assert fb == pytest.approx(0.5)

    def test_asymmetric_line_preserves_ratio(self):
        # Favorite -200 (0.6667) vs dog +170 (0.3704); sum 1.0371.
        pa, pb = _p(-200), _p(170)
        fa, fb = fair_pair(pa, pb)
        assert sum((fa, fb)) == pytest.approx(1.0)
        # ratio between sides is unchanged by multiplicative devig
        assert fa / fb == pytest.approx(pa / pb)
        assert fa == pytest.approx(0.6428, abs=1e-3)

    def test_order_is_preserved(self):
        fair = devig_multiplicative([0.7, 0.2, 0.4])   # 3-way, sums to 1.3
        assert fair[0] > fair[2] > fair[1]
        assert sum(fair) == pytest.approx(1.0)

    def test_already_fair_input_is_unchanged(self):
        fair = devig_multiplicative([0.25, 0.75])
        assert fair == pytest.approx([0.25, 0.75])


class TestFailLoud:
    @pytest.mark.parametrize("bad", [[], [0.5]])
    def test_needs_two_sides(self, bad):
        with pytest.raises(ValueError):
            devig_multiplicative(bad)

    @pytest.mark.parametrize("bad", [[0.5, 0.0], [0.5, -0.1], [0.5, 1.5], [0.5, None]])
    def test_rejects_out_of_range_probs(self, bad):
        with pytest.raises(ValueError):
            devig_multiplicative(bad)
