from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import sqlite3, time, os
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="Portfolio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "portfolio.db"
SECRET_KEY = "niru-super-secret-key-2026"
ADMIN_USER = "niru"
ADMIN_PASS = "bleach2025"
ALGORITHM = "HS256"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id        TEXT PRIMARY KEY,
            name      TEXT NOT NULL,
            desc      TEXT NOT NULL,
            icon      TEXT DEFAULT '🚀',
            status    TEXT DEFAULT 'live',
            url       TEXT DEFAULT '',
            github    TEXT DEFAULT '',
            tech      TEXT DEFAULT '',
            created   TEXT DEFAULT (datetime('now')),
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS visitors (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT DEFAULT (datetime('now')),
            page      TEXT,
            referrer  TEXT,
            ua        TEXT,
            ip        TEXT
        );
        INSERT OR IGNORE INTO projects VALUES
          ('neuroseg','NeuroSeg','Brain tumor segmentation using MONAI Swin-UNETR. 3D MRI scans processed with a transformer-based architecture, served via FastAPI REST API.','🧠','live','','https://github.com/niru001-dot','Python,MONAI,FastAPI,Swin-UNETR',datetime('now'),1),
          ('solofitness','SoloFitness','Solo Leveling-inspired fitness gamification. XP system, rank progression, raid bosses, powered by the Anthropic Claude API.','⚔️','live','','https://github.com/niru001-dot','React,Anthropic API,JavaScript',datetime('now'),2),
          ('studentlife','Student Life','Academic monitoring platform — track grades, attendance, deadlines, and performance trends in one clean dashboard.','📚','live','','https://github.com/niru001-dot','React,FastAPI,SQLite,Python',datetime('now'),3),
          ('nqueens','N-Queens Solver','Backtracking solution to the N-Queens problem in C. Visualizes all valid board configurations and benchmarks across board sizes.','♟️','live','','https://github.com/niru001-dot','C,Algorithms,Backtracking',datetime('now'),4);
    """)
    conn.commit()
    conn.close()

init_db()

security = HTTPBearer()

def make_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.utcnow() + timedelta(hours=12), "iat": datetime.utcnow()}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != ADMIN_USER:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

class LoginRequest(BaseModel):
    username: str
    password: str

class Project(BaseModel):
    id: Optional[str] = None
    name: str
    desc: str
    icon: Optional[str] = "🚀"
    status: Optional[str] = "live"
    url: Optional[str] = ""
    github: Optional[str] = ""
    tech: Optional[str] = ""
    sort_order: Optional[int] = 0

class VisitEvent(BaseModel):
    page: str
    referrer: Optional[str] = ""

@app.post("/api/auth/login")
def login(req: LoginRequest):
    if req.username == ADMIN_USER and req.password == ADMIN_PASS:
        return {"token": make_token(req.username), "message": "authenticated"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/auth/verify")
def verify(payload=Depends(verify_token)):
    return {"valid": True, "user": payload["sub"]}

@app.get("/api/projects")
def get_projects():
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects ORDER BY sort_order, created").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/visit")
async def record_visit(event: VisitEvent, request: Request):
    ip = request.headers.get("x-forwarded-for", "unknown")
    if not ip and request.client:
        ip = request.client.host
    ua = request.headers.get("user-agent", "")
    conn = get_db()
    conn.execute("INSERT INTO visitors (page,referrer,ua,ip) VALUES (?,?,?,?)",
                 (event.page, event.referrer or "", ua[:300], (ip or "")[:100]))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/stats/public")
def public_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    conn.close()
    return {"total_visits": total, "projects": projects}

@app.get("/api/admin/analytics")
def admin_analytics(payload=Depends(verify_token)):
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    today = conn.execute("SELECT COUNT(*) FROM visitors WHERE date(ts)=date('now')").fetchone()[0]
    week = conn.execute("SELECT COUNT(*) FROM visitors WHERE ts >= datetime('now','-7 days')").fetchone()[0]
    proj_clicks = conn.execute("SELECT COUNT(*) FROM visitors WHERE page LIKE 'project:%'").fetchone()[0]
    top_pages = conn.execute("SELECT page, COUNT(*) as cnt FROM visitors GROUP BY page ORDER BY cnt DESC LIMIT 10").fetchall()
    recent = conn.execute("SELECT * FROM visitors ORDER BY id DESC LIMIT 100").fetchall()
    daily = conn.execute("""SELECT date(ts) as day, COUNT(*) as cnt FROM visitors
        WHERE ts >= datetime('now','-14 days') GROUP BY day ORDER BY day""").fetchall()
    conn.close()
    return {
        "total": total, "today": today, "this_week": week,
        "project_clicks": proj_clicks,
        "top_pages": [dict(r) for r in top_pages],
        "recent": [dict(r) for r in recent],
        "daily": [dict(r) for r in daily],
    }

@app.post("/api/admin/projects")
def create_project(p: Project, payload=Depends(verify_token)):
    pid = p.id or f"proj_{int(time.time()*1000)}"
    conn = get_db()
    conn.execute("INSERT INTO projects (id,name,desc,icon,status,url,github,tech,sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
                 (pid, p.name, p.desc, p.icon, p.status, p.url, p.github, p.tech, p.sort_order))
    conn.commit()
    conn.close()
    return {"id": pid, "message": "created"}

@app.put("/api/admin/projects/{pid}")
def update_project(pid: str, p: Project, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE projects SET name=?,desc=?,icon=?,status=?,url=?,github=?,tech=?,sort_order=? WHERE id=?",
                 (p.name, p.desc, p.icon, p.status, p.url, p.github, p.tech, p.sort_order, pid))
    conn.commit()
    conn.close()
    return {"message": "updated"}

@app.delete("/api/admin/projects/{pid}")
def delete_project(pid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"message": "deleted"}

@app.delete("/api/admin/visitors")
def clear_visitors(payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("DELETE FROM visitors")
    conn.commit()
    conn.close()
    return {"message": "cleared"}

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
