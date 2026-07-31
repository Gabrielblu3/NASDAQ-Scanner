"""Tests for the event identity gate (prediction_terminal/identity.py).

Fixtures are verbatim strings captured from live Polymarket and Kalshi responses on
2026-07-30, including Polymarket's shared resolution boilerplate — the boilerplate is
load-bearing here, because reading the outcome leg out of it instead of out of the title
is what made every Polymarket leg parse as hold(0bps). These tests run offline.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prediction_terminal"))

from identity import (  # noqa: E402
    DIFFERENT_QUESTION,
    SAME_QUESTION,
    SUBTLY_DIFFERENT,
    check,
    extract,
    pair_markets,
)
from models import NormalizedMarket  # noqa: E402

# Polymarket ships the same resolution text on every market in the series, and it ends by
# naming the "No change" bracket. Any leg parser that reads this blob will call every
# contract a hold.
PM_BOILERPLATE = (
    "The FED interest rates are defined in this market by the upper bound of the target "
    "federal funds range. The decisions on the target federal funds range are made by the "
    "Federal Open Market Committee (FOMC). If no rate decision is released by the end date "
    'of the next scheduled meeting, this market will resolve to the "No change" bracket.'
)


def pm(title, prob=0.5, close="2026-09-16T00:00:00Z"):
    return NormalizedMarket(
        venue="polymarket", market_id=f"pm-{abs(hash(title)) % 10**6}",
        event_title=title, outcome="Yes", implied_prob=prob,
        resolution_criteria=PM_BOILERPLATE,
        settlement_source="resolution source for this market is the FOMC's statement",
        close_time=close,
    )


def kl(title, ticker, prob=0.5, close="2026-09-16T18:59:00Z"):
    return NormalizedMarket(
        venue="kalshi", market_id=ticker, event_title=title, outcome="Yes",
        implied_prob=prob,
        resolution_criteria=(
            f"If the Federal Reserve does a {title.split('rates by ')[-1].split(' at')[0]} "
            "on September 16, 2026, then the market resolves to Yes."
        ),
        settlement_source="", close_time=close,
    )


SEP = "September 2026"
PM_HOLD = pm(f"Will there be no change in Fed interest rates after the {SEP} meeting?", 0.445)
PM_HIKE25 = pm(f"Will the Fed increase interest rates by 25 bps after the {SEP} meeting?", 0.525)
PM_CUT25 = pm(f"Will the Fed decrease interest rates by 25 bps after the {SEP} meeting?", 0.0275)
PM_HIKE50 = pm(f"Will the Fed increase interest rates by 50+ bps after the {SEP} meeting?", 0.0145)

KL_HOLD = kl(f"Will the Federal Reserve Hike rates by 0bps at their {SEP} meeting?",
             "KXFEDDECISION-26SEP-H0", 0.43)
KL_HIKE25 = kl(f"Will the Federal Reserve Hike rates by 25bps at their {SEP} meeting?",
               "KXFEDDECISION-26SEP-H25", 0.545)
KL_HIKEGT25 = kl(f"Will the Federal Reserve Hike rates by >25bps at their {SEP} meeting?",
                 "KXFEDDECISION-26SEP-H26", 0.025)
KL_CUT25 = kl(f"Will the Federal Reserve Cut rates by 25bps at their {SEP} meeting?",
              "KXFEDDECISION-26SEP-C25", 0.02)
KL_HOLD_JAN28 = kl("Will the Federal Reserve Hike rates by 0bps at their January 2028 meeting?",
                   "KXFEDDECISION-28JAN-H0", 0.58, close="2028-01-26T18:59:00Z")
KL_LEVEL = kl("Will the upper bound of the federal funds rate be above 3.50% following "
              "the September 2026 meeting?", "KXFED-26SEP-T3.50", 0.52)


class TestLegExtraction:
    """The leg must come from the title; the shared boilerplate must not leak in."""

    def test_boilerplate_does_not_make_every_market_a_hold(self):
        assert extract(PM_HIKE25).leg == (25.0, 25.0)
        assert extract(PM_CUT25).leg == (-25.0, -25.0)
        assert extract(PM_HOLD).leg == (0.0, 0.0)

    def test_kalshi_zero_bps_hike_is_a_hold(self):
        # "Hike rates by 0bps" is Kalshi's spelling of no-change.
        assert extract(KL_HOLD).leg == (0.0, 0.0)

    def test_open_ended_legs(self):
        assert extract(KL_HIKEGT25).leg == (26.0, float("inf"))   # >25 excludes 25
        assert extract(PM_HIKE50).leg == (50.0, float("inf"))     # 50+ includes 50

    def test_meeting_referent(self):
        assert extract(PM_HOLD).referent == "2026-09"
        assert extract(KL_HOLD).referent == "2026-09"
        assert extract(KL_HOLD_JAN28).referent == "2028-01"


class TestComplementsAreNotGaps:
    """The failure this gate exists to stop."""

    @pytest.mark.parametrize("other", [KL_HIKE25, KL_HIKEGT25, KL_CUT25])
    def test_hold_against_any_move_is_rejected(self, other):
        v = check(PM_HOLD, other)
        assert v.status == DIFFERENT_QUESTION
        assert v.failed_check == "outcome_leg"
        assert "cannot both pay out" in v.reason

    def test_the_42pp_live_artifact(self):
        # PM no-change 44.5% vs Kalshi hike->25bps 2.5% looked like a 42pp edge and is not.
        v = check(PM_HOLD, KL_HIKEGT25)
        assert not v.is_same


class TestRealPairsSurvive:
    """Fail-closed must not mean fail-everything."""

    @pytest.mark.parametrize("a,b", [
        (PM_HOLD, KL_HOLD), (PM_HIKE25, KL_HIKE25), (PM_CUT25, KL_CUT25),
    ])
    def test_matching_legs_pass(self, a, b):
        assert check(a, b).status == SAME_QUESTION


class TestSubtleMismatch:
    def test_overlapping_but_unequal_legs_flagged_not_passed(self):
        # Kalshi ">25bps" is [26,inf); Polymarket "50+ bps" is [50,inf). They overlap but
        # settle differently on a 26-49bps move.
        v = check(PM_HIKE50, KL_HIKEGT25)
        assert v.status == SUBTLY_DIFFERENT
        assert v.failed_check == "outcome_leg"


class TestOtherGateChecks:
    def test_different_meetings_rejected(self):
        v = check(PM_HOLD, KL_HOLD_JAN28)
        assert v.status == DIFFERENT_QUESTION
        assert v.failed_check == "referent"

    def test_change_market_never_crossed_with_level_market(self):
        v = check(PM_HOLD, KL_LEVEL)
        assert v.status == DIFFERENT_QUESTION
        assert v.failed_check == "family"

    def test_unparseable_fails_closed(self):
        vague = pm("Fed rate hike in 2026?", 0.665, close="2026-12-09T00:00:00Z")
        assert check(vague, KL_HOLD).status == DIFFERENT_QUESTION

    def test_missing_close_date_fails_closed(self):
        broken = kl(f"Will the Federal Reserve Hike rates by 0bps at their {SEP} meeting?",
                    "KXFEDDECISION-26SEP-H0", 0.43, close="not-a-date")
        assert check(PM_HOLD, broken).status == DIFFERENT_QUESTION


class TestJoin:
    """pair_markets finds pairs by identity instead of by wording."""

    def test_finds_pairs_title_similarity_would_miss(self):
        # These score 0.29 Jaccard — under the old 0.30 threshold — purely because
        # Polymarket says "increase ... 25 bps" where Kalshi says "Hike ... 25bps".
        same, _ = pair_markets([PM_HIKE25, PM_CUT25, PM_HOLD],
                               [KL_HIKE25, KL_CUT25, KL_HOLD, KL_HIKEGT25])
        assert len(same) == 3
        assert all(v.is_same for _, _, v in same)

    def test_join_never_returns_complements(self):
        same, _ = pair_markets([PM_HOLD], [KL_HIKE25, KL_HIKEGT25, KL_CUT25])
        assert same == []

    def test_subtle_pairs_reported_separately_not_as_matches(self):
        same, subtle = pair_markets([PM_HIKE50], [KL_HIKEGT25])
        assert same == []
        assert len(subtle) == 1
        assert subtle[0][2].status == SUBTLY_DIFFERENT

    def test_join_agrees_with_pairwise_check(self):
        a_side = [PM_HOLD, PM_HIKE25, PM_CUT25, PM_HIKE50]
        b_side = [KL_HOLD, KL_HIKE25, KL_HIKEGT25, KL_CUT25, KL_LEVEL, KL_HOLD_JAN28]
        joined = {(a.market_id, b.market_id) for a, b, _ in pair_markets(a_side, b_side)[0]}
        brute = {(a.market_id, b.market_id)
                 for a in a_side for b in b_side if check(a, b).is_same}
        assert joined == brute


class TestSymmetry:
    @pytest.mark.parametrize("a,b", [
        (PM_HOLD, KL_HOLD), (PM_HOLD, KL_HIKE25), (PM_HIKE50, KL_HIKEGT25),
        (PM_HOLD, KL_LEVEL), (PM_HOLD, KL_HOLD_JAN28),
    ])
    def test_verdict_does_not_depend_on_argument_order(self, a, b):
        assert check(a, b).status == check(b, a).status
