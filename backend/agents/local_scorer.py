"""
Fast keyword-based local scorer — runs instantly, no API needed.
Title-weighted: exact title match is worth much more than description mentions.
"""

# Salary target
MIN_SALARY = 90000

# --- Title keywords (checked against job TITLE only) ---
# These indicate a direct role match
TITLE_ROLE_KEYWORDS = {
    "programme director": 40,
    "program director": 40,
    "delivery director": 40,
    "head of delivery": 40,
    "director of delivery": 38,
    "head of pmo": 35,
    "principal programme": 35,
    "vp delivery": 35,
    "head of technology delivery": 35,
    "vp of delivery": 35,
    "senior programme manager": 30,
    "programme manager": 25,
    "delivery manager": 22,
    "project director": 30,
    "head of transformation": 30,
    "transformation director": 32,
    "digital transformation": 20,
    "head of change": 28,
    "head of product delivery": 35,
    "principal consultant": 22,
    "engagement manager": 18,
    "portfolio director": 30,
    "portfolio manager": 22,
    "head of portfolio": 32,
    "vp programme": 35,
    "chief of staff": 18,
}

# --- Description / context keywords (lower weight) ---
CONTEXT_KEYWORDS = {
    "programme governance": 12,
    "stakeholder management": 10,
    "agile": 8,
    "waterfall": 6,
    "pmo": 10,
    "transformation": 8,
    "budget": 6,
    "risk management": 8,
    "change management": 8,
    "scrum": 5,
    "governance": 8,
    "cross-functional": 7,
    "enterprise": 5,
    "p&l": 8,
    "strategic": 5,
    "roadmap": 5,
    "delivery governance": 12,
    "programme management": 10,
    "project management": 6,
    "consulting": 7,
    "professional services": 7,
    "technology": 4,
    "digital": 4,
    "financial services": 5,
    "fintech": 6,
    "saas": 5,
}

# --- Negative signals ---
NEGATIVE_KEYWORDS = {
    "junior": -20,
    "graduate scheme": -25,
    "internship": -30,
    "entry level": -25,
    "apprentice": -25,
    "game developer": -10,
    "game designer": -10,
    "quantity surveyor": -15,
    "civil engineer": -10,
    "social care": -10,
    "teaching": -15,
    "nursing": -20,
    "clinical": -8,
}


def local_score(job_data: dict) -> int:
    title = (job_data.get("title") or "").lower()
    description = (job_data.get("description") or "").lower()
    company = (job_data.get("company") or "").lower()
    full_text = f"{title} {description} {company}"

    raw = 0

    # Title role match — high weight
    title_match = False
    for kw, weight in TITLE_ROLE_KEYWORDS.items():
        if kw in title:
            raw += weight
            title_match = True
            break  # Only count the best title match

    # Context keywords (in full text including description)
    for kw, weight in CONTEXT_KEYWORDS.items():
        if kw in full_text:
            raw += weight

    # Negative signals
    for kw, penalty in NEGATIVE_KEYWORDS.items():
        if kw in full_text:
            raw += penalty  # penalty is negative

    # Salary bonus
    sal_min = job_data.get("salary_min")
    if sal_min and sal_min >= MIN_SALARY:
        raw += 8
    elif sal_min and sal_min < 60000:
        raw -= 15

    # Remote bonus (Eugenio may want remote)
    if job_data.get("remote"):
        raw += 3

    # Normalise:
    # - 60 raw points → 100% (a perfect title match + many skills)
    # - 40 raw points → ~67% (good title match + some skills)
    # - 20 raw points → ~33% (weak match)
    # Floor at 10, cap at 95 (leave room for Claude to exceed)
    DENOM = 60
    score = int(min(95, max(10, round((raw / DENOM) * 100))))
    return score


def local_score_reason(job_data: dict) -> str:
    title = (job_data.get("title") or "").lower()
    description = (job_data.get("description") or "").lower()
    full_text = f"{title} {description}"

    matched_roles = [kw for kw in TITLE_ROLE_KEYWORDS if kw in title]
    matched_skills = [kw for kw in CONTEXT_KEYWORDS if kw in full_text and CONTEXT_KEYWORDS[kw] >= 8]

    parts = []
    if matched_roles:
        parts.append(f"Role: {matched_roles[0]}")
    if matched_skills:
        parts.append(f"Skills: {', '.join(matched_skills[:3])}")

    if not parts:
        return "Limited keyword match — check description manually"
    return " · ".join(parts)


def local_score_gaps(job_data: dict) -> str:
    """
    Returns a short paragraph describing what's missing from the profile for this job.
    Used as a placeholder score_suggestion until Claude provides a real one.
    """
    title = (job_data.get("title") or "").lower()
    description = (job_data.get("description") or "").lower()
    full_text = f"{title} {description}"

    # Missing role-level match
    title_matched = any(kw in title for kw in TITLE_ROLE_KEYWORDS)

    # High-value context keywords that are missing
    missing_skills = [
        kw for kw, weight in CONTEXT_KEYWORDS.items()
        if weight >= 8 and kw not in full_text
    ]

    parts = []
    if not title_matched:
        parts.append("Title doesn't match target roles (programme director / head of delivery / delivery director)")

    if missing_skills[:4]:
        parts.append(f"Keywords not found in description: {', '.join(missing_skills[:4])}")

    if not parts:
        return "Strong keyword match — awaiting Claude analysis for deeper fit assessment."

    return "Gap analysis (keyword): " + " · ".join(parts)
