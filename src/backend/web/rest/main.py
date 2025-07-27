from fastapi import FastAPI
from src.backend.web.rest.routes import chat

app = FastAPI()

app.include_router(chat.router)

# Try to include MCP routes if available
try:
    from src.backend.web.rest.routes import mcp
    app.include_router(mcp.router)
except ImportError:
    print("MCP routes not available, skipping...")


@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI AI API integration"}
