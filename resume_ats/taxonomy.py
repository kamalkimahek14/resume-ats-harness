"""Skill vocabulary with synonyms. Write it once, before any scoring, and do not tune it per company.

Each canonical skill maps to regex variants. Patterns that start with CS: are matched case-sensitively,
so short acronyms ("SQL", "AWS") are not counted inside ordinary words. Extend SKILLS for your field.
"""
import re

CS = "CS:"

SKILLS = {
    # languages and query
    "Python": [r"\bpython\b"],
    "SQL": [CS + r"\bSQL\b", r"\bpostgres(ql)?\b", r"\bmysql\b", r"\bt-sql\b"],
    "Scala": [r"\bscala\b"],
    "Java": [r"\bjava\b(?!script)"],
    "Bash": [r"\bbash\b", r"shell script"],
    # processing
    "Apache Spark": [r"\bspark\b", r"\bpyspark\b"],
    "Apache Kafka": [r"\bkafka\b"],
    "Apache Airflow": [r"\bairflow\b"],
    "dbt": [r"\bdbt\b"],
    "Apache Flink": [r"\bflink\b"],
    "pandas": [r"\bpandas\b"],
    "streaming data": [r"\bstreaming\b", r"real[- ]time (data|pipelines?|events?)", r"event[- ]driven"],
    "batch processing": [r"\bbatch (jobs?|processing|pipelines?|loads?)\b"],
    "ETL / ELT": [CS + r"\bETL\b", CS + r"\bELT\b", r"extract, transform,? (and )?load"],
    "data pipelines": [r"data pipelines?", r"ingestion pipelines?"],
    "data modeling": [r"data model(l)?ing", r"dimensional model", r"star schema", r"data vault"],
    "data warehousing": [r"data warehous", r"\bsnowflake\b", r"\bbigquery\b", r"\bredshift\b", r"\bsynapse\b"],
    "data lakes": [r"data lake", r"lakehouse", r"\bdelta lake\b", r"\biceberg\b", r"\bparquet\b"],
    "data quality": [r"data quality", r"great expectations", r"data validation", r"data contracts?"],
    "orchestration": [r"orchestrat", r"\bdagster\b", r"\bprefect\b", r"\bairflow\b"],
    # platforms
    "AWS": [CS + r"\bAWS\b", r"amazon web services", r"\bS3\b", r"\bglue\b", r"\blambda\b", r"\bkinesis\b"],
    "Google Cloud": [CS + r"\bGCP\b", r"google cloud", r"\bbigquery\b", r"\bdataflow\b"],
    "Azure": [r"\bazure\b"],
    "Docker": [r"\bdocker\b", r"\bcontainers?\b"],
    "Kubernetes": [r"\bkubernetes\b", CS + r"\bK8s\b"],
    "Terraform": [r"\bterraform\b", r"infrastructure as code"],
    "CI/CD": [CS + r"\bCI/CD\b", r"continuous (integration|delivery|deployment)", r"github actions", r"\bjenkins\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    # analysis and ML
    "statistics": [r"statistic", r"a/b test", r"hypothesis test", r"experiment design"],
    "machine learning": [r"machine learning", CS + r"\bML\b"],
    "feature stores": [r"feature store", r"\bfeast\b"],
    "dashboards / BI": [r"dashboards?", r"\blooker\b", r"\btableau\b", r"power bi", r"\bmetabase\b"],
    "data governance": [r"data governance", r"data catalog", r"lineage", r"access control"],
    "privacy / PII handling": [CS + r"\bPII\b", r"\bgdpr\b", r"\bhipaa\b", r"personal data", r"data privacy"],
    # ways of working
    "stakeholder communication": [r"stakeholder", r"cross-functional", r"business partners?"],
    "mentoring": [r"mentor"],
    "on-call / reliability": [r"on-call", r"\bSLAs?\b", r"\bSLOs?\b", r"incident", r"reliability"],
    "security clearance": [r"security clearance", r"TS/SCI"],
}

SOFT = {"stakeholder communication", "mentoring"}


def _compile(p):
    return re.compile(p[len(CS):]) if p.startswith(CS) else re.compile(p, re.I)


PATTERNS = {k: [_compile(p) for p in v] for k, v in SKILLS.items()}


def find(text):
    """Canonical skills named anywhere in text."""
    return {k for k, ps in PATTERNS.items() if any(p.search(text) for p in ps)}
