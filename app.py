import io
import os
import re
import webbrowser
from collections import Counter
from typing import List, Tuple
from urllib.parse import quote_plus

from flask import Flask, redirect, render_template, request, url_for

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR

DEFAULT_SKILLS = {
    "it": [
        "python", "java", "c", "c++", "javascript", "html", "css", "sql",
        "flask", "django", "react", "node", "api", "git", "machine learning",
        "data analysis", "mongodb", "mysql", "excel", "aws", "linux"
    ],
    "finance": ["banking", "finance", "accounting", "tally", "excel", "taxation", "audit"],
    "hr": ["recruitment", "payroll", "onboarding", "employee engagement", "communication"],
    "legal": ["legal", "law", "litigation", "contract drafting", "compliance"],
    "teaching": [
        "teaching", "teacher", "tutoring", "online tutoring", "english", "english language",
        "spoken english", "grammar", "ielts", "toefl", "academics", "mentoring",
        "communication skills", "soft skills", "tesol", "education", "lesson planning",
        "classroom management", "personality development", "bed", "pgt", "tgt"
    ],
    "fitness": [
        "fitness", "personal training", "strength training", "weight training", "cardio",
        "nutrition", "wellness", "gym training", "exercise science", "workout planning",
        "client assessment", "injury prevention", "group classes", "yoga", "zumba",
        "first aid", "cpr", "bodybuilding", "fat loss", "weight management"
    ],
    "general": ["communication", "leadership", "teamwork", "problem solving", "time management"]
}

JOB_ROLES = [
    "Sales", "Public Relations", "IT", "HR", "Healthcare", "Fitness",
    "Finance", "Engineering", "Digital Media", "Designer", "Consultant",
    "Construction", "Chef", "Business Development", "Banking", "BPO",
    "Aviation", "Automobile", "Apparel", "Arts", "Agriculture", "Teacher",
    "English Teacher", "Online Tutor", "Teaching Assistant", "Advocate", "Accountant",
    "Python Developer", "Web Developer", "Data Analyst"
]

JOB_SITES = ["LinkedIn", "Naukri", "Indeed", "Glassdoor"]

ROLE_RECOMMENDATIONS = {
    "Fitness": [
        "Fitness Trainer", "Personal Trainer", "Gym Trainer", "Fitness Coach",
        "Wellness Coach", "Group Fitness Instructor"
    ],
    "Teacher": [
        "Teacher", "Academic Mentor", "Teaching Assistant", "Subject Tutor",
        "Curriculum Assistant"
    ],
    "English Teacher": [
        "English Teacher", "Spoken English Trainer", "Online English Tutor",
        "Academic Mentor", "PGT English Teacher"
    ],
    "Online Tutor": [
        "Online Tutor", "Online English Tutor", "Academic Mentor",
        "Teaching Assistant", "Subject Tutor"
    ],
    "Teaching Assistant": [
        "Teaching Assistant", "Academic Mentor", "Classroom Assistant",
        "Subject Tutor"
    ],
    "IT": [
        "IT Support Executive", "System Administrator", "Technical Support Engineer",
        "IT Associate"
    ],
    "Python Developer": [
        "Python Developer", "Backend Developer", "Flask Developer", "Data Analyst"
    ],
    "Web Developer": [
        "Web Developer", "Frontend Developer", "UI Developer", "JavaScript Developer"
    ],
    "Data Analyst": [
        "Data Analyst", "MIS Analyst", "Business Analyst", "Reporting Analyst"
    ],
    "Finance": [
        "Finance Executive", "Financial Analyst", "Accounts Executive",
        "Banking Associate"
    ],
    "Banking": [
        "Banking Associate", "Relationship Officer", "Financial Analyst",
        "Accounts Executive"
    ],
    "Accountant": [
        "Accountant", "Accounts Executive", "Tax Assistant", "Audit Assistant"
    ],
    "Advocate": [
        "Advocate", "Legal Advisor", "Legal Associate", "Contract Analyst"
    ],
    "HR": [
        "HR Executive", "Recruiter", "Talent Acquisition Associate",
        "Payroll Executive"
    ],
}

ROLE_ACTION_VERBS = {
    "Fitness": "trained, coached, assessed, planned, improved, and tracked",
    "Teacher": "taught, developed, mentored, assessed, improved, and delivered",
    "English Teacher": "taught, developed, mentored, assessed, improved, and delivered",
    "Online Tutor": "taught, guided, mentored, assessed, improved, and delivered",
    "Teaching Assistant": "supported, taught, guided, organized, assessed, and improved",
    "IT": "built, configured, troubleshot, automated, supported, and improved",
    "Python Developer": "built, developed, tested, deployed, automated, and improved",
    "Web Developer": "built, developed, optimized, tested, deployed, and improved",
    "Data Analyst": "analyzed, cleaned, visualized, reported, automated, and improved",
    "Finance": "analyzed, reconciled, audited, reported, tracked, and improved",
    "Banking": "handled, verified, reconciled, advised, reported, and improved",
    "Accountant": "reconciled, audited, filed, reported, analyzed, and improved",
    "Advocate": "drafted, reviewed, represented, researched, advised, and negotiated",
    "HR": "recruited, onboarded, coordinated, screened, managed, and improved",
}

ROLE_KEYWORDS = {
    "Sales": ["sales", "lead generation", "customer relationship", "crm", "negotiation", "targets", "pipeline", "closing"],
    "Public Relations": ["public relations", "media relations", "press release", "brand communication", "events", "stakeholder communication"],
    "IT": ["it support", "troubleshooting", "networking", "hardware", "software", "windows", "linux", "ticketing", "system administration"],
    "HR": ["recruitment", "screening", "onboarding", "payroll", "employee engagement", "hr operations", "hrms", "interviewing"],
    "Healthcare": ["patient care", "clinical", "healthcare", "medical records", "vital signs", "care coordination", "first aid"],
    "Fitness": ["fitness", "personal training", "strength training", "cardio", "nutrition", "workout planning", "client assessment", "gym training"],
    "Finance": ["finance", "financial analysis", "accounting", "excel", "budgeting", "taxation", "audit", "reporting"],
    "Engineering": ["engineering", "autocad", "design", "maintenance", "quality control", "project management", "manufacturing"],
    "Digital Media": ["digital media", "social media", "content creation", "campaigns", "seo", "analytics", "video editing"],
    "Designer": ["design", "ui design", "graphic design", "figma", "adobe photoshop", "adobe illustrator", "typography", "branding", "wireframes"],
    "Consultant": ["consulting", "business analysis", "client management", "strategy", "process improvement", "presentation", "research"],
    "Construction": ["construction", "site supervision", "estimation", "safety", "civil engineering", "quality control", "boq"],
    "Chef": ["cooking", "kitchen operations", "menu planning", "food safety", "hygiene", "inventory", "recipe development"],
    "Business Development": ["business development", "lead generation", "market research", "sales", "client acquisition", "partnerships"],
    "Banking": ["banking", "cash handling", "kyc", "customer service", "loans", "financial products", "branch operations"],
    "BPO": ["bpo", "customer support", "voice process", "chat support", "email support", "crm", "call handling"],
    "Aviation": ["aviation", "ground staff", "customer service", "safety", "ticketing", "airport operations", "cabin crew"],
    "Automobile": ["automobile", "vehicle service", "diagnostics", "maintenance", "quality inspection", "automotive systems"],
    "Apparel": ["apparel", "fashion", "merchandising", "garment", "textile", "quality check", "production coordination"],
    "Arts": ["arts", "creative", "illustration", "painting", "visual arts", "portfolio", "exhibition", "composition"],
    "Agriculture": ["agriculture", "crop management", "soil", "irrigation", "farm operations", "fertilizer", "pest management"],
    "Teacher": ["teaching", "lesson planning", "classroom management", "assessment", "curriculum", "student mentoring"],
    "English Teacher": ["english", "teaching english", "grammar", "spoken english", "literature", "lesson planning", "student mentoring"],
    "Online Tutor": ["online tutoring", "virtual teaching", "lesson planning", "student mentoring", "assessment", "communication"],
    "Teaching Assistant": ["teaching assistant", "classroom support", "lesson preparation", "student support", "assessment", "education"],
    "Advocate": ["law", "legal", "litigation", "contract drafting", "legal research", "compliance", "case management"],
    "Accountant": ["accounting", "tally", "gst", "taxation", "reconciliation", "audit", "ledger", "excel"],
    "Python Developer": ["python", "flask", "django", "api", "sql", "git", "backend", "testing"],
    "Web Developer": ["html", "css", "javascript", "react", "responsive design", "web development", "git", "api"],
    "Data Analyst": ["data analysis", "sql", "excel", "python", "dashboard", "power bi", "statistics", "reporting"],
}

all_skills: List[str] = []


def clean(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9+# ]", " ", (text or "").lower())


def preprocess(text: str) -> str:
    return re.sub(r"\s+", " ", clean(text)).strip()


def build_job_search_links(role: str):
    role = (role or "").strip()
    encoded = quote_plus(role)
    slug = role.lower().replace(" ", "-")
    return {
        "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={encoded}",
        "Naukri": f"https://www.naukri.com/{slug}-jobs" if slug else "https://www.naukri.com/",
        "Indeed": f"https://in.indeed.com/jobs?q={encoded}",
        "Glassdoor": f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded}",
    }


def load_skills() -> List[str]:
    skills: List[str] = []

    skills_csv = os.path.join(BASE_DIR, "skills_dataset.csv")
    jobs_csv = os.path.join(BASE_DIR, "all_job_post.csv")

    if pd is not None and os.path.exists(skills_csv):
        try:
            skills_df = pd.read_csv(skills_csv)
            skills_df.columns = skills_df.columns.str.strip().str.lower()
            skills_df.rename(columns={"domain": "category", "skil": "skill", "skills": "skill"}, inplace=True)
            if "skill" in skills_df.columns:
                skills.extend(skills_df["skill"].dropna().astype(str).str.lower().tolist())
        except Exception:
            pass

    if pd is not None and os.path.exists(jobs_csv):
        try:
            jobs_df = pd.read_csv(jobs_csv)
            jobs_df.columns = jobs_df.columns.str.strip().str.lower()
            if "job_skill_set" in jobs_df.columns:
                for raw in jobs_df["job_skill_set"].dropna().astype(str):
                    skills.extend(re.findall(r"[A-Za-z+# ]+", raw.lower()))
        except Exception:
            pass

    if not skills:
        for values in DEFAULT_SKILLS.values():
            skills.extend(values)

    for values in ROLE_KEYWORDS.values():
        skills.extend(values)

    skills = sorted({s.strip().lower() for s in skills if s and len(s.strip()) > 1})
    return skills


def extract_text_from_file(file_storage) -> str:
    filename = (file_storage.filename or "").lower()
    data = file_storage.read()
    file_storage.seek(0)

    if filename.endswith(".pdf") and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""

    if filename.endswith(".docx") and Document is not None:
        try:
            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""

    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_skills(text: str) -> List[str]:
    text = preprocess(text)
    found = []
    padded = f" {text} "
    for skill in all_skills:
        normalized_skill = preprocess(skill)
        if not normalized_skill:
            continue
        if f" {normalized_skill} " in padded:
            found.append(skill)
        elif fuzz is not None and len(normalized_skill) > 3:
            try:
                if fuzz.partial_ratio(normalized_skill, text) > 95:
                    found.append(skill)
            except Exception:
                pass
    return sorted(set(found))


def skill_gap(resume_skills: List[str], jd_skills: List[str]) -> Tuple[List[str], List[str]]:
    matched = sorted(set(resume_skills) & set(jd_skills))
    missing = sorted(set(jd_skills) - set(resume_skills))
    return matched, missing


def get_priority_missing_skills(missing: List[str], jd_text: str) -> List[str]:
    jd_text = preprocess(jd_text)
    return sorted(missing, key=lambda skill: jd_text.count(preprocess(skill)), reverse=True)[:5]


def get_keyword_suggestions(resume_text: str, jd_text: str, limit: int = 8) -> List[str]:
    resume_words = set(preprocess(resume_text).split())
    jd_words = preprocess(jd_text).split()
    stop_words = {
        "and", "the", "for", "with", "you", "are", "our", "this", "that", "from",
        "will", "have", "has", "job", "role", "work", "team", "your", "skills",
        "experience", "candidate", "required", "preferred", "ability"
    }
    keywords = [
        word for word in jd_words
        if len(word) > 3 and word not in stop_words and word not in resume_words
    ]
    return [word for word, _ in Counter(keywords).most_common(limit)]


def get_resume_stats(resume_text: str) -> dict:
    lower = resume_text.lower()
    words = preprocess(resume_text).split()
    section_names = ["education", "experience", "skills", "projects", "certifications", "summary"]
    found_sections = [section.title() for section in section_names if section in lower]
    return {
        "word_count": len(words),
        "sections_found": found_sections,
        "section_score": int((len(found_sections) / len(section_names)) * 100),
    }


def coverage_score(candidates: List[str], text: str) -> float:
    normalized_text = f" {preprocess(text)} "
    normalized_candidates = [preprocess(item) for item in candidates if preprocess(item)]
    if not normalized_candidates:
        return 0.0
    matched = [
        item for item in normalized_candidates
        if f" {item} " in normalized_text
    ]
    return len(set(matched)) / len(set(normalized_candidates))


def keyword_coverage_score(resume: str, jd: str, limit: int = 20) -> float:
    resume_words = set(preprocess(resume).split())
    jd_words = preprocess(jd).split()
    stop_words = {
        "and", "the", "for", "with", "you", "are", "our", "this", "that", "from",
        "will", "have", "has", "job", "role", "work", "team", "your", "skills",
        "experience", "candidate", "required", "preferred", "ability", "should",
        "good", "full", "time", "type", "summary", "company", "location"
    }
    important_words = [
        word for word, _ in Counter(jd_words).most_common()
        if len(word) > 3 and word not in stop_words
    ][:limit]
    if not important_words:
        return 0.0
    return len(set(important_words) & resume_words) / len(set(important_words))


def role_alignment_score(resume: str, jd: str, selected_role: str) -> float:
    if not selected_role:
        return 0.0

    role_words = preprocess(selected_role).split()
    role_keywords = ROLE_KEYWORDS.get(selected_role, role_words)
    keywords = sorted(set(role_words + role_keywords))
    resume_role = coverage_score(keywords, resume)
    jd_role = coverage_score(keywords, jd)
    return min((0.75 * resume_role) + (0.25 * jd_role), 1.0)


def jd_similarity(resume: str, jd: str, selected_role: str = ""):
    resume_p = preprocess(resume)
    jd_p = preprocess(jd)

    if SKLEARN_OK:
        temp_vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        mat = temp_vectorizer.fit_transform([resume_p, jd_p])
        cos = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
    else:
        res_words = set(resume_p.split())
        jd_words = set(jd_p.split())
        union = len(res_words | jd_words) or 1
        cos = len(res_words & jd_words) / union

    res_sk = extract_skills(resume)
    jd_sk = extract_skills(jd)

    overlap = len(set(res_sk) & set(jd_sk)) / max(len(jd_sk), 1) if jd_sk else 0.0
    keyword_coverage = keyword_coverage_score(resume, jd)
    role_relevance = role_alignment_score(resume, jd, selected_role)
    skill_score = min((0.65 * overlap) + (0.20 * keyword_coverage) + (0.15 * role_relevance), 1.0)
    score = min((0.45 * skill_score) + (0.25 * keyword_coverage) + (0.20 * role_relevance) + (0.10 * cos), 1.0)
    return int(score * 100), cos, skill_score, keyword_coverage, role_relevance, res_sk, jd_sk


def detect_experience(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["intern", "internship", "fresher"]):
        return "Fresher"

    year_matches = re.findall(r"(\d+)\+?\s+years?", lower)
    if year_matches:
        total = max(int(x) for x in year_matches)
        return f"Experienced ({total}+ years)"

    years = re.findall(r"(20\d{2}|19\d{2})", lower)
    if len(years) >= 2:
        nums = sorted({int(y) for y in years})
        approx = max(0, nums[-1] - nums[0])
        if approx > 0:
            return f"Experienced ({approx}+ years approx.)"

    return "Unknown"


def get_resume_strength_level(match_percentage: int) -> Tuple[str, str]:
    if match_percentage <= 30:
        return "Weak Profile", "weak"
    if match_percentage <= 60:
        return "Average Profile", "average"
    if match_percentage <= 80:
        return "Strong Profile", "strong"
    return "Excellent Profile", "excellent"


def improvement_tips(missing: List[str], selected_role: str) -> List[str]:
    tips = [f"Add '{s}' to your resume if you really know it." for s in missing[:5]]
    if selected_role:
        tips.append(f"You selected {selected_role}. Tailor your summary and skills section toward that role.")
    verbs = ROLE_ACTION_VERBS.get(
        selected_role,
        "built, developed, analyzed, improved, delivered, and supported"
    )
    tips.extend([
        f"Use strong action verbs like {verbs}.",
        "Add measurable achievements like number of students, results, certifications, or tools used.",
        "Keep your resume wording close to the job description where truthful."
    ])
    return tips[:8]


def recommend_jobs(skills: List[str], selected_role: str = "") -> List[str]:
    joined = " ".join(skills)
    jobs = []

    if selected_role in ROLE_RECOMMENDATIONS:
        jobs.extend(ROLE_RECOMMENDATIONS[selected_role])
    elif selected_role:
        jobs.append(selected_role)

    if not selected_role:
        if "legal" in joined or "law" in joined:
            jobs.extend(["Lawyer", "Legal Advisor", "Advocate"])
        if any(x in joined for x in ["python", "flask", "sql"]):
            jobs.extend(["Python Developer", "Backend Developer", "Data Analyst"])
        if any(x in joined for x in ["banking", "finance", "accounting"]):
            jobs.extend(["Banking Associate", "Financial Analyst", "Accounts Executive"])
        if any(x in joined for x in ["html", "css", "javascript"]):
            jobs.extend(["Frontend Developer", "Web Developer", "UI Developer"])
        if any(x in joined for x in ["fitness", "training", "gym", "cardio", "nutrition", "wellness"]):
            jobs.extend(ROLE_RECOMMENDATIONS["Fitness"])
        if any(x in joined for x in ["teacher", "teaching", "tutoring", "english", "grammar", "ielts", "toefl", "education"]):
            jobs.extend(ROLE_RECOMMENDATIONS["English Teacher"])

    if not jobs:
        jobs = ["General Role", "Trainee", "Associate"]
    deduped = []
    for job in jobs:
        if job not in deduped:
            deduped.append(job)
    return deduped[:6]


def role_fit_message(selected_role: str, score: int) -> str:
    if score >= 65:
        return f"Strong fit for {selected_role}." if selected_role else "Strong fit. Your resume is fairly aligned with this job."
    if score >= 40:
        return "Moderate fit. Improve a few missing skills and keywords."
    return "Low fit right now. Tailor the resume more for this role."


def build_report_text(result: dict) -> str:
    missing = ", ".join(result["missing_skills"]) if result["missing_skills"] else "None"
    priority_missing = ", ".join(result["priority_missing_skills"]) if result["priority_missing_skills"] else "None"
    keyword_suggestions = ", ".join(result["keyword_suggestions"]) if result["keyword_suggestions"] else "None"
    sections = ", ".join(result["sections_found"]) if result["sections_found"] else "None detected"
    tips = "\n".join(f"- {tip}" for tip in result["tips"])

    return f"""Resume Skill Gap Analysis Report

Selected Role: {result["selected_role"]}
Match Percentage: {result["match_percentage"]}%
Resume Strength Level: {result["resume_strength_level"]}
Skill Match: {result["skill_match"]}%
Role Relevance: {result["role_relevance"]}%
Experience: {result["experience"]}
Resume Word Count: {result["word_count"]}
Sections Found: {sections}

Missing Skills: {missing}
Priority Missing Skills: {priority_missing}
JD Keywords To Add: {keyword_suggestions}

Improvement Tips:
{tips}
"""


all_skills = load_skills()


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    resume_filename = ""
    jd_text = ""
    selected_role = ""
    selected_site = JOB_SITES[0]
    job_links = build_job_search_links(selected_role)

    if request.method == "POST":
        jd_text = request.form.get("job_description", "")
        uploaded_file = request.files.get("resume_file")
        selected_role = request.form.get("job_role", "").strip()
        selected_site = request.form.get("job_site", JOB_SITES[0])
        job_links = build_job_search_links(selected_role)

        resume_text = ""
        if uploaded_file and uploaded_file.filename:
            resume_filename = uploaded_file.filename
            resume_text = extract_text_from_file(uploaded_file)

        if not preprocess(resume_text):
            error = "Please upload a resume file."
        elif not selected_role:
            error = "Please select a job role."
        elif not preprocess(jd_text):
            error = "Please paste the job description."
        else:
            score, cos, skill_score, keyword_coverage, role_relevance, res_sk, jd_sk = jd_similarity(
                resume_text,
                jd_text,
                selected_role,
            )
            matched, missing = skill_gap(res_sk, jd_sk)
            strength_level, strength_class = get_resume_strength_level(score)
            skill_match = int(skill_score * 100)
            keyword_score = int(keyword_coverage * 100)
            resume_stats = get_resume_stats(resume_text)
            result = {
                "experience": detect_experience(resume_text),
                "match_percentage": score,
                "resume_strength_level": strength_level,
                "strength_class": strength_class,
                "matched_skills": matched,
                "missing_skills": missing,
                "text_similarity": int(cos * 100),
                "skill_match": skill_match,
                "keyword_score": keyword_score,
                "role_relevance": int(role_relevance * 100),
                "priority_missing_skills": get_priority_missing_skills(missing, jd_text),
                "keyword_suggestions": get_keyword_suggestions(resume_text, jd_text),
                "word_count": resume_stats["word_count"],
                "sections_found": resume_stats["sections_found"],
                "section_score": resume_stats["section_score"],
                "tips": improvement_tips(missing, selected_role),
                "recommended_jobs": recommend_jobs(res_sk + jd_sk, selected_role),
                "resume_preview": resume_text[:1200],
                "selected_role": selected_role,
                "fit_message": role_fit_message(selected_role, score),
            }
            result["report_text"] = build_report_text(result)

    return render_template(
        "index.html",
        result=result,
        error=error,
        jd_text=jd_text,
        resume_filename=resume_filename,
        job_roles=JOB_ROLES,
        job_sites=JOB_SITES,
        selected_role=selected_role,
        selected_site=selected_site,
        job_links=job_links,
    )


@app.route("/open-job-site")
def open_job_site():
    role = request.args.get("role", "").strip()
    site = request.args.get("site", JOB_SITES[0])
    links = build_job_search_links(role)
    target_url = links.get(site, links[JOB_SITES[0]])
    webbrowser.open_new_tab(target_url)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
