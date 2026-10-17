"""Training / held-out split by company, with a separation proof.

Every company goes to one side only. Wording changes may use training results; held-out posts are read only
by the scorer. The proof checks that companies, post IDs and URLs are disjoint, and that no training post is a
near-copy of a held-out post (8-word shingle overlap below a limit).
"""
import json
import re
from pathlib import Path


class SeparationError(AssertionError):
    pass


def load_split(path):
    sp = json.loads(Path(path).read_text(encoding="utf-8"))
    both = set(sp["train"]) & set(sp["held"])
    if both:
        raise SeparationError(f"company on both sides: {sorted(both)}")
    return {c: "train" for c in sp["train"]} | {c: "held" for c in sp["held"]}


def shingles(text, n=8):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def separation(posts, side, limit=0.10, n=8):
    """posts: list of post dicts; side: company -> 'train' | 'held'. Raises SeparationError on any breach."""
    unknown = sorted({p["company"] for p in posts} - set(side))
    if unknown:
        raise SeparationError(f"companies missing from the split: {unknown}")
    tr = [p for p in posts if side[p["company"]] == "train"]
    he = [p for p in posts if side[p["company"]] == "held"]
    if not tr or not he:
        raise SeparationError("each side needs at least one post")
    tc, hc = {p["company"] for p in tr}, {p["company"] for p in he}
    if tc & hc:
        raise SeparationError(f"company overlap: {sorted(tc & hc)}")
    if {p["id"] for p in tr} & {p["id"] for p in he}:
        raise SeparationError("post ID overlap")
    urls = lambda ps: {p["url"] for p in ps if p.get("url")}
    if urls(tr) & urls(he):
        raise SeparationError("URL overlap")
    S = {p["id"]: shingles(p["body"], n) for p in posts}
    worst = max(((len(S[a["id"]] & S[b["id"]]) / max(1, min(len(S[a["id"]]), len(S[b["id"]]))), a["id"], b["id"])
                 for a in tr for b in he))
    if worst[0] > limit:
        raise SeparationError(f"near-duplicate posts {worst[1]} and {worst[2]}: {100 * worst[0]:.1f}% of {n}-word shingles shared")
    return {"train_companies": sorted(tc), "held_companies": sorted(hc), "train_posts": len(tr), "held_posts": len(he),
            "max_overlap": round(worst[0], 4), "pair": list(worst[1:]), "limit": limit}
