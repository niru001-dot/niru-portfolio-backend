from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import sqlite3, time, os
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="Portfolio API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "portfolio.db"
SECRET_KEY = "niru-portfolio-secret-2025"
ADMIN_USER = "niru"
ADMIN_PASS = "bleach2025"
ALGORITHM = "HS256"

# ─── DB ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            desc TEXT NOT NULL,
            icon TEXT DEFAULT '🚀',
            status TEXT DEFAULT 'live',
            url TEXT DEFAULT '',
            github TEXT DEFAULT '',
            tech TEXT DEFAULT '',
            created TEXT DEFAULT (datetime('now')),
            sort_order INTEGER DEFAULT 0,
            visible INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            tier INTEGER DEFAULT 1,
            visible INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS certificates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            org TEXT NOT NULL,
            date TEXT DEFAULT '',
            icon TEXT DEFAULT '🏆',
            url TEXT DEFAULT '',
            visible INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT (datetime('now')),
            page TEXT,
            referrer TEXT,
            ua TEXT,
            ip TEXT
        );

        INSERT OR IGNORE INTO projects VALUES
          ('neuroseg','NeuroSeg','Brain tumor segmentation using MONAI Swin-UNETR. 3D MRI scans processed with a transformer-based architecture, served via FastAPI REST API.','🧠','live','','https://github.com/niru001-dot','Python,MONAI,FastAPI,Swin-UNETR',datetime('now'),1,1),
          ('solofitness','SoloFitness','Solo Leveling-inspired fitness gamification. XP system, rank progression, raid bosses, powered by the Anthropic Claude API.','⚔️','live','','https://github.com/niru001-dot','React,Anthropic API,JavaScript',datetime('now'),2,1),
          ('studentlife','Student Life','Academic monitoring platform — track grades, attendance, deadlines, and performance trends in one clean dashboard.','📚','live','','https://github.com/niru001-dot','React,FastAPI,SQLite,Python',datetime('now'),3,1),
          ('nqueens','N-Queens Solver','Backtracking solution to the N-Queens problem in C. Visualizes all valid board configurations and benchmarks across board sizes.','♟️','live','','https://github.com/niru001-dot','C,Algorithms,Backtracking',datetime('now'),4,1);

        INSERT OR IGNORE INTO skills VALUES
          ('python','Python',1,1,1),
          ('react','React',1,1,2),
          ('fastapi','FastAPI',1,1,3),
          ('monai','MONAI',2,1,4),
          ('kotlin','Kotlin',2,1,5),
          ('c','C / C++',2,1,6),
          ('sqlite','SQLite',2,1,7),
          ('cloudflare','Cloudflare',3,1,8),
          ('docker','Docker',3,1,9),
          ('git','Git',3,1,10),
          ('linux','Linux',3,1,11),
          ('aws','AWS CLF',3,1,12);

        INSERT OR IGNORE INTO certificates VALUES
          ('python-cert','Basics of Python','Infosys Springboard','Dec 2024','🐍','',1,1),
          ('gcp-cert','Innovating with Google Cloud AI','Google Cloud','Jun 2026','☁️','',1,2);

        INSERT OR IGNORE INTO settings VALUES
          ('name','Niranjana H'),
          ('tagline','I build things that think.'),
          ('about','CS undergrad at CIT (VTU Karnataka). I work at the intersection of AI/ML, full-stack engineering, and medical imaging.'),
          ('about2','My work spans transformer-based medical image segmentation (NeuroSeg), full-stack gamification (SoloFitness with Claude API), Android academic platforms, and classic algorithm implementations.'),
          ('about3','Outside code: event coordinator for Vyanthra & SkyHack 2.0, Bleach fan, hardware tinkerer, Valorant enthusiast.'),
          ('status','Available for internships'),
          ('status_type','green'),
          ('email','niranjanha33@gmail.com'),
          ('github','https://github.com/niru001-dot'),
          ('portfolio_url','https://niranjana.dpdns.org'),
          ('show_about',1),
          ('show_projects',1),
          ('show_skills',1),
          ('show_certificates',1),
          ('show_contact',1),
          ('admin_user','niru'),
          ('admin_pass','bleach2025');
    """)
    conn.commit()
    conn.close()

init_db()

# ─── AUTH ─────────────────────────────────────────────
security = HTTPBearer()

def get_admin_creds():
    conn = get_db()
    u = conn.execute("SELECT value FROM settings WHERE key='admin_user'").fetchone()
    p = conn.execute("SELECT value FROM settings WHERE key='admin_pass'").fetchone()
    conn.close()
    return (u['value'] if u else ADMIN_USER), (p['value'] if p else ADMIN_PASS)

def make_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.utcnow() + timedelta(hours=12), "iat": datetime.utcnow()}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        admin_user, _ = get_admin_creds()
        if payload.get("sub") != admin_user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─── MODELS ───────────────────────────────────────────
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
    visible: Optional[int] = 1

class Skill(BaseModel):
    id: Optional[str] = None
    name: str
    tier: Optional[int] = 1
    visible: Optional[int] = 1
    sort_order: Optional[int] = 0

class Certificate(BaseModel):
    id: Optional[str] = None
    name: str
    org: str
    date: Optional[str] = ""
    icon: Optional[str] = "🏆"
    url: Optional[str] = ""
    visible: Optional[int] = 1
    sort_order: Optional[int] = 0

class SettingsUpdate(BaseModel):
    settings: dict

class CredentialsUpdate(BaseModel):
    new_username: str
    new_password: str
    current_password: str

class VisitEvent(BaseModel):
    page: str
    referrer: Optional[str] = ""

# ─── PUBLIC ROUTES ─────────────────────────────────────
@app.post("/api/auth/login")
def login(req: LoginRequest):
    admin_user, admin_pass = get_admin_creds()
    if req.username == admin_user and req.password == admin_pass:
        return {"token": make_token(req.username), "message": "authenticated"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/auth/verify")
def verify(payload=Depends(verify_token)):
    return {"valid": True, "user": payload["sub"]}

@app.get("/api/projects")
def get_projects():
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE visible=1 ORDER BY sort_order, created").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/skills")
def get_skills():
    conn = get_db()
    rows = conn.execute("SELECT * FROM skills WHERE visible=1 ORDER BY sort_order").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/certificates")
def get_certificates():
    conn = get_db()
    rows = conn.execute("SELECT * FROM certificates WHERE visible=1 ORDER BY sort_order").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/settings/public")
def get_public_settings():
    conn = get_db()
    rows = conn.execute("""SELECT key, value FROM settings WHERE key IN
        ('name','tagline','about','about2','about3','status','status_type',
         'email','github','portfolio_url',
         'show_about','show_projects','show_skills','show_certificates','show_contact')""").fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

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
    projects = conn.execute("SELECT COUNT(*) FROM projects WHERE visible=1").fetchone()[0]
    conn.close()
    return {"total_visits": total, "projects": projects}

# ─── ADMIN ROUTES ──────────────────────────────────────
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

# SETTINGS
@app.get("/api/admin/settings")
def get_all_settings(payload=Depends(verify_token)):
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings WHERE key != 'admin_pass'").fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

@app.post("/api/admin/settings")
def update_settings(body: SettingsUpdate, payload=Depends(verify_token)):
    conn = get_db()
    for key, value in body.settings.items():
        if key == 'admin_pass': continue
        conn.execute("INSERT INTO settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (key, str(value)))
    conn.commit()
    conn.close()
    return {"message": "settings updated"}

@app.post("/api/admin/credentials")
def update_credentials(body: CredentialsUpdate, payload=Depends(verify_token)):
    _, admin_pass = get_admin_creds()
    if body.current_password != admin_pass:
        raise HTTPException(status_code=401, detail="Current password is wrong")
    conn = get_db()
    conn.execute("INSERT INTO settings (key,value) VALUES ('admin_user',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (body.new_username,))
    conn.execute("INSERT INTO settings (key,value) VALUES ('admin_pass',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (body.new_password,))
    conn.commit()
    conn.close()
    return {"message": "credentials updated", "token": make_token(body.new_username)}

# PROJECTS
@app.get("/api/admin/projects")
def admin_get_projects(payload=Depends(verify_token)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects ORDER BY sort_order, created").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/projects")
def create_project(p: Project, payload=Depends(verify_token)):
    pid = p.id or f"proj_{int(time.time()*1000)}"
    conn = get_db()
    conn.execute("INSERT INTO projects (id,name,desc,icon,status,url,github,tech,sort_order,visible) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (pid, p.name, p.desc, p.icon, p.status, p.url, p.github, p.tech, p.sort_order, p.visible))
    conn.commit()
    conn.close()
    return {"id": pid, "message": "created"}

@app.put("/api/admin/projects/{pid}")
def update_project(pid: str, p: Project, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE projects SET name=?,desc=?,icon=?,status=?,url=?,github=?,tech=?,sort_order=?,visible=? WHERE id=?",
                 (p.name, p.desc, p.icon, p.status, p.url, p.github, p.tech, p.sort_order, p.visible, pid))
    conn.commit()
    conn.close()
    return {"message": "updated"}

@app.patch("/api/admin/projects/{pid}/visibility")
def toggle_project(pid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE projects SET visible = CASE WHEN visible=1 THEN 0 ELSE 1 END WHERE id=?", (pid,))
    conn.commit()
    row = conn.execute("SELECT visible FROM projects WHERE id=?", (pid,)).fetchone()
    conn.close()
    return {"visible": row['visible']}

@app.delete("/api/admin/projects/{pid}")
def delete_project(pid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"message": "deleted"}

# SKILLS
@app.get("/api/admin/skills")
def admin_get_skills(payload=Depends(verify_token)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM skills ORDER BY sort_order").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/skills")
def create_skill(s: Skill, payload=Depends(verify_token)):
    sid = s.id or f"skill_{int(time.time()*1000)}"
    conn = get_db()
    conn.execute("INSERT INTO skills (id,name,tier,visible,sort_order) VALUES (?,?,?,?,?)",
                 (sid, s.name, s.tier, s.visible, s.sort_order))
    conn.commit()
    conn.close()
    return {"id": sid, "message": "created"}

@app.put("/api/admin/skills/{sid}")
def update_skill(sid: str, s: Skill, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE skills SET name=?,tier=?,visible=?,sort_order=? WHERE id=?",
                 (s.name, s.tier, s.visible, s.sort_order, sid))
    conn.commit()
    conn.close()
    return {"message": "updated"}

@app.patch("/api/admin/skills/{sid}/visibility")
def toggle_skill(sid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE skills SET visible = CASE WHEN visible=1 THEN 0 ELSE 1 END WHERE id=?", (sid,))
    conn.commit()
    row = conn.execute("SELECT visible FROM skills WHERE id=?", (sid,)).fetchone()
    conn.close()
    return {"visible": row['visible']}

@app.delete("/api/admin/skills/{sid}")
def delete_skill(sid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("DELETE FROM skills WHERE id=?", (sid,))
    conn.commit()
    conn.close()
    return {"message": "deleted"}

# CERTIFICATES
@app.get("/api/admin/certificates")
def admin_get_certificates(payload=Depends(verify_token)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM certificates ORDER BY sort_order").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/certificates")
def create_certificate(c: Certificate, payload=Depends(verify_token)):
    cid = c.id or f"cert_{int(time.time()*1000)}"
    conn = get_db()
    conn.execute("INSERT INTO certificates (id,name,org,date,icon,url,visible,sort_order) VALUES (?,?,?,?,?,?,?,?)",
                 (cid, c.name, c.org, c.date, c.icon, c.url, c.visible, c.sort_order))
    conn.commit()
    conn.close()
    return {"id": cid, "message": "created"}

@app.put("/api/admin/certificates/{cid}")
def update_certificate(cid: str, c: Certificate, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE certificates SET name=?,org=?,date=?,icon=?,url=?,visible=?,sort_order=? WHERE id=?",
                 (c.name, c.org, c.date, c.icon, c.url, c.visible, c.sort_order, cid))
    conn.commit()
    conn.close()
    return {"message": "updated"}

@app.patch("/api/admin/certificates/{cid}/visibility")
def toggle_certificate(cid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("UPDATE certificates SET visible = CASE WHEN visible=1 THEN 0 ELSE 1 END WHERE id=?", (cid,))
    conn.commit()
    row = conn.execute("SELECT visible FROM certificates WHERE id=?", (cid,)).fetchone()
    conn.close()
    return {"visible": row['visible']}

@app.delete("/api/admin/certificates/{cid}")
def delete_certificate(cid: str, payload=Depends(verify_token)):
    conn = get_db()
    conn.execute("DELETE FROM certificates WHERE id=?", (cid,))
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
