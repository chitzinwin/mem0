"""
Memory client utilities for OpenMemory.

Provides a singleton OSSMemoryClient that proxies to the upstream
mem0 self-hosted server via HTTP.
"""

import logging

from app.utils.mem0_client import OSSMemoryClient

logger = logging.getLogger(__name__)

_memory_client = None


def reset_memory_client():
    """Reset the global memory client to force reinitialization."""
    global _memory_client
    _memory_client = None


def get_memory_client(custom_instructions: str = None):
    """
    Get or initialize the mem0 API client.

    Returns:
        OSSMemoryClient instance or None if initialization fails.
    """
    global _memory_client

    if _memory_client is not None:
        return _memory_client

    try:
        _memory_client = OSSMemoryClient()
        logger.info("Memory client initialized successfully")
        return _memory_client
    except Exception as e:
        logger.warning(f"Failed to initialize memory client: {e}")
        return None
