"""
MCP Server for OpenMemory backed by mem0 OSS API.

Provides memory operations (add, search, list, delete) via MCP protocol,
proxying to the upstream mem0 server for storage and retrieval.
"""

import contextvars
import datetime
import json
import logging
import uuid

import anyio

from app.database import SessionLocal
from app.models import App, User
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.responses import Response

load_dotenv()

mcp = FastMCP("mem0-mcp-server")

logger = logging.getLogger(__name__)


def get_memory_client_safe():
    """Get memory client with error handling."""
    try:
        return get_memory_client()
    except Exception as e:
        logger.warning(f"Failed to get memory client: {e}")
        return None


# Context variables for user_id and client_name
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")

mcp_router = APIRouter(prefix="/mcp")
sse = SseServerTransport("/mcp/messages/")


@mcp.tool(description="Add a new memory. This method is called everytime the user informs anything about themselves, their preferences, or anything that has any relevant information which can be useful in the future conversation. This can also be called when the user asks you to remember something. Set infer to False to store the memory verbatim without LLM fact extraction.")
async def add_memories(text: str, infer: bool = True) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)

    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        # Proxy to upstream mem0 API (no local storage)
        response = memory_client.add(
            text,
            user_id=uid,
            metadata={"source_app": "openmemory", "mcp_client": client_name},
            infer=infer,
        )

        return json.dumps(response)
    except Exception as e:
        logger.exception(f"Error adding to memory: {e}")
        return f"Error adding to memory: {e}"


@mcp.tool(description="Search through stored memories. This method is called EVERYTIME the user asks anything.")
async def search_memory(query: str, entity_boost: bool = False) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        # Proxy to upstream mem0 API with optional entity boost
        search_params = {
            "query": query,
            "filters": {"user_id": uid}
        }
        
        # Add entity boost if requested
        if entity_boost:
            search_params["entity_boost"] = True
            
        response = memory_client.search(**search_params)
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.exception(e)
        return f"Error searching memory: {e}"


@mcp.tool(description="List all memories in the user's memory")
async def list_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        # Proxy to upstream mem0 API (no local ACL filtering)
        response = memory_client.get_all(filters={"user_id": uid})
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.exception(f"Error getting memories: {e}")
        return f"Error getting memories: {e}"


@mcp.tool(description="Delete specific memories by their IDs")
async def delete_memories(memory_ids: list[str]) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        # Proxy delete operations to upstream
        deleted_count = 0
        errors = []
        
        for memory_id in memory_ids:
            try:
                memory_client.delete(memory_id)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete memory {memory_id}: {e}")
                errors.append(f"Memory {memory_id}: {str(e)}")

        if errors:
            return f"Deleted {deleted_count}/{len(memory_ids)} memories. Errors: {'; '.join(errors)}"
        
        return f"Successfully deleted {deleted_count} memories"
    except Exception as e:
        logger.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"


@mcp.tool(description="Delete all memories in the user's memory")
async def delete_all_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        # Proxy to upstream mem0 API (delete all for user)
        response = memory_client.delete_all(user_id=uid)
        return f"Successfully deleted all memories for user {uid}"
    except Exception as e:
        logger.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"




# --- MCP Transport Endpoints ---

@mcp_router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    uid = request.path_params.get("user_id")
    user_token = user_id_var.set(uid or "")
    client_name = request.path_params.get("client_name")
    client_token = client_name_var.set(client_name or "")

    try:
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
            await mcp._mcp_server.run(read_stream, write_stream, mcp._mcp_server.create_initialization_options())
    finally:
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)


@mcp_router.post("/messages/")
async def handle_messages_post(request: Request):
    try:
        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            return {}

        await sse.handle_post_message(request.scope, receive, send)
        return {"status": "ok"}
    except Exception:
        pass


@mcp_router.post("/{client_name}/sse/{user_id}/messages/")
async def handle_sse_messages_post(request: Request):
    return await handle_messages_post(request)


@mcp_router.api_route("/{client_name}/http/{user_id}", methods=["POST", "GET", "DELETE"])
async def handle_streamable_http(request: Request):
    uid = request.path_params.get("user_id")
    user_token = user_id_var.set(uid or "")
    client_name = request.path_params.get("client_name")
    client_token = client_name_var.set(client_name or "")

    response_started = False
    response_status = 200
    response_headers: list[tuple[bytes, bytes]] = []
    response_body = bytearray()

    async def capture_send(message):
        nonlocal response_started, response_status
        if message["type"] == "http.response.start":
            response_started = True
            response_status = message["status"]
            response_headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    try:
        transport = StreamableHTTPServerTransport(mcp_session_id=None, is_json_response_enabled=True)

        async with anyio.create_task_group() as tg:
            async def run_server(*, task_status=anyio.TASK_STATUS_IGNORED):
                async with transport.connect() as (read_stream, write_stream):
                    task_status.started()
                    await mcp._mcp_server.run(read_stream, write_stream, mcp._mcp_server.create_initialization_options(), stateless=True)

            await tg.start(run_server)
            await transport.handle_request(request.scope, request.receive, capture_send)
            await transport.terminate()
            tg.cancel_scope.cancel()
    finally:
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)

    if not response_started:
        return Response(status_code=500, content=b"Transport did not produce a response")

    return Response(
        content=bytes(response_body),
        status_code=response_status,
        headers={k.decode(): v.decode() for k, v in response_headers},
    )


def setup_mcp_server(app: FastAPI):
    mcp._mcp_server.name = "mem0-mcp-server"
    app.include_router(mcp_router)
