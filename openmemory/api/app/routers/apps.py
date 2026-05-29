from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models import App, User
from app.utils.memory import get_memory_client
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/apps", tags=["apps"])


@router.get("/")
async def get_apps(
    db: Session = Depends(get_db),
    user_id: Optional[str] = Query(None),
    page: int = Query(1),
    page_size: int = Query(10),
    name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_direction: Optional[str] = Query("asc"),
):
    """List apps. Derives memory counts from upstream."""
    query = db.query(App)

    if user_id:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            query = query.filter(App.owner_id == user.id)

    if name:
        query = query.filter(App.name.ilike(f"%{name}%"))
    if is_active is not None:
        query = query.filter(App.is_active == is_active)

    total = query.count()
    apps = query.offset((page - 1) * page_size).limit(page_size).all()

    # Get memory counts from upstream
    memory_client = get_memory_client()
    app_memory_counts = {}
    if memory_client and user_id:
        try:
            response = memory_client.get_all(filters={"user_id": user_id})
            items = response.get("results", []) if isinstance(response, dict) else []
            for mem in items:
                app_name = (mem.get("metadata") or {}).get("mcp_client", "unknown")
                app_memory_counts[app_name] = app_memory_counts.get(app_name, 0) + 1
        except Exception:
            pass

    return {
        "apps": [
            {
                "id": str(app.id),
                "name": app.name,
                "is_active": app.is_active,
                "total_memories_created": app_memory_counts.get(app.name, 0),
                "total_memories_accessed": 0,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            }
            for app in apps
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{app_id}")
async def get_app(app_id: UUID, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    return {
        "id": str(app.id),
        "name": app.name,
        "is_active": app.is_active,
        "total_memories_created": 0,
        "total_memories_accessed": 0,
        "first_accessed": None,
        "last_accessed": None,
    }


@router.get("/{app_id}/memories")
async def get_app_memories(
    app_id: UUID,
    page: int = Query(1),
    page_size: int = Query(10),
    db: Session = Depends(get_db),
):
    """Get memories created by this app from upstream."""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Find the user who owns this app
    user = db.query(User).filter(User.id == app.owner_id).first()
    if not user:
        return {"memories": [], "total": 0, "page": page, "page_size": page_size}

    memory_client = get_memory_client()
    if not memory_client:
        return {"memories": [], "total": 0, "page": page, "page_size": page_size}

    try:
        response = memory_client.get_all(filters={"user_id": user.user_id})
        items = response.get("results", []) if isinstance(response, dict) else []

        # Filter by app name in metadata
        app_memories = [
            m for m in items
            if (m.get("metadata") or {}).get("mcp_client") == app.name
        ]

        total = len(app_memories)
        start = (page - 1) * page_size
        paged = app_memories[start:start + page_size]

        return {
            "memories": [
                {
                    "id": m.get("id", ""),
                    "user_id": m.get("user_id", ""),
                    "content": m.get("memory", ""),
                    "state": "active",
                    "created_at": m.get("created_at"),
                    "updated_at": m.get("updated_at"),
                    "deleted_at": None,
                    "archived_at": None,
                    "app_id": str(app_id),
                    "app_name": app.name,
                    "vector": None,
                    "metadata_": m.get("metadata") or {},
                    "categories": [],
                }
                for m in paged
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception:
        return {"memories": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/{app_id}/accessed")
async def get_app_accessed_memories(
    app_id: UUID,
    page: int = Query(1),
    page_size: int = Query(10),
    db: Session = Depends(get_db),
):
    """No access tracking in stateless proxy mode."""
    return {"memories": [], "total": 0, "page": page, "page_size": page_size}


@router.put("/{app_id}")
async def update_app(
    app_id: UUID,
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    if is_active is not None:
        app.is_active = is_active

    db.commit()
    db.refresh(app)
    return {
        "id": str(app.id),
        "name": app.name,
        "is_active": app.is_active,
    }
