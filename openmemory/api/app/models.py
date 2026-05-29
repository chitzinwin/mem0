import datetime
import uuid

import sqlalchemy as sa
from app.database import Base
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import relationship


def get_current_utc_time():
    return datetime.datetime.now(datetime.UTC)


class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    metadata_ = Column('metadata', JSON, default=dict)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    apps = relationship("App", back_populates="owner")


class App(Base):
    __tablename__ = "apps"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    owner_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    metadata_ = Column('metadata', JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)

    owner = relationship("User", back_populates="apps")

    __table_args__ = (
        sa.UniqueConstraint('owner_id', 'name', name='idx_app_owner_name'),
    )


class Config(Base):
    __tablename__ = "configs"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_current_utc_time)
    updated_at = Column(DateTime, default=get_current_utc_time, onupdate=get_current_utc_time)
