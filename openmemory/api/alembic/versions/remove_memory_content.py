"""Remove memory content tables for stateless proxy

Revision ID: remove_memory_content
Revises: add_config_table
Create Date: 2026-05-25 05:15:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'remove_memory_content'
down_revision = 'add_config_table'
branch_labels = None
depends_on = None


def upgrade():
    """Remove memory content tables - OpenMemory is now a stateless proxy"""
    
    # Drop memory-related tables (in dependency order)
    op.drop_table('memory_access_logs')
    op.drop_table('memory_status_history') 
    op.drop_table('memory_categories')
    op.drop_table('archive_policies')
    op.drop_table('access_controls')
    op.drop_table('memories')
    op.drop_table('categories')


def downgrade():
    """Recreate memory content tables (for rollback only)"""
    
    # Recreate categories table
    op.create_table('categories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_created_at'), 'categories', ['created_at'], unique=False)
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=True)
    
    # Recreate memories table
    op.create_table('memories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('app_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('vector', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('state', sa.Enum('active', 'paused', 'archived', 'deleted', name='memorystate'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['app_id'], ['apps.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate other tables...
    # (Simplified for migration - full schema would be restored from backup if needed)