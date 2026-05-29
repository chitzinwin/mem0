from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator


class Entity(BaseModel):
    text: str
    type: str  # 'PERSON', 'ORG', 'PROPER', 'COMPOUND'
    linked_memories: Optional[List[str]] = []


class MemoryBase(BaseModel):
    content: str
    metadata_: Optional[dict] = Field(default_factory=dict)
    entities: Optional[List[Entity]] = []

class MemoryCreate(MemoryBase):
    user_id: UUID
    app_id: UUID


class Category(BaseModel):
    name: str


class App(BaseModel):
    id: UUID
    name: str


class Memory(MemoryBase):
    id: UUID
    user_id: UUID
    app_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    state: str
    categories: Optional[List[Category]] = None
    app: App

    model_config = ConfigDict(from_attributes=True)

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata_: Optional[dict] = None
    state: Optional[str] = None


class MemoryResponse(BaseModel):
    id: UUID
    content: str
    created_at: int
    state: str
    app_id: Optional[UUID] = None
    app_name: Optional[str] = None
    categories: List[str]
    metadata_: Optional[dict] = None
    entities: Optional[List[Entity]] = []

    @validator('created_at', pre=True)
    def convert_to_epoch(cls, v):
        if isinstance(v, datetime):
            return int(v.timestamp())
        elif isinstance(v, str):
            # Parse ISO timestamp string from upstream API
            try:
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except:
                return v
        return v

class PaginatedMemoryResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
    page: int
    size: int
    pages: int
