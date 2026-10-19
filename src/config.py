import os

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
)
os.makedirs(DATA_DIR, exist_ok=True)

Q_TABLE_PATH = os.path.join(DATA_DIR, "q_table.json")

EXPERTISE_LEVELS = ["intern", "junior", "mid", "senior", "lead", "principal"]

ROLE_FAMILIES = [
    "software_engineering",
    "data_science",
    "design",
    "marketing",
    "product_management",
    "sales",
    "customer_support",
    "finance",
    "human_resources",
    "operations",
    "legal",
    "healthcare",
    "education",
    "research",
    "engineering_hardware",
    "qa_testing",
    "devops_infra",
    "security",
    "content_writing",
    "project_management",
]

SPECIALTIES = {
    "software_engineering": ["backend", "frontend", "fullstack", "mobile", "game_dev", "embedded", "api", "web", "cloud"],
    "data_science": ["machine_learning", "nlp", "computer_vision", "analytics", "data_engineering", "bi", "deep_learning"],
    "design": ["ux", "ui", "product", "graphic", "interaction", "motion", "brand", "visual"],
    "marketing": ["digital", "content", "seo", "growth", "brand", "social_media", "email", "ppc"],
    "product_management": ["technical", "growth", "platform", "consumer", "b2b", "saas"],
    "sales": ["inside", "field", "enterprise", "smb", "account_executive", "sdr"],
    "customer_support": ["technical", "customer_success", "helpdesk", "chat", "onboarding"],
    "finance": ["accounting", "fp&a", "investment", "risk", "audit", "tax"],
    "human_resources": ["recruiting", "talent", "people_ops", "compensation", "hrbp"],
    "operations": ["business", "supply_chain", "logistics", "process", "revops"],
    "legal": ["corporate", "compliance", "ip", "contracts", "privacy"],
    "healthcare": ["nursing", "clinical", "admin", "pharma", "research"],
    "education": ["teacher", "tutor", "curriculum", "edtech", "instructional_design"],
    "research": ["academic", "industry", "applied", "r&d", "postdoc"],
    "engineering_hardware": ["mechanical", "electrical", "civil", "chemical", "robotics"],
    "qa_testing": ["manual", "automation", "performance", "security", "sdet"],
    "devops_infra": ["sre", "platform", "cloud", "kubernetes", "ci_cd"],
    "security": ["appsec", "network", "cloud_security", "pentest", "grc"],
    "content_writing": ["copywriting", "technical_writing", "editorial", "blog", "ghostwriting"],
    "project_management": ["scrum", "agile", "technical_pm", "program", "delivery"],
}


def get_specialties(role_family: str) -> list:
    return SPECIALTIES.get(role_family, ["general"])

# ── Skills catalogue (grouped for the UI; users can type custom ones too) ──
SKILL_CATALOG = {
    "programming": [
        "python", "javascript", "typescript", "java", "c#", "c++", "go", "rust",
        "php", "ruby", "kotlin", "swift", "sql", "bash", "r",
    ],
    "web": ["react", "vue", "angular", "next.js", "node.js", "django", "flask",
            "fastapi", "spring", "laravel", "html", "css", "tailwind"],
    "data": ["pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
             "spark", "airflow", "dbt", "tableau", "power bi", "excel"],
    "cloud_devops": ["aws", "gcp", "azure", "docker", "kubernetes", "terraform",
                     "jenkins", "github actions", "linux", "git"],
    "design": ["figma", "sketch", "adobe xd", "photoshop", "illustrator",
               "after effects", "canva"],
    "marketing": ["seo", "google ads", "meta ads", "hubspot", "mailchimp",
                  "google analytics", "copywriting"],
    "soft": ["comunicacao", "trabalho em equipe", "lideranca", "proatividade",
             "organizacao", "ingles", "espanhol"],
}

# University period options (Brazil: 1–10 semesters typical)
PERIOD_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
PERIOD_LABELS = ["Any / não sou estudante"] + [f"{i}º semestre" for i in range(1, 11)]

# Caminho do .env (na raiz do projeto)
ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".env",
)