import subprocess
import re
from pathlib import Path
from uuid import uuid4


def _escape_latex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "%": r"\%",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def _append_tailored_block(
    source_latex: str,
    tailored_summary: str,
    tailored_experience_bullets: list[str],
    selected_projects: list[dict],
    output_language: str = "fr",
) -> str:
    lang = "en" if output_language == "en" else "fr"

    project_lines = []
    for project in selected_projects[:4]:
        name = _escape_latex(str(project.get("name", "Project")))
        desc = _escape_latex(
            str(
                project.get("description")
                or project.get("readme_summary")
                or project.get("reason")
                or ""
            )
        )
        project_lines.append(f"\\item \\textbf{{{name}}} --- {desc}".strip())

    projects = "\n".join(project_lines) or (
        r"\item No ranked projects provided."
        if lang == "en"
        else r"\item Aucun projet selectionne."
    )

    title_proj = "Selected Projects" if lang == "en" else "Projets Selectionnes"

    tailored_block = f"""
\\clearpage
\\section*{{{title_proj}}}
\\begin{{itemize}}
{projects}
\\end{{itemize}}
"""

    marker = r"\end{document}"
    if marker in source_latex:
        return source_latex.replace(marker, tailored_block + "\n" + marker)

    return source_latex + "\n" + tailored_block + "\n" + marker + "\n"


def _normalize_section_title(title: str) -> str:
    normalized = title.replace(r"\&", "&").strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _replace_section_body(
    source_latex: str,
    target_titles: tuple[str, ...],
    replacement_body: str,
) -> tuple[str, bool]:
    section_matches = list(re.finditer(r"\\section\{([^}]*)\}", source_latex))
    if not section_matches:
        return source_latex, False

    normalized_targets = {t.strip().lower() for t in target_titles}
    marker = r"\end{document}"

    for idx, match in enumerate(section_matches):
        title = _normalize_section_title(match.group(1))
        if title not in normalized_targets:
            continue

        body_start = match.end()
        if idx + 1 < len(section_matches):
            body_end = section_matches[idx + 1].start()
        else:
            body_end = source_latex.find(marker, body_start)
            if body_end == -1:
                body_end = len(source_latex)

        updated = source_latex[:body_start] + "\n" + replacement_body + "\n\n" + source_latex[body_end:]
        return updated, True

    return source_latex, False


def _build_summary_body(tailored_summary: str, macro_style: bool) -> str:
    summary = _escape_latex(tailored_summary) or "Resume cible indisponible."
    if macro_style:
        return (
            "  \\resumeSubHeadingListStart\n"
            f"    \\resumeItem{{{summary}}}\n"
            "  \\resumeSubHeadingListEnd"
        )

    return "\\begin{itemize}\n  \\item " + summary + "\n\\end{itemize}"


def _build_experience_body(
    tailored_experience_bullets: list[str],
    macro_style: bool,
    output_language: str = "fr",
) -> str:
    lang = "en" if output_language == "en" else "fr"
    bullets = tailored_experience_bullets[:6] or [
        "Tailored experience details unavailable."
        if lang == "en"
        else "Details d'experience cibles indisponibles."
    ]
    escaped_bullets = [_escape_latex(b) for b in bullets]

    if macro_style:
        items = "\n".join(f"        \\resumeItem{{{b}}}" for b in escaped_bullets)
        return (
            "  \\resumeSubHeadingListStart\n"
            "    \\item\n"
            f"      \\textbf{{{'Tailored Experience Highlights' if lang == 'en' else 'Experience ciblee'}}}\n"
            "      \\resumeItemListStart\n"
            f"{items}\n"
            "      \\resumeItemListEnd\n"
            "  \\resumeSubHeadingListEnd"
        )

    items = "\n".join(f"  \\item {b}" for b in escaped_bullets)
    return "\\begin{itemize}\n" + items + "\n\\end{itemize}"


def _build_projects_body(
    selected_projects: list[dict],
    macro_style: bool,
    output_language: str = "fr",
) -> str:
    lang = "en" if output_language == "en" else "fr"
    project_lines = []
    for project in selected_projects[:4]:
        name = _escape_latex(str(project.get("name", "Project")))
        desc = _escape_latex(
            str(
                project.get("description")
                or project.get("readme_summary")
                or project.get("reason")
                or ""
            )
        )
        if desc:
            project_lines.append(f"\\textbf{{{name}}} --- {desc}")
        else:
            project_lines.append(f"\\textbf{{{name}}}")

    if not project_lines:
        project_lines = ["No selected projects."] if lang == "en" else ["Aucun projet selectionne."]

    if macro_style:
        items = "\n".join(f"    \\resumeItem{{{line}}}" for line in project_lines)
        return (
            "  \\resumeSubHeadingListStart\n"
            f"{items}\n"
            "  \\resumeSubHeadingListEnd"
        )

    items = "\n".join(f"  \\item {line}" for line in project_lines)
    return "\\begin{itemize}\n" + items + "\n\\end{itemize}"


def _inject_tailored_content_in_sections(
    master_cv_latex: str,
    tailored_summary: str,
    tailored_experience_bullets: list[str],
    selected_projects: list[dict],
    output_language: str = "fr",
) -> str:
    source = master_cv_latex
    macro_style = "\\resumeSubHeadingListStart" in source and "\\resumeItem" in source

    projects_body = _build_projects_body(
        selected_projects,
        macro_style,
        output_language=output_language,
    )

    source, replaced = _replace_section_body(
        source,
        (
            "personal and academic projects",
            "selected projects",
            "projects",
            "personal projects",
            "projets selectionnes",
            "projets personnels et academiques",
        ),
        projects_body,
    )
    if replaced:
        return source

    return _append_tailored_block(
        source_latex=source,
        tailored_summary=tailored_summary,
        tailored_experience_bullets=tailored_experience_bullets,
        selected_projects=selected_projects,
        output_language=output_language,
    )


def _sanitize_latex_for_tectonic(source: str) -> str:
    filtered_lines = []
    for line in source.splitlines():
        stripped = line.strip()

        # Common pdfTeX-specific helpers that fail under Tectonic/XeTeX.
        if "glyphtounicode" in stripped.lower():
            continue
        if stripped.startswith("\\pdfgentounicode"):
            continue
        if stripped.startswith("\\pdfminorversion"):
            continue
        if stripped.startswith("\\pdfobjcompresslevel"):
            continue
        if stripped.startswith("\\pdfcompresslevel"):
            continue

        filtered_lines.append(line)

    return "\n".join(filtered_lines)


def _escape_unescaped_ampersands(source: str) -> str:
    lines = source.splitlines()
    result = []
    in_alignment_env = False
    alignment_envs = (
        "tabular",
        "tabular*",
        "tabularx",
        "array",
        "align",
        "align*",
        "matrix",
        "pmatrix",
        "bmatrix",
    )

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("\\begin{"):
            for env in alignment_envs:
                if stripped.startswith(f"\\begin{{{env}}}"):
                    in_alignment_env = True
                    break
        if stripped.startswith("\\end{"):
            for env in alignment_envs:
                if stripped.startswith(f"\\end{{{env}}}"):
                    in_alignment_env = False
                    break

        if in_alignment_env:
            result.append(line)
            continue

        # Escape '&' not already escaped (prevents "Misplaced alignment tab character &").
        line = re.sub(r"(?<!\\)&", r"\\&", line)
        result.append(line)

    return "\n".join(result)


def _compile_latex_source_to_pdf(latex_source: str, stem_prefix: str) -> str:
    output_dir = Path("/tmp/cv_tailor_exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{stem_prefix}_{uuid4().hex}"
    tex_path = output_dir / f"{stem}.tex"
    pdf_path = output_dir / f"{stem}.pdf"

    safe_source = _sanitize_latex_for_tectonic(latex_source)
    safe_source = _escape_unescaped_ampersands(safe_source)
    tex_path.write_text(safe_source, encoding="utf-8")

    try:
        subprocess.run(
            ["tectonic", "--outdir", str(output_dir), str(tex_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("tectonic is not installed in the backend container") from exc
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"LaTeX compilation failed: {details[:800]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("LaTeX compilation timed out") from exc
    finally:
        tex_path.unlink(missing_ok=True)

    if not pdf_path.exists():
        raise RuntimeError("PDF was not generated by tectonic")

    return str(pdf_path)


def compile_master_latex_to_pdf(master_cv_latex: str) -> str:
    if not master_cv_latex.strip():
        return ""
    return _compile_latex_source_to_pdf(master_cv_latex, "master_resume")


def export_latex_to_pdf_with_tectonic(
    master_cv_latex: str,
    tailored_summary: str,
    tailored_experience_bullets: list[str],
    selected_projects: list[dict],
    output_language: str = "fr",
) -> str:
    if not master_cv_latex.strip():
        return ""

    latex_source = _inject_tailored_content_in_sections(
        master_cv_latex=master_cv_latex,
        tailored_summary=tailored_summary,
        tailored_experience_bullets=tailored_experience_bullets,
        selected_projects=selected_projects,
        output_language=output_language,
    )
    return _compile_latex_source_to_pdf(latex_source, "tailored_resume")
