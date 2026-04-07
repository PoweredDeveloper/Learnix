import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db
from app.core.config import get_settings
from app.models.entities import PrepSource, Subject, User
from app.services.ingestion import extract_text_from_pdf

router = APIRouter(prefix="/prep", tags=["prep"])


@router.post("/upload")
async def upload_prep(
    subject_id: uuid.UUID | None = None,
    file: UploadFile = File(...),
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    if subject_id:
        s = await db.get(Subject, subject_id)
        if not s or s.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "doc").suffix.lower() or ".bin"
    name = f"{uuid.uuid4()}{ext}"
    dest = upload_dir / name
    content = await file.read()
    dest.write_bytes(content)

    text = ""
    if ext == ".pdf":
        try:
            text = extract_text_from_pdf(dest)
        except Exception:
            text = ""
    elif ext in (".md", ".txt"):
        text = content.decode("utf-8", errors="replace")

    ps = PrepSource(
        user_id=user.id,
        subject_id=subject_id,
        file_path=str(dest),
        extracted_text=text[:500_000],
    )
    db.add(ps)
    await db.commit()
    await db.refresh(ps)
    return {"id": str(ps.id), "extracted_chars": len(text)}
