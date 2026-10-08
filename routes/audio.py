from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.audio import AudioTrack, Playlist, PlaylistTrack, SoundEffect


router = APIRouter(
    prefix="/audio",
    tags=["Audio"],
)


class CreateTrackRequest(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    artist: str = Field(default="", max_length=150)
    audio_url: str = Field(min_length=1, max_length=500)
    genre: str = Field(default="", max_length=100)
    duration: float = Field(default=0, ge=0)


class CreatePlaylistRequest(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=150)


class AddTrackRequest(BaseModel):
    playlist_id: int
    track_id: int


@router.get("/tracks")
async def get_tracks(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AudioTrack)
        .where(AudioTrack.is_active == True)
        .order_by(AudioTrack.id.desc())
    )

    tracks = result.scalars().all()

    return {
        "tracks": [
            {
                "id": track.id,
                "title": track.title,
                "artist": track.artist,
                "audio_url": track.audio_url,
                "genre": track.genre,
                "duration": track.duration,
                "is_active": track.is_active,
            }
            for track in tracks
        ]
    }


@router.get("/tracks/{track_id}")
async def get_track(
    track_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AudioTrack).where(
            AudioTrack.id == track_id
        )
    )

    track = result.scalar_one_or_none()

    if track is None:
        raise HTTPException(
            status_code=404,
            detail="Audio track not found",
        )

    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "audio_url": track.audio_url,
        "genre": track.genre,
        "duration": track.duration,
        "is_active": track.is_active,
    }


@router.post("/tracks")
async def create_track(
    data: CreateTrackRequest,
    db: AsyncSession = Depends(get_db),
):
    track = AudioTrack(
        title=data.title,
        artist=data.artist,
        audio_url=data.audio_url,
        genre=data.genre,
        duration=data.duration,
        is_active=True,
    )

    db.add(track)

    await db.commit()
    await db.refresh(track)

    return {
        "status": "track_created",
        "track": {
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "audio_url": track.audio_url,
            "genre": track.genre,
            "duration": track.duration,
        },
    }


@router.get("/playlists/{user_id}")
async def get_playlists(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Playlist)
        .where(Playlist.user_id == user_id)
        .order_by(Playlist.id.desc())
    )

    playlists = result.scalars().all()

    return {
        "user_id": user_id,
        "playlists": [
            {
                "id": playlist.id,
                "name": playlist.name,
            }
            for playlist in playlists
        ],
    }


@router.post("/playlists")
async def create_playlist(
    data: CreatePlaylistRequest,
    db: AsyncSession = Depends(get_db),
):
    playlist = Playlist(
        user_id=data.user_id,
        name=data.name,
    )

    db.add(playlist)

    await db.commit()
    await db.refresh(playlist)

    return {
        "status": "playlist_created",
        "playlist": {
            "id": playlist.id,
            "name": playlist.name,
            "user_id": playlist.user_id,
        },
    }


@router.post("/playlists/tracks")
async def add_track_to_playlist(
    data: AddTrackRequest,
    db: AsyncSession = Depends(get_db),
):
    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.id == data.playlist_id
        )
    )

    playlist = playlist_result.scalar_one_or_none()

    if playlist is None:
        raise HTTPException(
            status_code=404,
            detail="Playlist not found",
        )

    track_result = await db.execute(
        select(AudioTrack).where(
            AudioTrack.id == data.track_id
        )
    )

    track = track_result.scalar_one_or_none()

    if track is None:
        raise HTTPException(
            status_code=404,
            detail="Track not found",
        )

    existing_result = await db.execute(
        select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == data.playlist_id,
            PlaylistTrack.track_id == data.track_id,
        )
    )

    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Track already exists in playlist",
        )

    playlist_track = PlaylistTrack(
        playlist_id=data.playlist_id,
        track_id=data.track_id,
    )

    db.add(playlist_track)

    await db.commit()

    return {
        "status": "track_added_to_playlist",
        "playlist_id": data.playlist_id,
        "track_id": data.track_id,
    }


@router.get("/playlists/{playlist_id}/tracks")
async def get_playlist_tracks(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AudioTrack)
        .join(
            PlaylistTrack,
            PlaylistTrack.track_id == AudioTrack.id,
        )
        .where(
            PlaylistTrack.playlist_id == playlist_id
        )
        .order_by(PlaylistTrack.id.asc())
    )

    tracks = result.scalars().all()

    return {
        "playlist_id": playlist_id,
        "tracks": [
            {
                "id": track.id,
                "title": track.title,
                "artist": track.artist,
                "audio_url": track.audio_url,
                "genre": track.genre,
                "duration": track.duration,
            }
            for track in tracks
        ],
    }


@router.get("/effects")
async def get_sound_effects(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SoundEffect)
        .where(SoundEffect.is_active == True)
        .order_by(SoundEffect.id.asc())
    )

    effects = result.scalars().all()

    return {
        "effects": [
            {
                "id": effect.id,
                "name": effect.name,
                "effect_type": effect.effect_type,
                "audio_url": effect.audio_url,
                "volume": effect.volume,
                "is_active": effect.is_active,
            }
            for effect in effects
        ]
}
