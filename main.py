from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Literal
from datetime import datetime
import asyncio
import random

from database import db, create_document, get_documents
from schemas import User, Employee, Log

app = FastAPI(title="ScaleShield API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthPayload(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    email: EmailStr
    role: Literal["admin", "analyst"]


@app.get("/test")
async def test():
    # Verify database connectivity
    await create_document("health", {"ok": True, "ts": datetime.utcnow().isoformat()})
    docs = await get_documents("health", {}, 1)
    return {"status": "ok", "db": bool(docs)}


@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: AuthPayload):
    # Placeholder auth that accepts any non-empty credentials, creates user in DB for demo
    role: Literal["admin", "analyst"] = "admin" if "admin" in payload.email.lower() else "analyst"
    user = User(email=payload.email, role=role, created_at=datetime.utcnow())
    await create_document("user", user.dict())
    return AuthResponse(email=user.email, role=user.role)


@app.get("/employees", response_model=List[Employee])
async def list_employees():
    # Seed a few employees if empty
    docs = await get_documents("employee", {}, 100)
    if not docs:
        seed = [
            Employee(name=f"Employee {i+1}", role=["Engineer","Analyst","Manager"][i%3], location=["NYC","SF","Remote"][i%3], threatScore=random.randint(0,100), created_at=datetime.utcnow()).dict()
            for i in range(9)
        ]
        for d in seed:
            await create_document("employee", d)
        docs = await get_documents("employee", {}, 100)
    # Convert ObjectId to str if present
    for d in docs:
        d.pop("_id", None)
    return [Employee(**d) for d in docs]


@app.get("/logs", response_model=List[Log])
async def get_logs():
    docs = await get_documents("log", {}, 150)
    for d in docs:
        d.pop("_id", None)
    return [Log(**d) for d in docs]


# Real-time WebSocket that streams threat events
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict):
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(ws)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Generate a random event and push to client and DB
            events = ["Login attempt", "USB mounted", "Suspicious process", "Network spike", "File exfiltration"]
            severity = random.choice(["low", "medium", "high"])
            employee = f"Employee {random.randint(1,9)}"
            log = Log(time=datetime.utcnow(), event=random.choice(events), employee=employee, severity=severity)
            await create_document("log", log.dict())
            await manager.broadcast({
                "type": "log",
                "payload": log.dict()
            })
            await asyncio.sleep(1.8)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
