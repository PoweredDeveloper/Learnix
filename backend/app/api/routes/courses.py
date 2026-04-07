import uuid
from datetime import date, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Form, UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db, get_ollama
from app.api.ollama_http import raise_for_ollama_http
from app.core.config import get_settings
from app.models.entities import PrepSource, Subject, User
from app.schemas.dto import PersonalizedThemeIn
from app.services.ingestion import extract_text_from_pdf
from app.services.ollama import OllamaClient
from app.services.plan_build import build_study_plan

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("/personalized-theme")
async def personalized_theme(
    body: PersonalizedThemeIn,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    name = (body.course_name or body.theme).strip()[:255]
    subj = Subject(user_id=user.id, name=name)
    db.add(subj)
    await db.flush()
    start = date.today()
    end = start + timedelta(days=body.days)
    try:
        tasks = await build_study_plan(
            db=db,
            user=user,
            subject=subj,
            start_date=start,
            end_date=end,
            topic_names=[body.theme.strip()],
            ollama=ollama,
            prep_excerpt=None,
        )
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
    return {
        "subject_id": str(subj.id),
        "subject_name": subj.name,
        "task_count": len(tasks),
        "tasks": [t.model_dump(mode="json") for t in tasks],
    }


@router.post("/personalized-file")
async def personalized_file(
    file: UploadFile = File(...),
    days: int = Form(default=14),
    subject_name: str | None = Form(default=None),
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> dict:
    settings = get_settings()
    raw_name = (subject_name or file.filename or "My course").strip()
    subj_name = raw_name[:255]
    subj = Subject(user_id=user.id, name=subj_name)
    db.add(subj)
    await db.flush()

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "doc").suffix.lower() or ".bin"
    fname = f"{uuid.uuid4()}{ext}"
    dest = upload_dir / fname
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
        subject_id=subj.id,
        file_path=str(dest),
        extracted_text=text[:500_000],
    )
    db.add(ps)
    await db.flush()

    d = max(3, min(int(days), 365))
    start = date.today()
    end = start + timedelta(days=d)
    excerpt = text[:15_000] if text else None
    try:
        tasks = await build_study_plan(
            db=db,
            user=user,
            subject=subj,
            start_date=start,
            end_date=end,
            topic_names=[subj_name],
            ollama=ollama,
            prep_excerpt=excerpt,
        )
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)

    return {
        "subject_id": str(subj.id),
        "subject_name": subj.name,
        "prep_id": str(ps.id),
        "extracted_chars": len(text),
        "task_count": len(tasks),
        "tasks": [t.model_dump(mode="json") for t in tasks],
    }
