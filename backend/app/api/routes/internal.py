from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_api_key
from app.services.notification_dispatch import claim_due_notifications

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/notifications/due", dependencies=[Depends(verify_api_key)])
async def notifications_due(db: AsyncSession = Depends(get_db)) -> dict:
    items = await claim_due_notifications(db)
    await db.commit()
    return {"items": items}
