import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/docx")
def download_docx(path: str):
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DOCX file not found",
        )

    return FileResponse(
        path=path,
        filename="tailored_resume.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/pdf")
def download_pdf(path: str):
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found",
        )

    return FileResponse(
        path=path,
        filename="tailored_resume.pdf",
        media_type="application/pdf",
    )


@router.get("/letter")
def download_letter(path: str):
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Letter file not found",
        )

    return FileResponse(
        path=path,
        filename="lettre_motivation.txt",
        media_type="text/plain; charset=utf-8",
    )


@router.get("/pdf-inline")
def view_pdf_inline(path: str):
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found",
        )

    return FileResponse(
        path=path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
