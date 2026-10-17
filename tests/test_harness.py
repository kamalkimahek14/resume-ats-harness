"""Run: python -m unittest discover -s tests"""
import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from resume_ats import judge, match, parse, split, taxonomy
from resume_ats.__main__ import load_posts, run_score

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
RESUME = EX / "resume_sample.txt"


class Parse(unittest.TestCase):
    def setUp(self):
        self.p = parse.parse(parse.extract_text(RESUME), "2026-10")

    def test_profile_sections_jobs(self):
        self.assertEqual(self.p["name"], "Jordan Avery")
        self.assertTrue(self.p["headline"].startswith("Data Engineer"))
        self.assertEqual(self.p["sections"], ["summary", "skills", "experience", "projects", "education", "certifications"])
        self.assertEqual([(j["title"], j["company"], j["start"], j["end"]) for j in self.p["jobs"]],
                         [("Data Engineer", "Riverbend Commerce", "Mar 2022", "Present"),
                          ("Data Analyst", "Kettle Hill Insurance", "Jun 2019", "Feb 2022")])
        self.assertEqual(self.p["years"], 7.2)

    def test_sample_lints_clean_and_bad_layout_is_caught(self):
        self.assertEqual(parse.lint(parse.extract_text(RESUME), self.p), [])
        bad = "Pat Doe\nEngineer\n\nWork History\nI built things\tin columns 2019 - 2021\ncertiﬁcation\n"
        issues = " ".join(parse.lint(bad, parse.parse(bad)))
        for want in ("ligature", "tab", "missing headings", "Mon YYYY", "no job line", "first person"):
            self.assertIn(want, issues)

    def test_docx_reads_like_txt(self):
        body = "".join(f"<w:p><w:r><w:t>{l}</w:t></w:r></w:p>" for l in RESUME.read_text(encoding="utf-8").splitlines())
        xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
               + body.replace("&", "&amp;") + "</w:body></w:document>")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.docx"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("word/document.xml", xml)
            self.assertEqual(parse.parse(parse.extract_text(path))["jobs"], self.p["jobs"])

    def test_pdf_without_pypdf_explains_the_fallback(self):
        try:
            import pypdf  # noqa: F401
            self.skipTest("pypdf is installed")
        except ImportError:
            with self.assertRaisesRegex(RuntimeError, "pypdf"):
                parse.extract_text(Path("resume.pdf"))


class Match(unittest.TestCase):
    def test_taxonomy_acronyms_are_case_sensitive(self):
        self.assertIn("SQL", taxonomy.find("Expert SQL"))
        self.assertNotIn("SQL", taxonomy.find("a sequel is coming"))
        self.assertNotIn("Java", taxonomy.find("JavaScript only"))

    def test_scores_and_knockouts(self):
        r = run_score(RESUME, EX / "jds", EX / "split.json")
        rows = {x["id"]: x for x in r["rows"]}
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows["ex-101"]["coverage"], 100.0)
        self.assertIn("degree level above the resume's", rows["ex-105"]["knockouts"])
        self.assertIn("Apache Flink", rows["ex-103"]["missing_required"])
        self.assertTrue(all(0 <= x["B"] <= 100 for x in rows.values()))

    def test_placement_rewards_skills_inside_bullets(self):
        post = {"title": "Data Engineer", "body": "Requirements: Python and Apache Kafka."}
        listed = parse.parse("A B\nData Engineer\n\nSKILLS\nPython, Kafka\n\nEXPERIENCE\nData Engineer | Co | Jan 2020 – Jan 2024\n- Built reports.\n")
        used = parse.parse("A B\nData Engineer\n\nSKILLS\nPython, Kafka\n\nEXPERIENCE\nData Engineer | Co | Jan 2020 – Jan 2024\n- Built Kafka consumers in Python.\n")
        self.assertEqual(match.score(listed, "Python Kafka", post)["placement"], 0.0)
        self.assertEqual(match.score(used, "Python Kafka", post)["placement"], 100.0)


class Separation(unittest.TestCase):
    def setUp(self):
        self.posts = load_posts(EX / "jds")
        self.side = split.load_split(EX / "split.json")

    def test_example_split_is_separated(self):
        proof = split.separation(self.posts, self.side)
        self.assertFalse(set(proof["train_companies"]) & set(proof["held_companies"]))
        self.assertLess(proof["max_overlap"], 0.10)

    def test_near_duplicate_post_is_caught(self):
        copy = dict(self.posts[0], id="ex-999", company="Bluefin Retail Labs")  # a train post re-listed by a held-out company
        with self.assertRaisesRegex(split.SeparationError, "near-duplicate"):
            split.separation(self.posts + [copy], self.side)

    def test_company_on_both_sides_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "split.json"
            f.write_text(json.dumps({"train": ["A", "B"], "held": ["B"]}))
            with self.assertRaises(split.SeparationError):
                split.load_split(f)

    def test_posts_csv_has_links_only(self):
        with open(ROOT / "posts.example.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0]), ["url", "company", "id"])
        self.assertTrue(3 <= len(rows) <= 5 and all(r["url"].startswith("https://") for r in rows))


class Judge(unittest.TestCase):
    def test_prompt_and_reply(self):
        text = judge.render("RESUME TEXT", "POST TEXT")
        self.assertIn("RESUME TEXT", text)
        self.assertIn('{"skim6": n', text)
        self.assertEqual(judge.parse_reply('Sure: {"skim6": 80, "impact": 70, "credibility": 90, "relevance": 60}')["skim6"], 80)
        with self.assertRaises(ValueError):
            judge.parse_reply('{"skim6": 180, "impact": 70, "credibility": 90, "relevance": 60}')

    def test_aggregate_per_side(self):
        scores = json.loads((EX / "judge_scores.example.json").read_text(encoding="utf-8"))
        side = split.load_split(EX / "split.json")
        sop = {p["id"]: side[p["company"]] for p in load_posts(EX / "jds")}
        agg = judge.aggregate(scores, sop)
        self.assertEqual((agg["train"]["n"], agg["held"]["n"]), (3, 3))
        self.assertAlmostEqual(agg["gap"], round(agg["train"]["C"] - agg["held"]["C"], 1))


if __name__ == "__main__":
    unittest.main()
