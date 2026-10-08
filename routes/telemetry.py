from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.telemetry import DeviceTelemetry


router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
)


class TelemetryRequest(BaseModel):
    user_id: int
    session_id: int | None = None

    device_type: str = Field(
        min_length=1,
        max_length=50,
    )

    platform: str = Field(
        min_length=1,
        max_length=50,
    )

    os_name: str | None = Field(
        default=None,
        max_length=100,
    )

    browser: str | None = Field(
        default=None,
        max_length=100,
    )

    gpu: str | None = Field(
        default=None,
        max_length=255,
    )

    webgl_version: str | None = Field(
        default=None,
        max_length=50,
    )

    screen_width: int | None = Field(
        default=None,
        ge=1,
    )

    screen_height: int | None = Field(
        default=None,
        ge=1,
    )

    pixel_ratio: float | None = Field(
        default=None,
        ge=0.1,
        le=10,
    )

    quality_mode: str = Field(
        default="AUTO",
        max_length=20,
    )

    fps: float | None = Field(
        default=None,
        ge=0,
        le=240,
    )

    battery_level: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    low_power_mode: bool = False


@router.post("/")
async def save_telemetry(
    data: TelemetryRequest,
    db: AsyncSession = Depends(get_db),
):
    telemetry = DeviceTelemetry(
        user_id=data.user_id,
        session_id=data.session_id,
        device_type=data.device_type,
        platform=data.platform,
        os_name=data.os_name,
        browser=data.browser,
        gpu=data.gpu,
        webgl_version=data.webgl_version,
        screen_width=data.screen_width,
        screen_height=data.screen_height,
        pixel_ratio=data.pixel_ratio,
        quality_mode=data.quality_mode,
        fps=data.fps,
        battery_level=data.battery_level,
        low_power_mode=data.low_power_mode,
        created_at=datetime.utcnow(),
    )

    db.add(telemetry)

    await db.commit()
    await db.refresh(telemetry)

    return {
        "status": "telemetry_saved",
        "telemetry_id": telemetry.id,
        "quality_mode": telemetry.quality_mode,
    }


@router.get("/player/{user_id}")
async def get_player_telemetry(
    user_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))

    result = await db.execute(
        select(DeviceTelemetry)
        .where(
            DeviceTelemetry.user_id == user_id
        )
        .order_by(
            DeviceTelemetry.created_at.desc()
        )
        .limit(limit)
    )

    telemetry_list = result.scalars().all()

    return {
        "user_id": user_id,
        "telemetry": [
            {
                "id": item.id,
                "session_id": item.session_id,
                "device_type": item.device_type,
                "platform": item.platform,
                "os_name": item.os_name,
                "browser": item.browser,
                "gpu": item.gpu,
                "webgl_version": item.webgl_version,
                "screen_width": item.screen_width,
                "screen_height": item.screen_height,
                "pixel_ratio": item.pixel_ratio,
                "quality_mode": item.quality_mode,
                "fps": item.fps,
                "battery_level": item.battery_level,
                "low_power_mode": item.low_power_mode,
                "created_at": item.created_at,
            }
            for item in telemetry_list
        ],
    }


@router.get("/latest/{user_id}")
async def get_latest_telemetry(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeviceTelemetry)
        .where(
            DeviceTelemetry.user_id == user_id
        )
        .order_by(
            DeviceTelemetry.created_at.desc()
        )
        .limit(1)
    )

    telemetry = result.scalar_one_or_none()

    if telemetry is None:
        raise HTTPException(
            status_code=404,
            detail="No telemetry found",
        )

    return {
        "user_id": user_id,
        "device_type": telemetry.device_type,
        "platform": telemetry.platform,
        "os_name": telemetry.os_name,
        "browser": telemetry.browser,
        "gpu": telemetry.gpu,
        "webgl_version": telemetry.webgl_version,
        "screen": {
            "width": telemetry.screen_width,
            "height": telemetry.screen_height,
            "pixel_ratio": telemetry.pixel_ratio,
        },
        "quality_mode": telemetry.quality_mode,
        "fps": telemetry.fps,
        "battery_level": telemetry.battery_level,
        "low_power_mode": telemetry.low_power_mode,
        "created_at": telemetry.created_at,
    }
