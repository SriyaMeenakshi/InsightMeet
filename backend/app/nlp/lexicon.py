"""Small domain lexicons used for entities, components and topic grouping.

These are deliberately transparent word lists (not a trained model) so that
every match can be explained to the user.
"""
import re

# technology name -> category
TECH_LEXICON: dict[str, str] = {
    "python": "language", "java": "language", "javascript": "language",
    "typescript": "language", "golang": "language", "rust": "language",
    "c++": "language", "kotlin": "language", "swift": "language",
    "react": "frontend framework", "vue": "frontend framework",
    "angular": "frontend framework", "next.js": "frontend framework",
    "nextjs": "frontend framework", "svelte": "frontend framework",
    "flutter": "frontend framework",
    "fastapi": "backend framework", "flask": "backend framework",
    "django": "backend framework", "express": "backend framework",
    "spring": "backend framework", "node": "backend framework",
    "node.js": "backend framework", "nodejs": "backend framework",
    "postgres": "database", "postgresql": "database", "mysql": "database",
    "sqlite": "database", "mongodb": "database", "mongo": "database",
    "redis": "database", "firebase": "database", "oracle": "database",
    "aws": "cloud", "azure": "cloud", "gcp": "cloud", "docker": "cloud",
    "kubernetes": "cloud", "vercel": "cloud", "heroku": "cloud",
    "netlify": "cloud", "render": "cloud",
    "github": "tooling", "gitlab": "tooling", "jira": "tooling",
    "figma": "tooling", "slack": "tooling", "trello": "tooling",
    "notion": "tooling", "postman": "tooling", "jenkins": "tooling",
    "tensorflow": "ml", "pytorch": "ml", "scikit-learn": "ml",
    "sklearn": "ml", "spacy": "ml", "nltk": "ml", "bert": "ml",
    "tailwind": "styling", "bootstrap": "styling",
}

_TECH_RE = re.compile(
    r"(?<![\w.])(" + "|".join(
        re.escape(t) for t in sorted(TECH_LEXICON, key=len, reverse=True)
    ) + r")(?![\w])",
    re.IGNORECASE,
)

DISPLAY_TECH = {
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "mysql": "MySQL",
    "sqlite": "SQLite", "mongodb": "MongoDB", "mongo": "MongoDB",
    "fastapi": "FastAPI", "nextjs": "Next.js", "next.js": "Next.js",
    "javascript": "JavaScript", "typescript": "TypeScript",
    "github": "GitHub", "gitlab": "GitLab", "aws": "AWS", "gcp": "GCP",
    "nodejs": "Node.js", "node.js": "Node.js", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "scikit-learn": "scikit-learn", "sklearn": "scikit-learn",
    "spacy": "spaCy", "nltk": "NLTK", "bert": "BERT", "figma": "Figma",
    "jira": "Jira", "redis": "Redis", "docker": "Docker", "react": "React",
    "vue": "Vue", "angular": "Angular", "python": "Python", "java": "Java",
}


def display_tech(name: str) -> str:
    return DISPLAY_TECH.get(name.lower(), name.capitalize())


def find_tech(text: str) -> list[tuple[str, str, int, int]]:
    """Return (display_name, category, start, end) for each technology mention."""
    return [
        (display_tech(m.group(1)), TECH_LEXICON[m.group(1).lower()], m.start(1), m.end(1))
        for m in _TECH_RE.finditer(text)
    ]


# component (what a team works on) -> trigger words
COMPONENT_TERMS: dict[str, list[str]] = {
    "Frontend": ["frontend", "front-end", "front end", "ui", "ux", "interface",
                 "dashboard", "landing page", "webpage", "web page", "screens"],
    "Backend / API": ["backend", "back-end", "back end", "api", "apis", "server",
                      "endpoint", "endpoints", "microservice"],
    "Database": ["database", "db", "schema", "tables", "migration", "migrations", "queries"],
    "Authentication": ["login", "log in", "auth", "authentication", "signup",
                       "sign-up", "sign up", "password", "oauth", "sso"],
    "Testing": ["testing", "tests", "test", "qa", "unit tests", "integration tests",
                "regression", "test cases"],
    "Deployment": ["deployment", "deploy", "deploying", "hosting", "pipeline",
                   "ci/cd", "cicd", "release", "staging", "production"],
    "Documentation": ["documentation", "docs", "readme", "report", "slides",
                      "presentation", "write-up", "writeup"],
    "Design": ["design", "mockup", "mockups", "wireframe", "wireframes",
               "prototype", "branding"],
    "NLP / Model": ["model", "classifier", "training", "dataset", "nlp",
                    "accuracy", "embeddings", "pipeline model"],
    "Budget": ["budget", "cost", "costs", "pricing", "licence", "license"],
    "Demo": ["demo", "demonstration", "viva", "showcase"],
}

_COMPONENT_RES = {
    name: re.compile(
        r"(?<![\w-])(?:" + "|".join(
            re.escape(t) for t in sorted(terms, key=len, reverse=True)
        ) + r")(?![\w-])",
        re.IGNORECASE,
    )
    for name, terms in COMPONENT_TERMS.items()
}


def find_components(text: str) -> list[str]:
    return [name for name, rx in _COMPONENT_RES.items() if rx.search(text)]


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

# Capitalised words that start sentences but are not people.
NOT_PEOPLE = {
    "we", "they", "the", "it", "this", "that", "there", "here", "everyone",
    "someone", "somebody", "nobody", "team", "okay", "ok", "yes", "yeah", "no",
    "so", "and", "but", "also", "then", "please", "sure", "fine", "maybe",
    "perhaps", "testing", "login", "frontend", "backend", "database", "api",
    "dashboard", "deployment", "documentation", "design", "demo", "sprint",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "today", "tomorrow",
    "note", "agenda", "action", "actions", "summary", "todo", "decision",
    "decisions", "topic", "issue", "issues", "next", "update", "updates",
    "meeting", "project", "client", "all", "good", "great", "right", "well",
    "now", "just", "actually", "anyway", "hi", "hello", "thanks", "thank",
    "what", "who", "when", "where", "why", "how", "can", "could", "should",
    "would", "will", "let", "lets", "i", "you", "he", "she",
} | set(TECH_LEXICON)

NOT_SPEAKER_LABELS = {
    "note", "notes", "agenda", "action", "actions", "action item", "summary", "todo",
    "to do", "decision", "decisions", "topic", "topics", "issue", "issues", "next",
    "update", "updates", "date", "time", "attendees", "attendance", "participants",
    "subject", "re", "fyi", "important", "reminder", "warning", "example", "question",
    "answer", "q", "a", "step", "steps", "total", "status", "meeting", "title",
}
