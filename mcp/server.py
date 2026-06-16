"""MCP SSE Server exposing Telegram tools for external agents/services."""

import asyncio
import json
import logging
import os
from typing import TypedDict
import uuid

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

BACKEND_URL = os.getenv("SENTINEL_API_URL", os.getenv("BACKEND_URL", "http://backend:8000"))

app = FastAPI(title="TG API Client MCP Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class McpSession(TypedDict):
    queue: asyncio.Queue
    api_key: str


sessions: dict[str, McpSession] = {}

# ═══════════════════════════════════════════════════════════
#  MCP TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════

MCP_TOOLS = [
    {
        "name": "list_telegram_accounts",
        "description": "List connected Telegram accounts for the authenticated user. Returns account details including telegram_user_id which is used as the identifier in all other tools.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_chats",
        "description": "List chats for a specific Telegram account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tg_user_id": {
                    "type": "integer",
                    "description": "Telegram user ID (from list_telegram_accounts, field telegram_user_id)",
                },
            },
            "required": ["tg_user_id"],
        },
    },
    {
        "name": "get_recent_messages",
        "description": "Get recent messages from a chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tg_user_id": {
                    "type": "integer",
                    "description": "Telegram user ID (from list_telegram_accounts)",
                },
                "tg_chat_id": {
                    "type": "integer",
                    "description": "Telegram chat ID (from list_chats, field telegram_chat_id)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of messages to return (default: 20)",
                    "default": 20,
                },
                "since": {
                    "type": "string",
                    "description": "Optional ISO 8601 datetime string (e.g. 2026-06-01T12:00:00Z). Only fetch messages newer than this.",
                },
            },
            "required": ["tg_user_id", "tg_chat_id"],
        },
    },
    {
        "name": "send_telegram_message",
        "description": "Send a message through a Telegram account.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tg_user_id": {
                    "type": "integer",
                    "description": "Telegram user ID (from list_telegram_accounts)",
                },
                "tg_chat_id": {
                    "type": "integer",
                    "description": "Telegram chat ID (from list_chats)",
                },
                "text": {
                    "type": "string",
                    "description": "Message text to send",
                },
            },
            "required": ["tg_user_id", "tg_chat_id", "text"],
        },
    },
    {
        "name": "search_messages",
        "description": "Search cached messages by keyword.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text",
                },
                "tg_user_id": {
                    "type": "integer",
                    "description": "Optional: limit to specific account by Telegram user ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default: 50)",
                    "default": 50,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "subscribe_to_channel",
        "description": "Subscribe/join a new Telegram channel or group by username or link.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tg_user_id": {
                    "type": "integer",
                    "description": "Telegram user ID (from list_telegram_accounts)",
                },
                "channel_url": {
                    "type": "string",
                    "description": "Channel username (e.g. '@durov') or invitation link (e.g. 't.me/durov')",
                },
            },
            "required": ["tg_user_id", "channel_url"],
        },
    },
]


# ═══════════════════════════════════════════════════════════
#  BACKEND API CALLS
# ═══════════════════════════════════════════════════════════


async def call_backend(method: str, path: str, api_key: str, body: dict | None = None) -> dict | list:
    """Call the backend API with the user's API key."""
    headers = {"X-API-Key": api_key}
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as client:
        if method == "GET":
            resp = await client.get(path, headers=headers)
        elif method == "POST":
            resp = await client.post(path, headers=headers, json=body or {})
        else:
            raise ValueError(f"Unsupported method: {method}")
        resp.raise_for_status()
        return resp.json()


async def handle_tool_call(name: str, arguments: dict, api_key: str) -> str:
    """Execute an MCP tool and return the result as text."""
    try:
        if name == "list_telegram_accounts":
            result = await call_backend("GET", "/telegram/accounts", api_key)
            return json.dumps(result, indent=2, default=str)

        if name == "list_chats":
            tg_user_id = arguments["tg_user_id"]
            result = await call_backend("GET", f"/telegram/accounts/{tg_user_id}/chats", api_key)
            return json.dumps(result, indent=2, default=str)

        if name == "get_recent_messages":
            tg_user_id = arguments["tg_user_id"]
            tg_chat_id = arguments["tg_chat_id"]
            limit = arguments.get("limit", 20)
            since = arguments.get("since")
            path = f"/telegram/accounts/{tg_user_id}/chats/{tg_chat_id}/messages?limit={limit}"
            if since:
                import urllib.parse
                path += f"&since={urllib.parse.quote(since)}"
            result = await call_backend("GET", path, api_key)
            return json.dumps(result, indent=2, default=str)

        if name == "send_telegram_message":
            tg_user_id = arguments["tg_user_id"]
            tg_chat_id = arguments["tg_chat_id"]
            result = await call_backend(
                "POST",
                f"/telegram/accounts/{tg_user_id}/chats/{tg_chat_id}/send",
                api_key,
                body={"text": arguments["text"]},
            )
            return json.dumps(result, indent=2, default=str)

        if name == "subscribe_to_channel":
            tg_user_id = arguments["tg_user_id"]
            channel_url = arguments["channel_url"]
            result = await call_backend(
                "POST",
                f"/telegram/accounts/{tg_user_id}/channels/join",
                api_key,
                body={"channel_url": channel_url},
            )
            return json.dumps(result, indent=2, default=str)

        if name == "search_messages":
            # Search across all cached messages
            query = arguments["query"]
            tg_user_id = arguments.get("tg_user_id")
            limit = arguments.get("limit", 50)

            # If tg_user_id is given, search within that account's chats
            if tg_user_id:
                chats = await call_backend("GET", f"/telegram/accounts/{tg_user_id}/chats", api_key)
                all_messages = []
                for chat in chats[:20]:  # Limit to first 20 chats for performance
                    messages = await call_backend(
                        "GET",
                        f"/telegram/accounts/{tg_user_id}/chats/{chat['telegram_chat_id']}/messages?limit=100",
                        api_key,
                    )
                    for msg in messages:
                        if msg.get("message_text") and query.lower() in msg["message_text"].lower():
                            all_messages.append({
                                "chat_title": chat.get("title"),
                                "sender": msg.get("sender_name"),
                                "text": msg["message_text"],
                                "date": msg.get("message_date"),
                            })
                return json.dumps(all_messages[:limit], indent=2, default=str)
            else:
                # Search across all accounts
                accounts = await call_backend("GET", "/telegram/accounts", api_key)
                all_messages = []
                for acc in accounts:
                    acc_tg_id = acc.get("telegram_user_id")
                    if not acc_tg_id:
                        continue
                    chats = await call_backend("GET", f"/telegram/accounts/{acc_tg_id}/chats", api_key)
                    for chat in chats[:10]:
                        messages = await call_backend(
                            "GET",
                            f"/telegram/accounts/{acc_tg_id}/chats/{chat['telegram_chat_id']}/messages?limit=50",
                            api_key,
                        )
                        for msg in messages:
                            if msg.get("message_text") and query.lower() in msg["message_text"].lower():
                                all_messages.append({
                                    "account": acc.get("display_name") or acc.get("phone"),
                                    "chat_title": chat.get("title"),
                                    "sender": msg.get("sender_name"),
                                    "text": msg["message_text"],
                                    "date": msg.get("message_date"),
                                })
                return json.dumps(all_messages[:limit], indent=2, default=str)

        return json.dumps({"error": f"Unknown tool: {name}"})

    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"API error {exc.response.status_code}: {exc.response.text}"})
    except Exception as exc:
        logger.exception("Tool call failed: %s", name)
        return json.dumps({"error": str(exc)})


# ═══════════════════════════════════════════════════════════
#  SSE ENDPOINTS
# ═══════════════════════════════════════════════════════════


@app.get("/mcp/health")
def health():
    return {"status": "ok", "service": "mcp-server"}


@app.get("/mcp/sse")
async def sse_endpoint(request: Request, api_key: str = Query(default="")):
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    session_api_key = request.headers.get("X-API-Key") or api_key
    sessions[session_id] = {"queue": queue, "api_key": session_api_key}
    logger.info("New MCP SSE session: %s", session_id)

    async def event_generator():
        try:
            post_url = f"/mcp/messages?session_id={session_id}"
            yield f"event: endpoint\ndata: {post_url}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"event: message\ndata: {json.dumps(message)}\n\n"
                    queue.task_done()
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            sessions.pop(session_id, None)
            logger.info("SSE session closed: %s", session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/mcp/messages")
async def handle_message(
    request: Request,
    session_id: str = Query(...),
    api_key: str = Query(default=""),
):
    session = sessions.get(session_id)
    if session is None:
        return {"error": "Invalid or expired session_id"}, 400

    body = await request.json()
    req_id = body.get("id")
    method = body.get("method")
    queue = session["queue"]
    session_api_key = session["api_key"] or request.headers.get("X-API-Key") or api_key

    logger.info("MCP request [%s]: %s", session_id[:8], method)

    if method == "initialize":
        resp = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "tg-api-client-mcp", "version": "1.0.0"},
            },
        }
        await queue.put(resp)

    elif method == "notifications/initialized":
        pass  # No response needed

    elif method == "tools/list":
        resp = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }
        await queue.put(resp)

    elif method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})

        result_text = await handle_tool_call(name, arguments, session_api_key)

        resp = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result_text}],
            },
        }
        await queue.put(resp)

    else:
        if req_id is not None:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
            await queue.put(resp)

    return {"status": "accepted"}
