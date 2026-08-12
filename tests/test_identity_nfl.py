"""Tests for the NFL extension of the identity gate (prediction_terminal/identity.py).

Mirrors test_identity.py's style. The core claim under test: the SAME interval model that
matches Fed legs also matches NFL totals (over/under) and spreads (margin), including the
complement-rejection that stops "over" being scored as a gap against "under".

Sportsbook sides come from the REAL adapter (sportsbook.parse_event) so the adapter's raw
schema and the gate's reader are tested together. Kalshi contracts are synthetic — plausible
wordings, NOT captured from live Kalshi (no NFL feed key at authoring time). Where a wording
is genuinely ambiguous the gate is expected to fail closed, and that is asserted too.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prediction_terminal"))

from identity import (  # noqa: E402
    DIFFERENT_QUESTION,
    FAMILY_NFL_SPREAD,
    FAMILY_NFL_TOTAL,
    SAME_QUESTION,
    SUBTLY_DIFFERENT,
    check,
    extract,
    pair_markets,
)
from models import NormalizedMarket  # noqa: E402
import sportsbook  # noqa: E402

GAME_CLOSE = "2026-09-13T17:00:00Z"

# One synthetic SGO event: Bills @ Chiefs, total 45.5, Chiefs -3.5 (home favored).
SGO_EVENT = {
    "eventID": "E1",
    "awayTeam": {"name": "Buffalo Bills"},
    "homeTeam": {"name": "Kansas City Chiefs"},
    "startsAt": GAME_CLOSE,
    "odds": {
        "points-all-game-ou-over": {"byBookmaker": {"pinnacle": {"odds": -110, "overUnder": 45.5}}},
        "points-all-game-ou-under": {"byBookmaker": {"pinnacle": {"odds": -110, "overUnder": 45.5}}},
        "points-home-game-sp-home": {"byBookmaker": {"pinnacle": {"odds": -105, "spread": -3.5}}},
        "points-away-game-sp-away": {"byBookmaker": {"pinnacle": {"odds": -105, "spread": 3.5}}},
        # a quarter market that must be ignored (not full-game):
        "points-all-1q-ou-over": {"byBookmaker": {"pinnacle": {"odds": -110, "overUnder": 11.5}}},
    },
}

SB_SIDES = {m.raw["market"] + ":" + m.raw["side"]: m for m in sportsbook.parse_event(SGO_EVENT)}


def kl(title, prob=0.5, close=GAME_CLOSE, resolution="", ticker="KXNFLX"):
    return NormalizedMarket(
        venue="kalshi", market_id=ticker, event_title=title, outcome="Yes",
        implied_prob=prob, resolution_criteria=resolution, settlement_source="",
        close_time=close,
    )


class TestAdapterProducesFourSides:
    def test_full_game_total_and_spread_only(self):
        # over/under total + home/away spread = 4 sides; the 1q quarter market is dropped.
        assert set(SB_SIDES) == {"total:over", "total:under", "spread:home", "spread:away"}


class TestTotalsExtraction:
    def test_sportsbook_over_is_an_open_interval(self):
        # over 45.5 snaps to integer points: total >= 46.
        e = extract(SB_SIDES["total:over"])
        assert e.family == FAMILY_NFL_TOTAL
        assert e.leg == (46.0, float("inf"))
        assert e.referent == "BUF-KC"          # order-independent game key

    def test_kalshi_combined_over_matches_sportsbook_over(self):
        k = kl("Will the Bills and Chiefs combine for more than 45.5 points?")
        assert extract(k).leg == (46.0, float("inf"))
        assert check(k, SB_SIDES["total:over"]).status == SAME_QUESTION

    def test_kalshi_under_matches_sportsbook_under(self):
        k = kl("Will the Bills and Chiefs combine for fewer than 45.5 total points?")
        assert extract(k).leg == (float("-inf"), 45.0)
        assert check(k, SB_SIDES["total:under"]).status == SAME_QUESTION

    def test_over_and_under_are_complements_not_a_gap(self):
        k_over = kl("Will Bills vs Chiefs combine for over 45.5 points?", prob=0.60)
        v = check(k_over, SB_SIDES["total:under"])
        assert v.status == DIFFERENT_QUESTION
        assert v.failed_check == "outcome_leg"
        assert "cannot both pay out" in v.reason

    def test_half_point_line_difference_is_subtle_not_same(self):
        # Kalshi at 46, sportsbook at 45.5 — overlapping but unequal -> flagged, not matched.
        k = kl("Will the Bills and Chiefs combine for more than 46 points?")
        v = check(k, SB_SIDES["total:over"])
        assert v.status == SUBTLY_DIFFERENT
        assert v.failed_check == "outcome_leg"


class TestSpreadsExtraction:
    def test_reference_axis_is_alphabetical_team(self):
        # ref team = min(BUF, KC) = BUF. Chiefs -3.5 (home) -> KC wins by >=4 -> BUF <= -4.
        e = extract(SB_SIDES["spread:home"])
        assert e.family == FAMILY_NFL_SPREAD
        assert e.leg == (float("-inf"), -4.0)
        assert extract(SB_SIDES["spread:away"]).leg == (-3.0, float("inf"))

    def test_kalshi_favored_win_by_matches_book_home_spread(self):
        # "Chiefs beat the Bills by more than 3.5" == Chiefs -3.5 == book home side.
        k = kl("Will the Chiefs beat the Bills by more than 3.5 points?")
        assert extract(k).leg == (float("-inf"), -4.0)
        assert check(k, SB_SIDES["spread:home"]).status == SAME_QUESTION

    def test_kalshi_underdog_plus_matches_book_away_spread(self):
        k = kl("Will the Bills +3.5 cover against the Chiefs?")
        assert extract(k).leg == (-3.0, float("inf"))
        assert check(k, SB_SIDES["spread:away"]).status == SAME_QUESTION

    def test_favored_and_underdog_are_complements(self):
        fav = kl("Will the Chiefs beat the Bills by more than 3.5 points?")
        dog = kl("Will the Bills +3.5 cover against the Chiefs?")
        assert check(fav, dog).status == DIFFERENT_QUESTION

    def test_inclusive_cue_keeps_the_key_number_in_the_interval(self):
        # "by 3 or more" is margin >= 3 (KC axis (3, inf) -> ref BUF axis (-inf, -3)); the
        # strict "by more than 3" drops to (-inf, -4). That one-integer difference IS the
        # push at the key number — the whole basis of the wedge.
        incl = kl("Will the Chiefs beat the Bills by 3 or more points?")
        strict = kl("Will the Chiefs beat the Bills by more than 3 points?")
        assert extract(incl).leg == (float("-inf"), -3.0)
        assert extract(strict).leg == (float("-inf"), -4.0)

    def test_inclusive_vs_book_integer_line_is_subtly_different_at_the_push(self):
        # Book at an INTEGER -3 (push live at 3) vs Kalshi "3 or more" (no push): overlap
        # but disagree exactly on margin 3 -> SUBTLY_DIFFERENT, not SAME.
        ev = dict(SGO_EVENT, odds={
            "points-home-game-sp-home": {"byBookmaker": {"pinnacle": {"odds": -110, "spread": -3.0}}},
            "points-away-game-sp-away": {"byBookmaker": {"pinnacle": {"odds": -110, "spread": 3.0}}},
        })
        book_home = {m.raw["side"]: m for m in sportsbook.parse_event(ev)}["home"]
        k = kl("Will the Chiefs beat the Bills by 3 or more points?")
        assert check(k, book_home).status == SUBTLY_DIFFERENT

    def test_lose_by_wording_resolves_to_underdog_side(self):
        # "Chiefs lose to Bills by more than 3.5" is nonsensical as favorite, but the parser
        # should still land it deterministically as a subject-margin interval.
        k = kl("Will the Bills lose to the Chiefs by more than 3.5 points?")
        # Bills (subject) margin < -3.5  -> BUF <= -4 == book home side.
        assert extract(k).leg == (float("-inf"), -4.0)
        assert check(k, SB_SIDES["spread:home"]).status == SAME_QUESTION


class TestAdversarialAndFailClosed:
    def test_team_total_without_combined_cue_does_not_match_game_total(self):
        # "Chiefs to score over 30.5" is a TEAM total; only one team, no combined cue.
        k = kl("Will the Chiefs score over 30.5 points against the Bills?")
        # It names both teams but reads as a total with no game-total interval mismatch;
        # at minimum it must NOT be scored SAME against the 45.5 game total.
        assert check(k, SB_SIDES["total:over"]).status != SAME_QUESTION

    def test_wrong_teams_do_not_match(self):
        k = kl("Will the Jets and Dolphins combine for more than 45.5 points?")
        assert extract(k).referent == "MIA-NYJ"
        assert check(k, SB_SIDES["total:over"]).status == DIFFERENT_QUESTION
        assert check(k, SB_SIDES["total:over"]).failed_check == "referent"

    def test_no_teams_fails_closed(self):
        k = kl("Will there be more than 45.5 points combined?")
        assert check(k, SB_SIDES["total:over"]).status == DIFFERENT_QUESTION

    def test_missing_close_date_fails_closed(self):
        k = kl("Will the Bills and Chiefs combine for over 45.5 points?", close="not-a-date")
        assert check(k, SB_SIDES["total:over"]).status == DIFFERENT_QUESTION

    def test_reworded_titles_still_match(self):
        # Same question, three different Kalshi phrasings — all must match the book over side.
        for title in [
            "Bills @ Chiefs: total points over 45.5?",
            "Will Buffalo Bills vs Kansas City Chiefs go over 45.5 combined points?",
            "Chiefs/Bills game: more than 45.5 total points scored?",
        ]:
            assert check(kl(title), SB_SIDES["total:over"]).status == SAME_QUESTION


class TestJoinAndCrossFamily:
    def test_pair_markets_matches_kalshi_slate_to_book(self):
        kalshi = [
            kl("Will the Bills and Chiefs combine for more than 45.5 points?"),   # -> over
            kl("Will the Bills and Chiefs combine for fewer than 45.5 points?"),  # -> under
            kl("Will the Chiefs beat the Bills by more than 3.5 points?"),        # -> home spread
        ]
        same, _ = pair_markets(kalshi, list(SB_SIDES.values()))
        assert len(same) == 3
        assert all(v.is_same for _, _, v in same)

    def test_pair_markets_routes_the_inverted_push_to_subtle_not_same(self):
        # The live pull's finding: Kalshi only quotes half-points, books quote integers. A
        # book -3 (pushes at 3) and Kalshi "more than 3.5" share an IDENTICAL win leg, so the
        # exact-join would call them SAME. They must instead land in `subtle` — the push mass
        # at margin 3 is a real disagreement hiding inside a look-alike line.
        ev = dict(SGO_EVENT, odds={
            "points-home-game-sp-home": {"byBookmaker": {"pinnacle": {"odds": -110, "spread": -3.0}}},
            "points-away-game-sp-away": {"byBookmaker": {"pinnacle": {"odds": -110, "spread": 3.0}}},
        })
        book_int = list(sportsbook.parse_event(ev))
        kalshi = [kl("Will the Chiefs beat the Bills by more than 3.5 points?")]
        same, subtle = pair_markets(kalshi, book_int)
        assert not any(v.is_same for _, _, v in same)
        assert any(v.status == SUBTLY_DIFFERENT for _, _, v in subtle)

    def test_nfl_never_crosses_with_fed(self):
        fed = NormalizedMarket(
            venue="kalshi", market_id="KXFEDDECISION-26SEP-H0",
            event_title="Will the Federal Reserve Hike rates by 0bps at their September 2026 meeting?",
            outcome="Yes", implied_prob=0.43, resolution_criteria="", settlement_source="",
            close_time="2026-09-16T18:59:00Z",
        )
        v = check(fed, SB_SIDES["total:over"])
        assert v.status == DIFFERENT_QUESTION
        assert v.failed_check == "family"
