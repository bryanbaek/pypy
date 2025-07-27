"""
FastAPI routes for MCP server integration.
Demonstrates how to use the MCP server tools via REST API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.backend.mcp.business_server import DiaryMCPServer

router = APIRouter(prefix="/mcp", tags=["MCP"])

# Initialize the MCP server
mcp_server = DiaryMCPServer()


# Pydantic models for request/response
class DiaryEntryCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []


class DiaryEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteCreate(BaseModel):
    title: str
    content: str


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


class ListRequest(BaseModel):
    limit: Optional[int] = 10
    tag: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@router.post("/diary/entries")
async def create_diary_entry(entry: DiaryEntryCreate):
    """Create a new diary entry."""
    try:
        result = await mcp_server._create_diary_entry(
            {"title": entry.title, "content": entry.content, "tags": entry.tags}
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diary/entries")
async def list_diary_entries(
    limit: int = 10,
    tag: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """List diary entries with optional filtering."""
    try:
        args = {"limit": limit}
        if tag:
            args["tag"] = tag
        if date_from:
            args["date_from"] = date_from
        if date_to:
            args["date_to"] = date_to

        result = await mcp_server._list_diary_entries(args)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diary/entries/{entry_id}")
async def read_diary_entry(entry_id: str):
    """Read a specific diary entry."""
    try:
        result = await mcp_server._read_diary_entry({"entry_id": entry_id})
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/diary/entries/{entry_id}")
async def update_diary_entry(entry_id: str, entry: DiaryEntryUpdate):
    """Update an existing diary entry."""
    try:
        args = {"entry_id": entry_id}
        if entry.title is not None:
            args["title"] = entry.title
        if entry.content is not None:
            args["content"] = entry.content
        if entry.tags is not None:
            args["tags"] = entry.tags

        result = await mcp_server._update_diary_entry(args)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/diary/entries/{entry_id}")
async def delete_diary_entry(entry_id: str):
    """Delete a diary entry."""
    try:
        result = await mcp_server._delete_diary_entry({"entry_id": entry_id})
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diary/entries/search")
async def search_diary_entries(search: SearchRequest):
    """Search diary entries."""
    try:
        result = await mcp_server._search_diary_entries(
            {"query": search.query, "limit": search.limit}
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes")
async def create_note(note: NoteCreate):
    """Create a new note."""
    try:
        result = await mcp_server._create_note(
            {"title": note.title, "content": note.content}
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes")
async def list_notes(limit: int = 10):
    """List notes."""
    try:
        result = await mcp_server._list_notes({"limit": limit})
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{note_id}")
async def read_note(note_id: str):
    """Read a specific note."""
    try:
        result = await mcp_server._read_note({"note_id": note_id})
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get diary statistics."""
    try:
        result = await mcp_server._get_stats()
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """List available MCP tools."""
    try:
        # This would normally be done by the MCP server's list_tools handler
        # For demo purposes, we'll return a simple list
        tools = [
            {
                "name": "create_diary_entry",
                "description": "Create a new diary entry with title and content",
                "endpoint": "POST /mcp/diary/entries",
            },
            {
                "name": "list_diary_entries",
                "description": "List all diary entries with optional filtering",
                "endpoint": "GET /mcp/diary/entries",
            },
            {
                "name": "read_diary_entry",
                "description": "Read a specific diary entry by ID",
                "endpoint": "GET /mcp/diary/entries/{entry_id}",
            },
            {
                "name": "update_diary_entry",
                "description": "Update an existing diary entry",
                "endpoint": "PUT /mcp/diary/entries/{entry_id}",
            },
            {
                "name": "delete_diary_entry",
                "description": "Delete a diary entry by ID",
                "endpoint": "DELETE /mcp/diary/entries/{entry_id}",
            },
            {
                "name": "search_diary_entries",
                "description": "Search diary entries by content or title",
                "endpoint": "POST /mcp/diary/entries/search",
            },
            {
                "name": "create_note",
                "description": "Create a quick note",
                "endpoint": "POST /mcp/notes",
            },
            {
                "name": "list_notes",
                "description": "List all notes",
                "endpoint": "GET /mcp/notes",
            },
            {
                "name": "read_note",
                "description": "Read a specific note by ID",
                "endpoint": "GET /mcp/notes/{note_id}",
            },
            {
                "name": "get_stats",
                "description": "Get diary statistics",
                "endpoint": "GET /mcp/stats",
            },
        ]
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
