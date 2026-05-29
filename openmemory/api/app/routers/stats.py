from app.database import get_db
from app.models import App, User
from app.utils.memory import get_memory_client
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])

@router.get("/")
async def get_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user profile stats (simplified for stateless proxy)."""
    
    # Find user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's apps
    apps = db.query(App).filter(App.owner_id == user.id).all()
    
    # Get memory stats from upstream API
    total_memories = 0
    try:
        memory_client = get_memory_client()
        if memory_client:
            response = memory_client.get_all(filters={"user_id": user_id})
            total_memories = len(response.get("results", []))
    except Exception:
        # Continue with 0 if upstream fails
        pass
    
    return {
        "user_id": user_id,
        "total_memories": total_memories,
        "total_apps": len(apps),
        "active_apps": len([app for app in apps if app.is_active]),
        "apps": [
            {
                "id": str(app.id),
                "name": app.name,
                "is_active": app.is_active,
                "memory_count": 0  # Memory counts per app not available in stateless proxy
            }
            for app in apps
        ]
    }