import logging
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import User
from app.utils.memory import get_memory_client
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


class Entity(BaseModel):
    id: str
    type: str
    total_memories: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EntityMemory(BaseModel):
    id: str
    memory: str
    created_at: str
    metadata: Optional[dict] = None


@router.get("/", response_model=List[Entity])
async def list_entities(
    user_id: str = Query(..., description="User ID to list entities for"),
    db: Session = Depends(get_db)
):
    """List all entities for a user from upstream mem0 API."""
    # Verify user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    try:
        # Call upstream entities endpoint directly
        import httpx
        import os
        
        api_key = os.getenv("MEM0_API_KEY")
        base_url = os.getenv("MEM0_API_URL", "http://localhost:8888")
        
        headers = {"X-API-Key": api_key} if api_key else {}
        
        with httpx.Client() as client:
            response = client.get(f"{base_url}/entities", headers=headers)
            response.raise_for_status()
            entities_data = response.json()
        
        # Filter entities for this user
        user_entities = [
            entity for entity in entities_data 
            if entity.get("id") == user_id and entity.get("type") == "user"
        ]
        
        return user_entities
        
    except Exception as e:
        logging.error(f"Error listing entities: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")


@router.get("/{entity_name}/memories", response_model=List[EntityMemory])
async def get_entity_memories(
    entity_name: str,
    user_id: str = Query(..., description="User ID to search within"),
    db: Session = Depends(get_db)
):
    """Get all memories containing a specific entity."""
    # Verify user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    try:
        # Use search with entity name to find related memories
        response = memory_client.search(
            query=entity_name,
            filters={"user_id": user_id},
            top_k=100  # Get more results for entity search
        )
        
        memories = response.get("results", [])
        
        # Filter memories that actually contain the entity
        # This is a simple text-based filter - could be enhanced with entity extraction
        entity_memories = []
        for memory in memories:
            memory_text = memory.get("memory", "").lower()
            if entity_name.lower() in memory_text:
                entity_memories.append(EntityMemory(
                    id=memory.get("id"),
                    memory=memory.get("memory", ""),
                    created_at=memory.get("created_at", ""),
                    metadata=memory.get("metadata", {})
                ))
        
        return entity_memories
        
    except Exception as e:
        logging.error(f"Error getting entity memories for {entity_name}: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")


@router.delete("/{entity_type}/{entity_id}")
async def delete_entity(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Delete all memories for an entity (proxy to upstream)."""
    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    try:
        # Call upstream entity deletion endpoint directly
        import httpx
        import os
        
        api_key = os.getenv("MEM0_API_KEY")
        base_url = os.getenv("MEM0_API_URL", "http://localhost:8888")
        
        headers = {"X-API-Key": api_key} if api_key else {}
        
        with httpx.Client() as client:
            response = client.delete(f"{base_url}/entities/{entity_type}/{entity_id}", headers=headers)
            response.raise_for_status()
        
        return {"message": "Entity deleted successfully"}
        
    except Exception as e:
        logging.error(f"Error deleting entity {entity_type}/{entity_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")