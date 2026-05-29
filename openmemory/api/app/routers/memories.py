import logging
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import (
    App,
    User,
)
from app.schemas import MemoryResponse
from app.utils.memory import get_memory_client
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page, Params
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


from pydantic import BaseModel


class MemoryFilterRequest(BaseModel):
    user_id: str
    page: int = 1
    size: int = 10
    search_query: Optional[str] = None
    app_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    sort_column: Optional[str] = None
    sort_direction: Optional[str] = None
    show_archived: Optional[bool] = False


@router.post("/filter", response_model=Page[MemoryResponse])
async def filter_memories(
    request: MemoryFilterRequest,
    db: Session = Depends(get_db)
):
    """Filter memories (compatibility endpoint for frontend)."""
    # This is essentially the same as the GET endpoint but accepts POST with body
    return await list_memories(
        user_id=request.user_id,
        app_id=None,  # App filtering handled differently in stateless proxy
        from_date=None,
        to_date=None,
        categories=None,
        params=Params(page=request.page, size=request.size),
        search_query=request.search_query,
        entity_boost=False,
        entity_filter=None,
        sort_column=request.sort_column,
        sort_direction=request.sort_direction,
        db=db
    )


@router.get("/", response_model=Page[MemoryResponse])
async def list_memories(
    user_id: str,
    app_id: Optional[UUID] = None,
    from_date: Optional[int] = Query(
        None,
        description="Filter memories created after this date (timestamp)",
        examples=[1718505600]
    ),
    to_date: Optional[int] = Query(
        None,
        description="Filter memories created before this date (timestamp)",
        examples=[1718505600]
    ),
    categories: Optional[str] = None,
    params: Params = Depends(),
    search_query: Optional[str] = None,
    entity_boost: Optional[bool] = Query(False, description="Enable entity-based search boosting"),
    entity_filter: Optional[str] = Query(None, description="Filter by specific entity"),
    sort_column: Optional[str] = Query(None, description="Column to sort by (memory, categories, app_name, created_at)"),
    sort_direction: Optional[str] = Query(None, description="Sort direction (asc or desc)"),
    db: Session = Depends(get_db)
):
    # Verify user exists (for app filtering)
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    try:
        # Proxy to upstream mem0 API
        if search_query:
            # Use search endpoint for queries
            search_filters = {"user_id": user_id}
            
            # Add entity boost if requested
            search_params = {
                "query": search_query,
                "filters": search_filters,
                "top_k": params.size * params.page  # Get enough results for pagination
            }
            
            # If entity boost is enabled, add it to the search
            if entity_boost:
                search_params["entity_boost"] = True
                
            response = memory_client.search(**search_params)
            memories = response.get("results", [])
        else:
            # Use get_all for listing
            response = memory_client.get_all(filters={"user_id": user_id})
            memories = response.get("results", [])

        # Apply entity filtering if specified
        if entity_filter:
            filtered_memories = []
            for memory in memories:
                memory_text = memory.get("memory", "").lower()
                if entity_filter.lower() in memory_text:
                    filtered_memories.append(memory)
            memories = filtered_memories

        # Apply app filtering if specified
        if app_id:
            app_obj = db.query(App).filter(App.id == app_id, App.owner_id == user.id).first()
            if app_obj:
                # Filter by app metadata (stored in upstream)
                memories = [
                    m for m in memories 
                    if m.get("metadata", {}).get("mcp_client") == app_obj.name
                ]

        # Apply date filtering
        if from_date or to_date:
            filtered_memories = []
            for memory in memories:
                created_at = memory.get("created_at")
                if created_at:
                    # Parse ISO timestamp
                    from datetime import datetime
                    memory_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    memory_timestamp = memory_date.timestamp()
                    
                    if from_date and memory_timestamp < from_date:
                        continue
                    if to_date and memory_timestamp > to_date:
                        continue
                    
                filtered_memories.append(memory)
            memories = filtered_memories

        # Manual pagination (since upstream doesn't support it)
        start_idx = (params.page - 1) * params.size
        end_idx = start_idx + params.size
        paginated_memories = memories[start_idx:end_idx]

        # Transform to expected format
        memory_responses = []
        for memory in paginated_memories:
            memory_responses.append(MemoryResponse(
                id=memory.get("id"),
                content=memory.get("memory", ""),
                created_at=memory.get("created_at"),
                state="active",  # Upstream memories are always active
                app_id=None,  # Will be resolved from metadata
                app_name=memory.get("metadata", {}).get("mcp_client"),
                categories=[],  # Categories not supported in proxy mode
                metadata_=memory.get("metadata", {})
            ))

        # Return paginated response
        return Page(
            items=memory_responses,
            total=len(memories),
            page=params.page,
            size=params.size,
            pages=(len(memories) + params.size - 1) // params.size
        )

    except Exception as e:
        logging.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")


# Categories endpoint - not supported in proxy mode
@router.get("/categories")
async def get_categories(
    user_id: str,
    db: Session = Depends(get_db)
):
    # Categories not supported in stateless proxy mode
    # Use upstream metadata for organization instead
    return {
        "categories": [],
        "total": 0
    }


class CreateMemoryRequest(BaseModel):
    user_id: str
    text: str
    app: str
    metadata: Optional[dict] = None
    infer: bool = True


@router.post("/")
async def create_memory(
    request: CreateMemoryRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Get or create app
    app_obj = db.query(App).filter(App.name == request.app,
                                   App.owner_id == user.id).first()
    if not app_obj:
        app_obj = App(name=request.app, owner_id=user.id)
        db.add(app_obj)
        db.commit()
        db.refresh(app_obj)

    # Check if app is active
    if not app_obj.is_active:
        raise HTTPException(status_code=403, detail=f"App {request.app} is currently paused on OpenMemory. Cannot create new memories.")

    # Log what we're about to do
    logging.info(f"Creating memory for user_id: {request.user_id} with app: {request.app}")
    
    # Try to get memory client safely
    try:
        memory_client = get_memory_client()
        if not memory_client:
            raise Exception("Memory client is not available")
    except Exception as client_error:
        logging.warning(f"Memory client unavailable: {client_error}. Creating memory in database only.")
        # Return a json response with the error
        return {
            "error": str(client_error)
        }

    # Proxy to upstream mem0 API (no local storage)
    try:
        upstream_response = memory_client.add(
            request.text,
            user_id=request.user_id,
            metadata={
                "source_app": "openmemory",
                "mcp_client": request.app,
            },
            infer=request.infer
        )
        
        logging.info(f"Upstream response: {upstream_response}")
        return upstream_response
        
    except Exception as upstream_error:
        logging.error(f"Upstream operation failed: {upstream_error}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(upstream_error)}")


@router.get("/{memory_id}")
async def get_memory(
    memory_id: UUID,
    db: Session = Depends(get_db)
):
    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    try:
        # Proxy to upstream mem0 API
        memory = memory_client.get(str(memory_id))
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "id": memory.get("id"),
            "text": memory.get("memory", ""),
            "created_at": memory.get("created_at"),
            "state": "active",  # Upstream memories are always active
            "app_id": None,  # Will be resolved from metadata
            "app_name": memory.get("metadata", {}).get("mcp_client"),
            "categories": [],  # Categories not supported in proxy mode
            "metadata_": memory.get("metadata", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting memory {memory_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")


class DeleteMemoriesRequest(BaseModel):
    user_id: str
    memory_ids: List[UUID]


@router.delete("/")
async def delete_memories(
    request: DeleteMemoriesRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    # Proxy delete operations to upstream
    deleted_count = 0
    errors = []
    
    for memory_id in request.memory_ids:
        try:
            memory_client.delete(str(memory_id))
            deleted_count += 1
        except Exception as delete_error:
            logging.error(f"Failed to delete memory {memory_id}: {delete_error}")
            errors.append(f"Memory {memory_id}: {str(delete_error)}")

    if errors:
        return {
            "message": f"Deleted {deleted_count}/{len(request.memory_ids)} memories",
            "errors": errors
        }
    
    return {"message": f"Successfully deleted {deleted_count} memories"}


@router.get("/{memory_id}/related", response_model=Page[MemoryResponse])
async def get_related_memories(
    memory_id: UUID,
    user_id: str,
    params: Params = Depends(),
    db: Session = Depends(get_db)
):
    """Get related memories using entity linking (replaces category-based similarity)."""
    # Verify user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get memory client
    memory_client = get_memory_client()
    if not memory_client:
        raise HTTPException(status_code=502, detail="Memory system unavailable")

    try:
        # Get the source memory first
        source_memory_response = memory_client.get_all(filters={"user_id": user_id})
        all_memories = source_memory_response.get("results", [])
        
        # Find the source memory
        source_memory = None
        for memory in all_memories:
            if memory.get("id") == str(memory_id):
                source_memory = memory
                break
        
        if not source_memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Extract keywords from source memory for similarity matching
        source_text = source_memory.get("memory", "").lower()
        source_words = set(word.strip(".,!?;:") for word in source_text.split() if len(word) > 3)
        
        # Find related memories using keyword similarity and semantic relationships
        related_memories = []
        
        for memory in all_memories:
            if memory.get("id") == str(memory_id):
                continue  # Skip the source memory itself
                
            memory_text = memory.get("memory", "").lower()
            memory_words = set(word.strip(".,!?;:") for word in memory_text.split() if len(word) > 3)
            
            # Calculate similarity score
            similarity_score = 0
            
            # 1. Direct word overlap (high weight)
            overlap = len(source_words.intersection(memory_words))
            similarity_score += overlap * 3
            
            # 2. Semantic relationships (simple keyword matching)
            # Programming-related terms
            prog_terms = {"python", "programming", "coding", "editor", "vim", "emacs", "language"}
            if source_words.intersection(prog_terms) and memory_words.intersection(prog_terms):
                similarity_score += 2
            
            # Location-related terms  
            location_terms = {"live", "city", "location", "place", "home", "from"}
            if source_words.intersection(location_terms) and memory_words.intersection(location_terms):
                similarity_score += 2
                
            # Preference-related terms
            pref_terms = {"prefer", "favorite", "like", "love", "enjoy", "hate", "dislike"}
            if source_words.intersection(pref_terms) and memory_words.intersection(pref_terms):
                similarity_score += 2
            
            # Add memory if it has any similarity
            if similarity_score > 0:
                memory["similarity_score"] = similarity_score
                related_memories.append(memory)
        
        # Sort by similarity score (highest first)
        related_memories.sort(key=lambda m: m.get("similarity_score", 0), reverse=True)
        
        # Apply pagination
        start_idx = (params.page - 1) * params.size
        end_idx = start_idx + params.size
        paginated_memories = related_memories[start_idx:end_idx]
        
        # Transform to expected format
        memory_responses = []
        for memory in paginated_memories:
            memory_responses.append(MemoryResponse(
                id=memory.get("id"),
                content=memory.get("memory", ""),
                created_at=memory.get("created_at"),
                state="active",
                app_id=None,
                app_name=memory.get("metadata", {}).get("mcp_client"),
                categories=[],
                metadata_=memory.get("metadata", {}),
                entities=[]
            ))

        return Page(
            items=memory_responses,
            total=len(related_memories),
            page=params.page,
            size=params.size,
            pages=(len(related_memories) + params.size - 1) // params.size
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting related memories for {memory_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")