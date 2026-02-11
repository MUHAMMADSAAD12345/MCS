"""Document management endpoints — upload, list, delete."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from auth.middleware import get_current_user
from config import settings
from models.schemas import DocumentInfo, DocumentUploadResponse
from services.session_store import (
    add_document_record,
    delete_document_record,
    get_user_documents,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# These will be set by main.py
_ingestion_pipeline = None
_vector_store = None


def set_dependencies(ingestion_pipeline, vector_store):
    global _ingestion_pipeline, _vector_store
    _ingestion_pipeline = ingestion_pipeline
    _vector_store = vector_store


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".md"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload and ingest a document into the RAG pipeline."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read and save file
    settings.ensure_dirs()
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    doc_id = str(uuid.uuid4())
    filepath = settings.UPLOAD_DIR / f"{doc_id}{ext}"
    filepath.write_bytes(content)

    # Ingest into RAG
    if _ingestion_pipeline is None:
        raise HTTPException(
            status_code=503, detail="RAG pipeline not available"
        )

    try:
        _, chunk_count = await _ingestion_pipeline.ingest(
            filepath=filepath,
            user_id=user["id"],
            doc_id=doc_id,
        )
    except Exception as e:
        # Clean up file on ingestion failure
        filepath.unlink(missing_ok=True)
        logger.error("Ingestion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {e}")

    # Record in database
    await add_document_record(
        doc_id=doc_id,
        user_id=user["id"],
        filename=file.filename,
        file_type=ext.lstrip("."),
        chunk_count=chunk_count,
    )

    doc_info = DocumentInfo(
        id=doc_id,
        filename=file.filename,
        file_type=ext.lstrip("."),
        chunk_count=chunk_count,
        uploaded_at=datetime.utcnow(),
    )
    return DocumentUploadResponse(document=doc_info)


@router.get("/list")
async def list_documents(user: dict = Depends(get_current_user)):
    """List all documents uploaded by the current user."""
    docs = await get_user_documents(user["id"])
    return {"documents": docs}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a document from RAG and database."""
    # Delete from vector store
    if _vector_store:
        try:
            _vector_store.delete_by_document(doc_id, user["id"])
        except Exception as e:
            logger.warning("Failed to delete vectors: %s", e)

    # Delete from database
    deleted = await delete_document_record(doc_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file
    for ext in ALLOWED_EXTENSIONS:
        filepath = settings.UPLOAD_DIR / f"{doc_id}{ext}"
        filepath.unlink(missing_ok=True)

    return {"message": "Document deleted", "doc_id": doc_id}
