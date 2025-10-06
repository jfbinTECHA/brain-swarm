import asyncio, os, re, subprocess, shlex, datetime as dt, json, logging
from typing import Optional, List, Dict, Any
import httpx
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, Session, create_engine, select
from passlib.hash import bcrypt
from jose import jwt, JWTError
import psutil
import time
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# -------------------- Config --------------------
APP_PORT = int(os.environ.get("ADMIN_PANEL_PORT", "8060"))
JWT_SECRET = os.environ.get("ADMIN_PANEL_SECRET", "change-me-please")  # set in systemd
JWT_ALG = "HS256"
DB_URL = "sqlite:///./admin.db"
ALLOW_REGISTRATION = os.environ.get("ALLOW_REGISTRATION", "false").lower() == "true"

# Brain-Swarm API endpoints (for decoupled integration)
BRAIN_SWARM_BASE_URL = os.environ.get("BRAIN_SWARM_BASE_URL", "http://localhost:8000")
BRAIN_SWARM_API_KEY = os.environ.get("BRAIN_SWARM_API_KEY", "")  # Optional API key for authentication

# Prometheus metrics
REQUEST_COUNT = Counter('admin_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
RESPONSE_TIME = Histogram('admin_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])
ACTIVE_USERS = Gauge('admin_active_users', 'Number of currently active users')
LOGIN_ATTEMPTS = Counter('admin_login_attempts_total', 'Total login attempts', ['result'])
SYSTEM_CPU = Gauge('admin_system_cpu_percent', 'System CPU usage percentage')
SYSTEM_MEMORY = Gauge('admin_system_memory_percent', 'System memory usage percentage')
SYSTEM_DISK = Gauge('admin_system_disk_percent', 'System disk usage percentage')
HEALTH_CHECKS = Counter('admin_health_checks_total', 'Total health checks performed', ['service', 'status'])

# -------------------- Brain-Swarm API helpers --------------------
async def call_brain_swarm_api(endpoint: str, method: str = "GET", **kwargs) -> Optional[Dict[str, Any]]:
    """Call Brain-Swarm API endpoint with proper authentication"""
    url = f"{BRAIN_SWARM_BASE_URL}{endpoint}"
    headers = {}
    if BRAIN_SWARM_API_KEY:
        headers["Authorization"] = f"Bearer {BRAIN_SWARM_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, **kwargs)
            elif method == "POST":
                response = await client.post(url, headers=headers, **kwargs)
            else:
                return None

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Brain-Swarm API call failed: {response.status_code} for {endpoint}")
                return None
    except Exception as e:
        logger.warning(f"Brain-Swarm API call error: {e} for {endpoint}")
        return None

async def get_brain_swarm_login_attempts() -> List[Dict[str, Any]]:
    """Get login attempts from Brain-Swarm API"""
    result = await call_brain_swarm_api("/internal/login_attempts")
    if result and "attempts" in result:
        return result["attempts"]
    return []

async def get_brain_swarm_system_stats() -> Optional[Dict[str, Any]]:
    """Get system stats from Brain-Swarm API"""
    return await call_brain_swarm_api("/internal/system_stats")

async def get_brain_swarm_user_keys() -> List[Dict[str, Any]]:
    """Get SSH key fingerprints from Brain-Swarm API"""
    result = await call_brain_swarm_api("/internal/user_keys")
    if result and "keys" in result:
        return result["keys"]
    return []

engine = create_engine(DB_URL, echo=False)
app = FastAPI(title="Local Admin Panel")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------- Models --------------------
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="viewer")  # "admin" | "viewer"
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.utcnow())

class LoginAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: dt.datetime
    user: Optional[str] = None
    src_ip: Optional[str] = None
    result: str  # "SUCCESS" | "FAIL"
    raw: str

class Registration(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password_hash: str
    status: str = Field(default="pending")  # "pending" | "approved" | "rejected"
    requested_at: dt.datetime = Field(default_factory=lambda: dt.datetime.utcnow())

def init_db():
    SQLModel.metadata.create_all(engine)

# -------------------- Auth helpers --------------------
def create_token(username: str, role: str) -> str:
    payload = {"sub": username, "role": role, "exp": dt.datetime.utcnow() + dt.timedelta(hours=12)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def current_user(request: Request) -> Optional[User]:
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        return None
    with Session(engine) as s:
        return s.exec(select(User).where(User.username == data.get("sub"))).first()

def require_role(role: str):
    def dep(user: User = Depends(current_user)):
        if not user:
            raise HTTPException(302, detail="Login required")
        if role == "admin" and user.role != "admin":
            raise HTTPException(403, "Admin required")
        return user
    return dep

# -------------------- SSH key fingerprints --------------------
def list_authorized_key_fingerprints() -> List[dict]:
    # For each /home/<user>/.ssh/authorized_keys, compute fingerprints
    entries = []
    base = "/home"
    if not os.path.isdir(base):
        return entries
    for uname in os.listdir(base):
        ak = os.path.join(base, uname, ".ssh", "authorized_keys")
        if not os.path.isfile(ak):
            continue
        try:
            with open(ak, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Use ssh-keygen -lf via stdin
                    cmd = "ssh-keygen -lf -"
                    p = subprocess.run(shlex.split(cmd), input=(line+"\n").encode(),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out = p.stdout.decode().strip()
                    if out:
                        # e.g., "3072 SHA256:abc.. user@host (RSA)"
                        entries.append({"user": uname, "line": i, "fingerprint": out})
        except Exception as e:
            entries.append({"user": uname, "line": 0, "fingerprint": f"error: {e}"})
    return entries

# -------------------- journalctl ingestion --------------------
SSH_RE = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2}).*sshd.*?(Failed|Accepted)\s+password\s+for\s+(invalid user\s+)?(?P<user>[\w\-\.\@]+)\s+from\s+(?P<ip>[\d\.]+)"
)

MONTHS = {m: i for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], start=1)}

async def ingest_sshd_loop():
    # Poll journalctl periodically; store new lines
    last_seen = dt.datetime.utcnow() - dt.timedelta(minutes=10)
    while True:
        try:
            cmd = ["journalctl", "-u", "sshd", "--since", last_seen.isoformat(), "--no-pager"]
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            now_year = dt.datetime.utcnow().year
            with Session(engine) as s:
                for line in p.stdout.splitlines():
                    m = SSH_RE.search(line)
                    if not m:
                        continue
                    month = MONTHS.get(m.group("month"), 1)
                    day = int(m.group("day"))
                    t = dt.datetime.strptime(m.group("time"), "%H:%M:%S").time()
                    ts = dt.datetime(now_year, month, day, t.hour, t.minute, t.second)
                    user = m.group("user")
                    ip = m.group("ip")
                    result = "SUCCESS" if "Accepted" in m.group(0) else "FAIL"
                    la = LoginAttempt(ts=ts, user=user, src_ip=ip, result=result, raw=line)
                    s.add(la)
                s.commit()
            last_seen = dt.datetime.utcnow()
        except Exception:
            pass
        await asyncio.sleep(20)

@app.on_event("startup")
async def on_startup():
    init_db()
    # ensure at least one admin exists
    with Session(engine) as s:
        admin = s.exec(select(User).where(User.role == "admin")).first()
        if not admin:
            # default admin: admin / admin (force change!)
            s.add(User(username="admin", password_hash=bcrypt.hash("admin"), role="admin"))
            s.commit()
    asyncio.create_task(ingest_sshd_loop())

# -------------------- Routes (HTML) --------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request, user: Optional[User] = Depends(current_user)):
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "allow_reg": ALLOW_REGISTRATION})

@app.post("/login")
def do_login(username: str = Form(...), password: str = Form(...)):
    with Session(engine) as s:
        u = s.exec(select(User).where(User.username == username)).first()
        if not u or not bcrypt.verify(password, u.password_hash):
            raise HTTPException(401, "Invalid credentials")
        token = create_token(u.username, u.role)
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie("session", token, httponly=True, secure=False, samesite="lax", max_age=12*3600)
        return resp

@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("session")
    return resp

@app.get("/attempts", response_class=HTMLResponse)
async def attempts_page(request: Request, user: User = Depends(require_role("viewer"))):
    # Try Brain-Swarm API first, fallback to local data
    brain_swarm_attempts = await get_brain_swarm_login_attempts()
    if brain_swarm_attempts:
        # Convert Brain-Swarm format to local format
        rows = []
        for attempt in brain_swarm_attempts[-500:]:  # Limit to 500
            rows.append(type('LoginAttempt', (), {
                'ts': dt.datetime.fromisoformat(attempt['ts']) if isinstance(attempt['ts'], str) else attempt['ts'],
                'user': attempt.get('user'),
                'src_ip': attempt.get('src_ip'),
                'result': attempt.get('result', 'UNKNOWN')
            })())
    else:
        # Fallback to local database
        with Session(engine) as s:
            rows = s.exec(select(LoginAttempt).order_by(LoginAttempt.ts.desc()).limit(500)).all()

    return templates.TemplateResponse("attempts.html", {"request": request, "user": user, "rows": rows})

@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, user: User = Depends(require_role("admin"))):
    with Session(engine) as s:
        rows = s.exec(select(User).order_by(User.created_at.desc())).all()
        regs = s.exec(select(Registration).order_by(Registration.requested_at.desc())).all()
    return templates.TemplateResponse("users.html", {"request": request, "user": user, "rows": rows, "regs": regs, "allow_reg": ALLOW_REGISTRATION})

@app.post("/users/create")
def create_user(username: str = Form(...), password: str = Form(...), role: str = Form("viewer"), user: User = Depends(require_role("admin"))):
    with Session(engine) as s:
        if s.exec(select(User).where(User.username == username)).first():
            raise HTTPException(400, "Username exists")
        s.add(User(username=username, password_hash=bcrypt.hash(password), role=role))
        s.commit()
    return RedirectResponse("/users", status_code=302)

@app.get("/keys", response_class=HTMLResponse)
async def keys_page(request: Request, user: User = Depends(require_role("viewer"))):
    # Try Brain-Swarm API first, fallback to local parsing
    brain_swarm_keys = await get_brain_swarm_user_keys()
    if brain_swarm_keys:
        fps = brain_swarm_keys
    else:
        # Fallback to local parsing
        fps = list_authorized_key_fingerprints()

    return templates.TemplateResponse("keys.html", {"request": request, "user": user, "fps": fps})

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    if not ALLOW_REGISTRATION:
        raise HTTPException(403, "Registration disabled")
    with Session(engine) as s:
        if s.exec(select(User).where(User.username == username)).first():
            raise HTTPException(400, "Username exists")
        s.add(Registration(username=username, password_hash=bcrypt.hash(password)))
        s.commit()
    return RedirectResponse("/login", status_code=302)

@app.post("/registrations/{reg_id}/{action}")
def handle_registration(reg_id: int, action: str, user: User = Depends(require_role("admin"))):
    with Session(engine) as s:
        reg = s.get(Registration, reg_id)
        if not reg:
            raise HTTPException(404, "Not found")
        if action == "approve":
            s.add(User(username=reg.username, password_hash=reg.password_hash, role="viewer"))
            reg.status = "approved"
        elif action == "reject":
            reg.status = "rejected"
        else:
            raise HTTPException(400, "Invalid action")
        s.add(reg)
        s.commit()
    return RedirectResponse("/users", status_code=302)

@app.post("/block-ip")
def block_ip(ip: str = Form(...), user: User = Depends(require_role("admin"))):
    # Try ufw if available, otherwise suggest command
    if subprocess.call(["which", "ufw"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        subprocess.call(["sudo", "ufw", "deny", "from", ip])
        msg = f"Applied 'ufw deny from {ip}'"
    else:
        msg = f"Run manually: sudo iptables -A INPUT -s {ip} -j DROP"
    return RedirectResponse(f"/attempts?msg={msg}", status_code=302)

@app.get("/sysstats")
async def sysstats():
    """Get system statistics (CPU, memory, disk usage)"""
    # Try Brain-Swarm API first, fallback to local psutil
    brain_swarm_stats = await get_brain_swarm_system_stats()
    if brain_swarm_stats:
        return brain_swarm_stats
    else:
        # Fallback to local system stats
        return {
            "cpu": psutil.cpu_percent(interval=0.1),
            "mem": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent
        }

@app.get("/console", response_class=HTMLResponse)
async def console(request: Request, user: User = Depends(require_role("viewer"))):
    """Serve the unified console dashboard"""
    try:
        with open("dashboards.json", "r") as f:
            dashboards = json.load(f)
    except FileNotFoundError:
        # Fallback to default dashboards
        dashboards = [
            {"name": "Mission Control", "url": "/mission-control", "status": "UP"},
            {"name": "Grafana", "url": "http://localhost:3000", "status": "UP"},
            {"name": "Prometheus", "url": "http://localhost:9090", "status": "UP"},
        ]
    return templates.TemplateResponse("console.html", {"request": request, "user": user, "dashboards": dashboards})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "local-admin", "timestamp": dt.datetime.utcnow()}

@app.get("/status")
async def status_check():
    """Status endpoint with more details"""
    with Session(engine) as s:
        user_count = s.exec(select(User)).all()
        attempt_count = s.exec(select(LoginAttempt)).all()

    return {
        "status": "operational",
        "service": "local-admin",
        "users": len(user_count),
        "login_attempts": len(attempt_count),
        "timestamp": dt.datetime.utcnow()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # Update system metrics
    SYSTEM_CPU.set(psutil.cpu_percent(interval=0.1))
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
    SYSTEM_DISK.set(psutil.disk_usage("/").percent)

    # Update active users count
    with Session(engine) as s:
        active_users = len(s.exec(select(User)).all())
        ACTIVE_USERS.set(active_users)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=APP_PORT, reload=False)