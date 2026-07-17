"""Signal runner — where the moat actually executes.

Loads master-prompt.md, assembles the structured input payload (two venue snapshots +
optional sharp reference + optional user position), and asks the model to run the
Step 1-5 procedure. If ANTHROPIC_API_KEY is unset it returns the fully-assembled
payload instead of calling out, so the plumbing is verifiable without credentials.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from models import MatchCandidate

PROMPT_PATH = Path(__file__).parent / "master-prompt.md"
MODEL = "claude-opus-4-7"


def load_prompt() -> str:
    return PROMPT_PATH.read_text()


def build_payload(
    candidate: MatchCandidate,
    sharp_reference: Optional[dict] = None,
    user_position: Optional[dict] = None,
) -> dict:
    return {
        "VENUE_A": candidate.a.to_dict(),
        "VENUE_B": candidate.b.to_dict(),
        "SHARP_REFERENCE": sharp_reference or {"type": "none"},
        "USER_POSITION": user_position,
    }


def run_signal(
    candidate: MatchCandidate,
    sharp_reference: Optional[dict] = None,
    user_position: Optional[dict] = None,
) -> dict:
    """Returns {'assembled': payload, 'verdict': <model text or None>, 'called_model': bool}."""
    payload = build_payload(candidate, sharp_reference, user_position)
    system = load_prompt()
    user_msg = (
        "Run the procedure on this event. Return only the structured OUTPUT block.\n\n"
        + json.dumps(payload, indent=2)
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"assembled": payload, "verdict": None, "called_model": False,
                "note": "ANTHROPIC_API_KEY unset — payload assembled but model not called."}

    try:
        import anthropic
    except ImportError:
        return {"assembled": payload, "verdict": None, "called_model": False,
                "note": "anthropic SDK not installed (pip install anthropic)."}

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return {"assembled": payload, "verdict": resp.content[0].text,
            "called_model": True}
