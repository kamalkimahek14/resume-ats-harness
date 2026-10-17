"""Read a resume the way applicant tracking software does: as plain lines, with headings and job lines found
by pattern. Standard library only. .txt and .docx always work; .pdf needs the optional pypdf package.

The heuristics follow the common ATS approach (and the open-source OpenResume parser):
  1. a heading is a known section word alone on a line, or a short line in capitals,
  2. the profile is everything before the first heading: name first, headline second,
  3. in Experience, a non-bullet line with a date range starts a job: "Title | Company | Mon YYYY – Mon YYYY",
  4. bullets are lines that start with a bullet mark.
"""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

SECTION_WORDS = ("summary", "objective", "skills", "experience", "work experience", "employment", "projects",
                 "education", "certifications", "certificates", "publications", "awards")
EXPECTED = ("summary", "skills", "experience", "education")
MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (?:19|20)\d\d"
RANGE = re.compile(rf"({MON})\s*[–—-]\s*({MON}|Present|Current)", re.I)
OTHER_DATES = re.compile(r"\b\d{1,2}/(19|20)\d\d\b|\b(19|20)\d\d\s*(to|-|–)\s*(19|20)\d\d\b")
BULLET = re.compile(r"^\s*[•●▪‣⁃\-\*]\s+")
LIGATURES = re.compile("[ﬀ-ﬆ]")
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_text(path):
    """Plain text of a .txt, .docx or .pdf file."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".txt":
        return path.read_text(encoding="utf-8")
    if ext == ".docx":
        with zipfile.ZipFile(path) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
        paras = []
        for p in root.iter(W_NS + "p"):
            paras.append("".join(t.text or "" for t in p.iter(W_NS + "t")))
        return "\n".join(paras)
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("Reading .pdf needs the optional 'pypdf' package. Install it, or save the resume "
                               "as .txt or .docx and run again.") from None
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    raise ValueError(f"unsupported file type: {ext} (use .txt, .docx or .pdf)")


def _heading(line):
    t = line.strip().rstrip(":").strip()
    if not t:
        return None
    if t.lower() in SECTION_WORDS:
        return t.lower()
    letters = re.sub(r"[^A-Za-z]", "", t)
    if letters and letters.isupper() and len(t.split()) <= 3 and not RANGE.search(t):
        return t.lower()
    return None


def month_index(s, as_of):
    """'Mar 2022' -> months since year 0; 'Present' -> as_of ('YYYY-MM')."""
    if s.lower() in ("present", "current"):
        y, m = as_of.split("-")
        return int(y) * 12 + int(m) - 1
    mon, year = s.replace(".", "").split()
    return int(year) * 12 + MONTHS[mon[:3].lower()] - 1


def parse(text, as_of="2026-10"):
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    sections, cur = {"profile": []}, "profile"
    for l in lines:
        h = _heading(l)
        if h:
            cur = "experience" if h in ("work experience", "employment") else h
            sections.setdefault(cur, [])
        elif l.strip():
            sections[cur].append(l.strip())
    prof = sections["profile"]
    jobs = []
    for l in sections.get("experience", []):
        m = RANGE.search(l)
        if m and not BULLET.match(l):
            parts = [p.strip() for p in l[:m.start()].split("|") if p.strip()]
            jobs.append({"title": parts[0] if parts else "", "company": parts[1] if len(parts) > 1 else "",
                         "start": m.group(1), "end": m.group(2), "bullets": []})
        elif jobs and BULLET.match(l):
            jobs[-1]["bullets"].append(BULLET.sub("", l))
    months = sum(max(0, month_index(j["end"], as_of) - month_index(j["start"], as_of)) for j in jobs)
    project_bullets = [BULLET.sub("", l) for l in sections.get("projects", []) if BULLET.match(l)]
    return {
        "name": prof[0] if prof else "",
        "headline": prof[1] if len(prof) > 1 else "",
        "sections": [s for s in sections if s != "profile"],
        "summary": " ".join(sections.get("summary", [])),
        "skills_text": " ".join(sections.get("skills", [])),
        "jobs": jobs,
        "years": round(months / 12, 1),
        "bullets": [b for j in jobs for b in j["bullets"]] + project_bullets,
        "education": " ".join(sections.get("education", [])),
    }


def lint(text, parsed):
    """Layout and wording problems that make tracking software misread a resume."""
    issues = []
    if LIGATURES.search(text):
        issues.append("ligature glyphs (turn ligatures off in the font settings)")
    if "\t" in text:
        issues.append("tab characters (often a sign of columns or tables)")
    missing = [s for s in EXPECTED if s not in parsed["sections"]]
    if missing:
        issues.append("missing headings: " + ", ".join(missing))
    if OTHER_DATES.search(text):
        issues.append("dates not in 'Mon YYYY' form")
    if not parsed["jobs"]:
        issues.append("no job line found ('Title | Company | Mon YYYY – Mon YYYY')")
    if any(not j["company"] for j in parsed["jobs"]):
        issues.append("a job line without a company")
    if re.search(r"\bI\b|\bmy\b|\bme\b", text):
        issues.append("first person")
    return issues
