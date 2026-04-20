import sys
import os
sys.path.append(os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import init_db, get_all_listings
from agent.agent import run_agent
from collections import Counter

@asynccontextmanager
async def lifespan(app):
    init_db()
    print("Backend API started!")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

@app.get("/stats")
async def get_stats():
    listings = get_all_listings()
    sources = Counter(l[1] for l in listings)
    return {
        "total": len(listings),
        "merrjep": sources.get("merrjep", 0),
        "njoftime": sources.get("njoftime", 0),
        "instagram": sources.get("instagram", 0),
    }

@app.post("/chat")
async def chat(msg: ChatMessage):
    result = await run_agent(msg.message)
    return result

@app.get("/listings")
async def get_listings(source: str = None, limit: int = 20):
    listings = get_all_listings()
    if source:
        listings = [l for l in listings if l[1] == source]
    return {"listings": listings[:limit]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
