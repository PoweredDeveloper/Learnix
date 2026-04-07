from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import authenticate_user, get_db, get_ollama
from app.api.ollama_http import raise_for_ollama_http
from app.models.entities import CheatSheet, PrepSource, Subject, User
from app.schemas.dto import CheatSheetOut
from app.services.ollama import OllamaClient

router = APIRouter(prefix="/cheat-sheets", tags=["cheat-sheets"])

CHEAT_SYSTEM = """You write exam cheat sheets. Return JSON only: {"content_md": string} — Markdown, compact, formulas in plain text."""


@router.post("/generate")
async def generate_cheat_sheet(
    subject_id: UUID,
    prep_source_id: UUID | None = None,
    density: str = "normal",
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> CheatSheetOut:
    subj = await db.get(Subject, subject_id)
    if not subj or subj.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    source_text = ""
    if prep_source_id:
        ps = await db.get(PrepSource, prep_source_id)
        if not ps or ps.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prep not found")
        if ps.subject_id != subj.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prep source does not belong to this subject")
        source_text = ps.extracted_text[:20_000]

    user_prompt = f"Subject: {subj.name}. Density: {density}.\n\nSource excerpt:\n{source_text or 'No source; infer general outline.'}"
    try:
        data = await ollama.chat_json(CHEAT_SYSTEM, user_prompt)
    except httpx.HTTPError as e:
        raise_for_ollama_http(e)
    md = str(data.get("content_md", "# " + subj.name))

    cs = CheatSheet(
        user_id=user.id,
        subject_id=subj.id,
        prep_source_id=prep_source_id,
        content_md=md,
        density=density,
    )
    db.add(cs)
    await db.commit()
    await db.refresh(cs)
    return CheatSheetOut.model_validate(cs)


@router.get("/latest/{subject_id}")
async def latest_sheet(
    subject_id: UUID,
    user: User = Depends(authenticate_user),
    db: AsyncSession = Depends(get_db),
) -> CheatSheetOut | dict:
    subj = await db.get(Subject, subject_id)
    if not subj or subj.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    r = await db.execute(
        select(CheatSheet)
        .where(CheatSheet.subject_id == subj.id, CheatSheet.user_id == user.id)
        .order_by(CheatSheet.created_at.desc())
        .limit(1)
    )
    cs = r.scalar_one_or_none()
    if not cs:
        return {"found": False}
    return CheatSheetOut.model_validate(cs)
