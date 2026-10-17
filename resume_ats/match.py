"""Score one parsed resume against one job post. Deterministic, no network.

Per post: required-skill coverage, keyword placement (required skills that appear inside experience or
project bullets, not only in the Skills list), title alignment, years, education, plus knock-out risks.
"""
import re
from pathlib import Path
from . import taxonomy

WEIGHTS = {"coverage": 0.40, "placement": 0.20, "title": 0.15, "years": 0.15, "education": 0.10}
PREFERRED = re.compile(r"^[^\n]{0,40}\b(preferred|nice to have|nice-to-have|bonus|desired|pluses)\b", re.I | re.M)
SENIORITY = {"senior", "sr", "junior", "jr", "staff", "principal", "lead", "ii", "iii", "i"}
# Abbreviations are case-sensitive so "40 ms" or "bs" in prose are not read as degrees.
DEGREE = [(3, re.compile(r"\bPh\.?\s?D\b|\b[Dd]octora")), (2, re.compile(r"\b[Mm]aster|\bM\.?Sc?\b")),
          (1, re.compile(r"\b[Bb]achelor|\bB\.?Sc?\b|\bB\.?A\b"))]


def load_post(path):
    """A post file: 'KEY: value' header lines (ID, COMPANY, TITLE, optional URL), a blank line, then the text."""
    text = Path(path).read_text(encoding="utf-8")
    head, _, body = text.partition("\n\n")
    meta = {k.strip().lower(): v.strip() for k, v in (l.split(":", 1) for l in head.splitlines() if ":" in l)}
    for key in ("id", "company", "title"):
        if not meta.get(key):
            raise ValueError(f"{path}: header line '{key.upper()}:' is missing")
    meta["body"] = body.strip()
    return meta


def split_required(body):
    m = PREFERRED.search(body)
    return (body[:m.start()], body[m.start():]) if m else (body, "")


def years_required(text):
    ys = [int(y) for y in re.findall(r"(\d{1,2})\+?\s*(?:or more\s+)?years", text, re.I) if 0 < int(y) < 30]
    return max(ys) if ys else 0


def degree_level(text):
    return max((lvl for lvl, p in DEGREE if p.search(text)), default=0)


def degree_required(req):
    """Level a post insists on: a degree named without 'or equivalent' / a lower alternative."""
    if re.search(r"or equivalent|equivalent (practical )?experience", req, re.I):
        return 0
    lvl = degree_level(req)
    lower = [l for l, p in DEGREE if l < lvl and p.search(req)]
    return min(lower) if lower else lvl


def title_words(title):
    return [w for w in re.findall(r"[a-z]+", title.lower()) if w not in SENIORITY]


def knockouts(req, body, parsed):
    k = []
    y = years_required(req)
    if y > parsed["years"]:
        k.append(f"asks {y}+ years (resume shows {parsed['years']})")
    need = degree_required(req)
    if need > degree_level(parsed["education"]):
        k.append("degree level above the resume's")
    if re.search(r"security clearance|TS/SCI|U\.?S\.? citizen", body, re.I):
        k.append("citizenship or clearance")
    if re.search(r"(fluen\w+|native)[^.\n]{0,25}\b(Japanese|Korean|French|German|Spanish|Mandarin|Portuguese)", body):
        k.append("language requirement")
    return k


def score(parsed, resume_text, post):
    req, pref = split_required(post["body"])
    R = taxonomy.find(req) - {"security clearance"}
    P = taxonomy.find(pref) - R - {"security clearance"}
    have = taxonomy.find(resume_text)
    wt = lambda s: 0.5 if s in taxonomy.SOFT else 1.0
    total = sum(wt(s) for s in R) or 1.0
    matched = R & have
    coverage = 100 * sum(wt(s) for s in matched) / total
    in_bullets = taxonomy.find("\n".join(parsed["bullets"]))
    placed = matched & in_bullets
    placement = 100 * len(placed) / len(matched) if matched else 0.0
    words = title_words(post["title"])
    has_all = lambda text: bool(words) and all(re.search(r"\b" + w, text.lower()) for w in words)
    if has_all(parsed["headline"]):
        title = 100
    elif has_all(parsed["summary"]) or any(has_all(j["title"]) for j in parsed["jobs"]):
        title = 70
    else:
        title = 30
    need_y = years_required(req)
    years = 100 if need_y <= parsed["years"] else max(0, 100 - 25 * (need_y - parsed["years"]))
    education = 100 if degree_required(req) <= degree_level(parsed["education"]) else 40
    parts = {"coverage": coverage, "placement": placement, "title": title, "years": years, "education": education}
    return {"B": round(sum(WEIGHTS[k] * v for k, v in parts.items()), 1), **{k: round(v, 1) for k, v in parts.items()},
            "pref_coverage": round(100 * len(P & have) / len(P), 1) if P else 100.0,
            "missing_required": sorted(R - have), "unplaced": sorted(matched - placed),
            "knockouts": knockouts(req, post["body"], parsed)}
