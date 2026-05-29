from datetime import UTC, datetime
import io 
import json 
import gzip 
import zipfile
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import User, App, Config
from app.utils.memory import get_memory_client

router = APIRouter(prefix="/api/v1/backup", tags=["backup"])


class BackupResponse(BaseModel):
    message: str
    backup_size: Optional[int] = None
    records_count: Optional[int] = None


@router.get("/export")
async def export_backup(
    user_id: str = Query(..., description="User ID to export data for"),
    include_memories: bool = Query(True, description="Include memories from upstream API"),
    db: Session = Depends(get_db)
):
    """Export user data (simplified for stateless proxy)."""
    
    # Find user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's apps
    apps = db.query(App).filter(App.owner_id == user.id).all()
    
    # Get user's configs
    configs = db.query(Config).filter(Config.user_id == user.id).all()
    
    # Prepare backup data
    backup_data = {
        "export_timestamp": datetime.now(UTC).isoformat(),
        "user": {
            "user_id": user.user_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        },
        "apps": [
            {
                "id": str(app.id),
                "name": app.name,
                "is_active": app.is_active,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "updated_at": app.updated_at.isoformat() if app.updated_at else None
            }
            for app in apps
        ],
        "configs": [
            {
                "id": str(config.id),
                "key": config.key,
                "value": config.value,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            }
            for config in configs
        ],
        "memories": []  # Will be populated from upstream if requested
    }
    
    # Get memories from upstream API if requested
    if include_memories:
        try:
            memory_client = get_memory_client()
            if memory_client:
                response = memory_client.get_all(filters={"user_id": user_id})
                backup_data["memories"] = response.get("results", [])
        except Exception as e:
            # Continue without memories if upstream fails
            backup_data["memories_error"] = f"Failed to fetch memories: {str(e)}"
    
    # Create JSON backup
    backup_json = json.dumps(backup_data, indent=2)
    
    # Compress the backup
    buffer = io.BytesIO()
    with gzip.open(buffer, 'wt', encoding='utf-8') as f:
        f.write(backup_json)
    
    buffer.seek(0)
    
    # Generate filename
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"openmemory_backup_{user_id}_{timestamp}.json.gz"
    
    return StreamingResponse(
        io.BytesIO(buffer.read()),
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import")
async def import_backup(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Import user data (simplified for stateless proxy)."""
    
    if not file.filename.endswith(('.json', '.json.gz')):
        raise HTTPException(status_code=400, detail="Invalid file format. Expected .json or .json.gz")
    
    try:
        # Read file content
        content = await file.read()
        
        # Decompress if gzipped
        if file.filename.endswith('.gz'):
            content = gzip.decompress(content).decode('utf-8')
        else:
            content = content.decode('utf-8')
        
        # Parse JSON
        backup_data = json.loads(content)
        
        # Find or create user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        imported_count = 0
        
        # Import apps
        if "apps" in backup_data:
            for app_data in backup_data["apps"]:
                existing_app = db.query(App).filter(
                    App.name == app_data["name"],
                    App.owner_id == user.id
                ).first()
                
                if not existing_app:
                    app = App(
                        name=app_data["name"],
                        owner_id=user.id,
                        is_active=app_data.get("is_active", True)
                    )
                    db.add(app)
                    imported_count += 1
        
        # Import configs
        if "configs" in backup_data:
            for config_data in backup_data["configs"]:
                existing_config = db.query(Config).filter(
                    Config.key == config_data["key"],
                    Config.user_id == user.id
                ).first()
                
                if not existing_config:
                    config = Config(
                        key=config_data["key"],
                        value=config_data["value"],
                        user_id=user.id
                    )
                    db.add(config)
                    imported_count += 1
        
        db.commit()
        
        # Note: Memories are not imported to local DB in stateless proxy mode
        # They would need to be imported directly to upstream mem0 API
        
        return BackupResponse(
            message=f"Successfully imported {imported_count} records. Note: Memories not imported in stateless proxy mode.",
            records_count=imported_count
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# Note: Memory import/export now handled by upstream mem0 API
# Local backup only covers UI configuration (users, apps, configs)