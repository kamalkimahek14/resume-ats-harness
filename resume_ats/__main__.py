"""Command line.

    python -m resume_ats score RESUME --posts DIR --split FILE [--as-of YYYY-MM]
    python -m resume_ats judge-prompt RESUME POST
    python -m resume_ats judge-aggregate SCORES --posts DIR --split FILE
"""
import argparse
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

from . import judge, match, parse, split


def load_posts(folder):
    posts = [match.load_post(p) for p in sorted(Path(folder).glob("*.txt"))]
    if not posts:
        raise SystemExit(f"no post files (*.txt) in {folder}")
    return posts


def run_score(resume, posts_dir, split_file, as_of="2026-10"):
    text = parse.extract_text(resume)
    parsed = parse.parse(text, as_of)
    posts = load_posts(posts_dir)
    side = split.load_split(split_file)
    proof = split.separation(posts, side)
    rows = []
    for p in posts:
        s = match.score(parsed, text, p)
        s.update(id=p["id"], company=p["company"], post_title=p["title"], side=side[p["company"]])
        rows.append(s)
    summary = {}
    for sd in ("train", "held"):
        r = [x for x in rows if x["side"] == sd]
        summary[sd] = {k: round(st.mean(x[k] for x in r), 1) for k in ("B", "coverage", "placement", "title", "years", "education")}
        summary[sd]["n"] = len(r)
    summary["gap_B"] = round(summary["train"]["B"] - summary["held"]["B"], 1)
    return {"parsed": parsed, "lint": parse.lint(text, parsed), "separation": proof, "rows": rows, "summary": summary}


def print_score(r):
    p = r["parsed"]
    print(f"parse: name={p['name']!r} headline={p['headline']!r} sections={p['sections']} jobs={len(p['jobs'])} years={p['years']}")
    for j in p["jobs"]:
        print(f"  job: {j['title']} | {j['company']} | {j['start']} - {j['end']} ({len(j['bullets'])} bullets)")
    print("lint:", "; ".join(r["lint"]) or "clean")
    s = r["separation"]
    print(f"separation: train {s['train_posts']} posts {s['train_companies']} | held-out {s['held_posts']} posts "
          f"{s['held_companies']} | companies, posts and URLs disjoint | max 8-word shingle overlap "
          f"{100 * s['max_overlap']:.1f}% (limit {100 * s['limit']:.0f}%)")
    print(f"{'post':<8}{'side':<6}{'B':>6}{'cov':>7}{'place':>7}{'title':>7}{'years':>7}{'edu':>6}  knock-outs")
    for x in sorted(r["rows"], key=lambda x: (x["side"] != "train", x["id"])):
        print(f"{x['id']:<8}{x['side']:<6}{x['B']:>6}{x['coverage']:>7}{x['placement']:>7}{x['title']:>7}"
              f"{x['years']:>7}{x['education']:>6}  {', '.join(x['knockouts']) or '-'}")
    for sd in ("train", "held"):
        print(sd.ljust(6), json.dumps(r["summary"][sd]))
    print("train minus held-out B:", r["summary"]["gap_B"])
    # Diagnostics come from training posts only: held-out details must not steer the wording.
    tr = [x for x in r["rows"] if x["side"] == "train"]
    print("train missing:", Counter(s for x in tr for s in x["missing_required"]).most_common(8))
    print("train unplaced:", Counter(s for x in tr for s in x["unplaced"]).most_common(8))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="resume_ats", description="Resume test harness: ATS parse, match, split, judge.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("score")
    a.add_argument("resume")
    a.add_argument("--posts", required=True)
    a.add_argument("--split", required=True)
    a.add_argument("--as-of", default="2026-10", help="month that 'Present' means, YYYY-MM")
    b = sub.add_parser("judge-prompt")
    b.add_argument("resume")
    b.add_argument("post")
    c = sub.add_parser("judge-aggregate")
    c.add_argument("scores")
    c.add_argument("--posts", required=True)
    c.add_argument("--split", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "score":
        print_score(run_score(args.resume, args.posts, args.split, args.as_of))
    elif args.cmd == "judge-prompt":
        post = match.load_post(args.post)
        print(judge.render(parse.extract_text(args.resume), post["title"] + " at " + post["company"] + "\n\n" + post["body"]))
    else:
        side = split.load_split(args.split)
        side_of_post = {p["id"]: side[p["company"]] for p in load_posts(args.posts)}
        scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))
        print(json.dumps(judge.aggregate(scores, side_of_post), indent=1))


if __name__ == "__main__":
    sys.exit(main())
