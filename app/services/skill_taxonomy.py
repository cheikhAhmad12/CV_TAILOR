from typing import Dict, List

SKILL_GROUPS: Dict[str, List[str]] = {
    "python": ["python"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django", "drf", "django rest"],
    "docker": ["docker", "container", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "sql": ["sql", "postgres", "postgresql", "mysql", "sqlite"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "keras"],
    "llm": ["llm", "large language model", "gpt", "llama", "mistral", "transformers"],
    "rag": ["rag", "retrieval augmented generation", "vector search"],
    "nlp": ["nlp", "natural language processing", "text mining"],
    "ml": ["machine learning", "ml", "scikit-learn", "sklearn"],
    "deep_learning": ["deep learning", "neural network", "neural networks"],
    "apis": ["api", "apis", "rest api", "rest", "backend api"],
    "aws": ["aws", "amazon web services"],
    "git": ["git", "github", "gitlab"],
    "faiss": ["faiss"],
    "langchain": ["langchain"],
    "streamlit": ["streamlit"],
}

PRETTY_MAP = {
    "llm": "LLM",
    "rag": "RAG",
    "nlp": "NLP",
    "ml": "Machine Learning",
    "deep_learning": "Deep Learning",
    "apis": "API Development",
    "sql": "SQL",
    "aws": "AWS",
    "faiss": "FAISS",
    "langchain": "LangChain",
    "fastapi": "FastAPI",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "docker": "Docker",
    "git": "Git",
    "python": "Python",
    "flask": "Flask",
    "django": "Django",
    "kubernetes": "Kubernetes",
    "streamlit": "Streamlit",
}


def extract_skills_from_text(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for canonical, variants in SKILL_GROUPS.items():
        for variant in variants:
            if variant in text_lower:
                found.append(canonical)
                break
    return found


def pretty_skill(skill: str) -> str:
    return PRETTY_MAP.get(skill, skill.title())