"""Tests for keynumbers.py — the push-mass quantifier that sizes key-number mismatches.

The wedge's whole claim is that a spread disagreement landing on margin 3 (the most common
NFL result) is a real edge while one landing on margin 17 is noise. These tests pin that
ordering, the symmetric-difference logic feeding it, and the fail-safe on the infinite tail.
All offline, no market data.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prediction_terminal"))

from keynumbers import (  # noqa: E402
    disputed_margins,
    hinge_margin,
    margin_prob,
    push_mass,
)

INF = float("inf")


class TestMarginProb:
    def test_key_number_three_is_the_heaviest(self):
        # 3 is the single most common NFL margin — the whole reason the wedge exists.
        assert margin_prob(3) == max(margin_prob(m) for m in range(1, 22))

    def test_sign_is_ignored(self):
        # The reference-team axis is signed; the key number is |margin|.
        assert margin_prob(-3) == margin_prob(3)

    def test_unlisted_margin_falls_to_small_tail(self):
        assert margin_prob(45) == pytest.approx(0.004)
        assert margin_prob(45) < margin_prob(7)


class TestDisputedMargins:
    def test_inclusive_vs_strict_at_three_disputes_only_three(self):
        # Kalshi "win by 3 or more" -> (3, inf) ; book "-3" cover -> (4, inf).
        # They disagree only on margin 3 — the push.
        assert disputed_margins((3.0, INF), (4.0, INF)) == [3]

    def test_identical_legs_dispute_nothing(self):
        assert disputed_margins((4.0, INF), (4.0, INF)) == []

    def test_two_point_line_move_disputes_the_span(self):
        # (3, inf) vs (5, inf) disagree on margins 3 and 4.
        assert disputed_margins((3.0, INF), (5.0, INF)) == [3, 4]

    def test_lower_bounded_leg_symmetric_difference(self):
        # A losing-margin leg (-inf, -4] vs (-inf, -6]: disagree on -5 and -4.
        assert disputed_margins((-INF, -4.0), (-INF, -6.0)) == [-5, -4]


class TestHingeMargin:
    def test_win_region_hinges_on_the_margin_below_the_line(self):
        # A win-region (3, inf) flips to a loss at margin 2 — the heartbreak number.
        assert hinge_margin((3.0, INF)) == 2

    def test_lose_region_hinges_on_the_margin_above_the_ceiling(self):
        # A losing-side leg (-inf, -4] flips at -3.
        assert hinge_margin((-INF, -4.0)) == -3

    def test_bounded_or_total_leg_has_no_single_hinge(self):
        # Nothing single-margin to hinge on for a bounded band.
        assert hinge_margin((3.0, 7.0)) is None

    def test_hinge_feeds_a_real_key_number_probability(self):
        # The always-on literacy claim: the hinge lands on a scoreable margin.
        assert margin_prob(hinge_margin((4.0, INF))) == margin_prob(3)


class TestPushMass:
    def test_dispute_on_three_outweighs_dispute_on_seventeen(self):
        mass_key, _ = push_mass((3.0, INF), (4.0, INF))       # margin 3
        mass_noise, _ = push_mass((17.0, INF), (18.0, INF))   # margin 17
        assert mass_key > mass_noise

    def test_mass_equals_summed_margin_probs(self):
        mass, margins = push_mass((3.0, INF), (5.0, INF))     # {3, 4}
        assert margins == [3, 4]
        assert mass == pytest.approx(margin_prob(3) + margin_prob(4))

    def test_identical_legs_have_zero_mass(self):
        mass, margins = push_mass((4.0, INF), (4.0, INF))
        assert mass == 0.0
        assert margins == []
