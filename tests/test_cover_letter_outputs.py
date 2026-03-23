from types import SimpleNamespace

import app.models.job  # noqa: F401
import app.models.profile  # noqa: F401
import app.models.user  # noqa: F401
from app.models.application import ApplicationVersion
from app.routers.exports import download_letter
from app.services import tailoring_engine


class FakeDB:
    def __init__(self, profile, job):
        self.profile = profile
        self.job = job
        self.added = None

    def get(self, model, object_id):
        if object_id == self.profile.id:
            return self.profile
        if object_id == self.job.id:
            return self.job
        return None

    def add(self, obj):
        self.added = obj

    def commit(self):
        return None

    def refresh(self, obj):
        obj.id = 999


def _make_profile():
    return SimpleNamespace(
        id=11,
        user_id=1,
        master_cv_text="CV source",
        master_cv_latex="\\documentclass{article}\\begin{document}cv\\end{document}",
        master_cover_letter_text="Lettre master texte",
        master_cover_letter_latex="\\documentclass{article}\\begin{document}lettre\\end{document}",
        github_username="",
        parsed_summary_json="{}",
    )


def _make_job():
    return SimpleNamespace(
        id=22,
        user_id=1,
        raw_text="ML Engineer role",
        parsed_json="{}",
    )


def _patch_common(monkeypatch):
    monkeypatch.setattr(
        tailoring_engine,
        "parse_cv",
        lambda _: {"summary": "cv", "skills": ["Python"], "experiences": [], "education": [], "projects": []},
    )
    monkeypatch.setattr(
        tailoring_engine,
        "parse_job_description",
        lambda _: {
            "title": "ML Engineer",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "responsibilities": [],
            "keywords": ["Python", "LLM"],
        },
    )
    monkeypatch.setattr(
        tailoring_engine,
        "rank_projects",
        lambda projects, parsed_job: [
            {
                "name": "demo",
                "score": 80.0,
                "reason": "fit",
                "description": "desc",
                "readme_summary": "",
                "languages": ["Python"],
                "topics": ["llm"],
                "html_url": "",
            }
        ],
    )
    monkeypatch.setattr(tailoring_engine, "generate_tailored_summary", lambda *args, **kwargs: "summary")
    monkeypatch.setattr(tailoring_engine, "generate_experience_bullets", lambda *args, **kwargs: ["bullet"])
    monkeypatch.setattr(tailoring_engine, "generate_resume_markdown", lambda *args, **kwargs: "# CV")
    monkeypatch.setattr(tailoring_engine, "compute_compatibility_score", lambda *args, **kwargs: 91.5)
    monkeypatch.setattr(tailoring_engine, "compute_ats_score", lambda *args, **kwargs: 88.0)
    monkeypatch.setattr(tailoring_engine, "export_resume_to_docx", lambda *_: "/tmp/resume.docx")
    monkeypatch.setattr(tailoring_engine, "export_latex_to_pdf_with_tectonic", lambda **_: "/tmp/resume.pdf")
    monkeypatch.setattr(
        tailoring_engine,
        "generate_cover_letter_with_llm",
        lambda *args, **kwargs: "Lettre adaptee",
    )
    monkeypatch.setattr(
        tailoring_engine,
        "generate_cover_letter",
        lambda *args, **kwargs: "Lettre fallback",
    )


def test_tailoring_uses_pdf_letter_when_latex_template_exists(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        tailoring_engine,
        "generate_cover_letter_latex_with_llm",
        lambda **kwargs: "\\documentclass{article}\\begin{document}tailored\\end{document}",
    )
    monkeypatch.setattr(tailoring_engine, "export_cover_letter_to_tex", lambda *_: "/tmp/letter.tex")
    monkeypatch.setattr(tailoring_engine, "export_cover_letter_latex_to_pdf", lambda *_: "/tmp/letter.pdf")
    monkeypatch.setattr(
        tailoring_engine,
        "export_cover_letter_to_txt",
        lambda *_: (_ for _ in ()).throw(AssertionError("txt fallback should not be used")),
    )

    db = FakeDB(_make_profile(), _make_job())

    result = tailoring_engine.run_tailoring_engine(
        db=db,
        current_user_id=1,
        profile_id=11,
        job_posting_id=22,
        github_projects=[],
        use_llm=True,
    )

    assert result["cover_letter_path"] == "/tmp/letter.pdf"
    assert result["cover_letter"] == "Lettre adaptee"
    assert isinstance(db.added, ApplicationVersion)


def test_tailoring_falls_back_to_txt_when_latex_letter_generation_fails(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        tailoring_engine,
        "generate_cover_letter_latex_with_llm",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("latex failed")),
    )
    monkeypatch.setattr(tailoring_engine, "export_cover_letter_to_txt", lambda *_: "/tmp/letter.txt")

    db = FakeDB(_make_profile(), _make_job())

    result = tailoring_engine.run_tailoring_engine(
        db=db,
        current_user_id=1,
        profile_id=11,
        job_posting_id=22,
        github_projects=[],
        use_llm=True,
    )

    assert result["cover_letter_path"] == "/tmp/letter.txt"
    assert result["cover_letter"] == "Lettre adaptee"


def test_download_letter_serves_pdf_media_type(tmp_path):
    pdf_path = tmp_path / "letter.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    response = download_letter(str(pdf_path))

    assert response.media_type == "application/pdf"
    assert response.filename == "lettre_motivation.pdf"
