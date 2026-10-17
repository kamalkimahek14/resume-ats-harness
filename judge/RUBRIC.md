# Recruiter judge rubric

Fix this rubric before round 1 and do not change it between rounds. The text between the two lines below is
the prompt; `python -m resume_ats judge-prompt` fills `{resume}` and `{post}` and prints it. Give it to any
judge (a person, or a model of your choice) and save the JSON reply. No API call is made by this repository.

---
You are a technical recruiter screening one resume for one job post. You see only the two texts below.
Score each criterion from 0 to 100 with these anchors: 90-100 advance to a phone screen at once; 70-89 likely
screen; 50-69 maybe, with weak spots; below 50 reject.

1. skim6: in a 6-second skim of the top third (name, headline, summary, first bullets), can you tell the
   candidate's role, level and fit for THIS job?
2. impact: do the bullets show what was built, what it fed, and a measured outcome? Are the numbers specific?
3. credibility: are the claims specific, consistent and plausible, with no hype? Do dates, titles and scope agree?
4. relevance: how well does the experience cover this job's must-have requirements? A hard requirement the
   candidate clearly does not meet (years, degree, clearance, a core technology) pulls this below 60.

Return ONLY this JSON, nothing else:
{{"skim6": n, "impact": n, "credibility": n, "relevance": n, "missing_must_haves": ["..."], "top_fixes": ["...", "...", "..."]}}

RESUME:
{resume}

JOB POST:
{post}
---
