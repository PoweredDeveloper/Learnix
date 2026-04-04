import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.core.config import get_settings
from app.models.entities import PrepSource, Subject, User
from app.services.ingestion import extract_text_from_pdf

router = APIRouter(prefix="/prep", tags=["prep"])


async def _tid(x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id")) -> int:
    return x_telegram_user_id


async def _user(db: AsyncSession, telegram_id: int) -> User:
    r = await db.execute(select(User).where(User.telegram_id == telegram_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u


@router.post("/upload", dependencies=[Depends(verify_api_key)])
async def upload_prep(
    subject_id: UUID | None = None,
    file: UploadFile = File(...),
    telegram_user_id: int = Depends(_tid),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    user = await _user(db, telegram_user_id)
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
        text = extract_text_from_pdf(dest)
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
