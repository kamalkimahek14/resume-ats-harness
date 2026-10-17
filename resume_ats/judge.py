"""Recruiter-judge rubric: fill the prompt template, check a judge's JSON reply, and aggregate scores.
No API calls: you run the judge (a person or any model) and save the replies as JSON."""
import json
import re
import statistics as st
from pathlib import Path

RUBRIC = Path(__file__).resolve().parent.parent / "judge" / "RUBRIC.md"
CRITERIA = ("skim6", "impact", "credibility", "relevance")


def template():
    text = RUBRIC.read_text(encoding="utf-8")
    parts = text.split("\n---\n")
    if len(parts) < 3:
        raise ValueError("RUBRIC.md must hold the prompt between two '---' lines")
    return parts[1].strip()


def render(resume_text, post_text):
    return template().format(resume=resume_text.strip(), post=post_text.strip())


def parse_reply(text):
    """The judge's reply as a dict; raises ValueError when it is not the JSON the rubric asks for."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in the reply")
    d = json.loads(m.group(0))
    for k in CRITERIA:
        v = d.get(k)
        if not isinstance(v, (int, float)) or not 0 <= v <= 100:
            raise ValueError(f"criterion {k!r} must be a number from 0 to 100, got {v!r}")
    return d


def aggregate(scores, side_of_post, noise=3.0):
    """scores: {post_id: reply dict}; side_of_post: {post_id: 'train' | 'held'}.
    Returns per-side means per criterion and the overall C score (mean of the four criteria)."""
    out = {}
    for side in ("train", "held"):
        rows = [parse_reply(json.dumps(v)) for pid, v in scores.items() if side_of_post.get(pid) == side]
        if not rows:
            out[side] = None
            continue
        crit = {k: round(st.mean(r[k] for r in rows), 1) for k in CRITERIA}
        out[side] = {"n": len(rows), **crit, "C": round(st.mean(crit.values()), 1)}
    if out["train"] and out["held"]:
        gap = round(out["train"]["C"] - out["held"]["C"], 1)
        out["gap"] = gap
        out["note"] = (f"gap {gap} is within judge noise (+/-{noise}); not evidence" if abs(gap) < noise
                       else f"gap {gap} is larger than judge noise (+/-{noise})")
    return out
