"""Download endpoint for generated documents."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import settings

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


@router.get("/{file_id}/{filename}")
async def download_file(file_id: str, filename: str):
    """Serve a generated document for download."""
    # Check all possible extensions
    for ext in [".pdf", ".docx", ".xlsx"]:
        filepath = settings.GENERATED_DIR / f"{file_id}{ext}"
        if filepath.exists():
            media_types = {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            return FileResponse(
                path=str(filepath),
                filename=filename,
                media_type=media_types.get(ext, "application/octet-stream"),
            )

    raise HTTPException(status_code=404, detail="File not found")
