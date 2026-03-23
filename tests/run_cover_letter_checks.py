from types import SimpleNamespace

import app.models.job  # noqa: F401
import app.models.profile  # noqa: F401
import app.models.user  # noqa: F401
from app.models.application import ApplicationVersion
from app.routers.exports import download_letter
from app.services.llm_cover_letter import (
    _normalize_latex_output,
    _force_salutation,
    _extract_body_paragraphs,
    cover_letter_salutation,
)
from app.services.latex_exporter import render_cover_letter_template
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


def _patch_common():
    tailoring_engine.parse_cv = lambda _: {
        "summary": "cv",
        "skills": ["Python"],
        "experiences": [],
        "education": [],
        "projects": [],
    }
    tailoring_engine.parse_job_description = lambda _: {
        "title": "ML Engineer",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "responsibilities": [],
        "keywords": ["Python", "LLM"],
    }
    tailoring_engine.rank_projects = lambda projects, parsed_job: [
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
    ]
    tailoring_engine.generate_tailored_summary = lambda *args, **kwargs: "summary"
    tailoring_engine.generate_experience_bullets = lambda *args, **kwargs: ["bullet"]
    tailoring_engine.generate_resume_markdown = lambda *args, **kwargs: "# CV"
    tailoring_engine.compute_compatibility_score = lambda *args, **kwargs: 91.5
    tailoring_engine.compute_ats_score = lambda *args, **kwargs: 88.0
    tailoring_engine.export_resume_to_docx = lambda *_: "/tmp/resume.docx"
    tailoring_engine.export_latex_to_pdf_with_tectonic = lambda **_: "/tmp/resume.pdf"
    tailoring_engine.generate_cover_letter_with_llm = lambda *args, **kwargs: "Lettre adaptee"
    tailoring_engine.generate_cover_letter = lambda *args, **kwargs: "Lettre fallback"


def test_pdf_path_when_latex_template_exists():
    _patch_common()
    tailoring_engine.export_cover_letter_template_to_pdf = lambda **kwargs: "/tmp/letter.pdf"
    tailoring_engine.export_cover_letter_to_txt = (
        lambda *_: (_ for _ in ()).throw(AssertionError("txt fallback should not be used"))
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


def test_txt_fallback_when_latex_generation_fails():
    _patch_common()

    def fail_template(**kwargs):
        raise RuntimeError("template pdf failed")

    def fail_latex(**kwargs):
        raise RuntimeError("latex failed")

    tailoring_engine.export_cover_letter_template_to_pdf = fail_template
    tailoring_engine.generate_cover_letter_latex_with_llm = fail_latex
    tailoring_engine.export_cover_letter_to_txt = lambda *_: "/tmp/letter.txt"

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


def test_download_letter_pdf_media_type():
    path = "/tmp/test_letter.pdf"
    with open(path, "wb") as file_obj:
        file_obj.write(b"%PDF-1.4")

    response = download_letter(path)

    assert response.media_type == "application/pdf"
    assert response.filename == "lettre_motivation.pdf"


def test_normalize_latex_output_unescapes_commands():
    raw = "\\\\documentclass{article}\\n\\\\begin{document}\\nBonjour\\\\end{document}"
    normalized = _normalize_latex_output(raw)

    assert normalized.startswith("\\documentclass{article}")
    assert "\\begin{document}" in normalized
    assert "\\end{document}" in normalized


def test_render_cover_letter_template_replaces_body():
    template = (
        "\\documentclass{letter}\n"
        "\\begin{document}\n"
        "\\begin{letter}{Entreprise}\n"
        "\\opening{Madame, Monsieur,}\n"
        "Ancien contenu.\n\n"
        "\\closing{Cordialement,}\n"
        "\\end{letter}\n"
        "\\end{document}\n"
    )
    rendered = render_cover_letter_template(
        template,
        "Madame, Monsieur,\n\nNouveau paragraphe adapte.\n\nCordialement,",
    )

    assert "Ancien contenu." not in rendered
    assert "Nouveau paragraphe adapte." in rendered
    assert "\\opening{Madame, Monsieur,}" in rendered
    assert "\\closing{Cordialement,}" in rendered


def test_force_salutation_removes_template_names():
    text = "Madame Douwes, Monsieur Emiya,\n\nContenu adapte.\n\nCordialement,"
    normalized = _force_salutation(text, output_language="fr")

    assert normalized.startswith("Madame, Monsieur,")
    assert "Douwes" not in normalized
    assert "Emiya" not in normalized


def test_contact_salutation_overrides_default():
    parsed_job = {"contact_salutation": "Monsieur Martin,"}
    normalized = _force_salutation(
        "Madame Douwes,\n\nContenu adapte.",
        output_language="fr",
        parsed_job=parsed_job,
    )

    assert cover_letter_salutation(parsed_job, "fr") == "Monsieur Martin,"
    assert normalized.startswith("Monsieur Martin,")


def test_force_salutation_preserves_target_body_paragraph_count():
    text = (
        "Madame Douwes,\n\n"
        "Premier paragraphe. Deux phrases ici.\n\n"
        "Deuxieme paragraphe.\n\n"
        "Troisieme paragraphe.\n\n"
        "Cordialement,"
    )
    normalized = _force_salutation(
        text,
        output_language="fr",
        target_body_paragraph_count=2,
    )

    assert normalized.startswith("Madame, Monsieur,")
    assert len(_extract_body_paragraphs(normalized)) == 2


def main():
    test_pdf_path_when_latex_template_exists()
    test_txt_fallback_when_latex_generation_fails()
    test_download_letter_pdf_media_type()
    test_normalize_latex_output_unescapes_commands()
    test_render_cover_letter_template_replaces_body()
    test_force_salutation_removes_template_names()
    test_contact_salutation_overrides_default()
    test_force_salutation_preserves_target_body_paragraph_count()
    print("8 checks passed")


if __name__ == "__main__":
    main()
