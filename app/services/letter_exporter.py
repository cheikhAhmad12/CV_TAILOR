from pathlib import Path
from uuid import uuid4


def export_cover_letter_to_txt(cover_letter: str) -> str:
    output_dir = Path("/tmp/cv_tailor_exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"cover_letter_{uuid4().hex}.txt"
    path.write_text((cover_letter or "").strip() + "\n", encoding="utf-8")
    return str(path)
