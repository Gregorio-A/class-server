import os
import sys
import time
import asyncio
import argparse
import subprocess
import venv
import socket
import logging
import secrets
import string
import re
import json
import webbrowser
import threading
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = Path.cwd().resolve()

parser = argparse.ArgumentParser(description="Class-Server V2")
parser.add_argument('-p', '--port', type=int, default=8000)
parser.add_argument('-u', '--user', type=str, default="admin")
parser.add_argument('-pwd', '--password', type=str, default="")
parser.add_argument('-o', '--open', action='store_true')
parser.add_argument('--http', action='store_true')
parser.add_argument('--vscode', action='store_true')
args, _ = parser.parse_known_args()

AUTH_USER = args.user
AUTH_PASS = args.password if args.password else ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
WS_TOKEN = secrets.token_urlsafe(16)
MAGIC_TOKEN = secrets.token_urlsafe(32)

def setup_vscode_integration():
    vscode_dir = WORK_DIR / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    tasks_path = vscode_dir / "tasks.json"

    new_task = {
        "label": "Iniciar Class-Server V2",
        "type": "shell",
        "command": sys.executable,
        "args": [Path(__file__).name, "--http", "--open"],
        "group": {"kind": "build", "isDefault": True},
        "presentation": {"reveal": "always", "panel": "new"}
    }

    tasks_content = {"version": "2.0.0", "tasks": []}
    if tasks_path.exists():
        try:
            with open(tasks_path, "r", encoding="utf-8") as file_descriptor:
                tasks_content = json.load(file_descriptor)
            if "tasks" not in tasks_content:
                tasks_content["tasks"] = []
            tasks_content["tasks"] = [t for t in tasks_content.get("tasks", []) if t.get("label") != "Iniciar Class-Server V2"]
        except (json.JSONDecodeError, PermissionError):
            pass

    tasks_content["tasks"].append(new_task)

    try:
        with open(tasks_path, "w", encoding="utf-8") as file_descriptor:
            json.dump(tasks_content, file_descriptor, indent=4, ensure_ascii=False)
        sys.exit(0)
    except PermissionError:
        print("[Erro] Permissao negada. O arquivo tasks.json esta bloqueado.")
        sys.exit(1)

if args.vscode:
    setup_vscode_integration()

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Depends, HTTPException, status
    from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    import uvicorn
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import qrcode
    if not args.http:
        import cryptography

    # Evita logs WinError 10054 em desconexoes abruptas de socket
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

except ImportError:
    venv_dir = SCRIPT_DIR / ".venv"
    is_windows = sys.platform == "win32"
    venv_python = venv_dir / "Scripts" / "python.exe" if is_windows else venv_dir / "bin" / "python"

    packages = ["fastapi", "uvicorn[standard]", "watchdog", "websockets", "qrcode[pil]"]
    if not args.http:
        packages.append("cryptography")

    def safe_install(python_exe: str, pkgs: list):
        try:
            subprocess.check_call([python_exe, "-m", "pip", "install", "--quiet", "--timeout", "15"] + pkgs)
        except subprocess.CalledProcessError:
            print("[Erro] Falha ao baixar pacotes via PIP. Verifique sua conexao ou regras de firewall.")
            print(f"[Instrucao] Para instalacao manual offline, utilize: {python_exe} -m pip install -r requirements.txt")
            sys.exit(1)

    if sys.executable != str(venv_python):
        if not venv_dir.exists():
            venv.create(venv_dir, with_pip=True)
            safe_install(str(venv_python), packages)

        try:
            subprocess.run([str(venv_python)] + sys.argv)
        except KeyboardInterrupt:
            pass
        sys.exit(0)
    else:
        safe_install(sys.executable, packages)
        try:
            subprocess.run([sys.executable] + sys.argv)
        except KeyboardInterrupt:
            pass
        sys.exit(0)

IGNORE_DIRS = {'.git', 'node_modules', 'venv', '.venv', 'env', '__pycache__', '.idea', '.vscode', 'dist', 'build'}
DEBOUNCE_DELAY = 0.5

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(str(SCRIPT_DIR / "live_server.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def get_free_port(start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1

def generate_self_signed_cert():
    if args.http:
        return None, None

    cert_path = str(SCRIPT_DIR / "server.crt")
    key_path = str(SCRIPT_DIR / "server.key")
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import hashes
        from cryptography.x509.oid import NameOID
        from cryptography import x509
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"localhost")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .sign(key, hashes.SHA256())
        )

        with open(key_path, "wb") as file_descriptor:
            file_descriptor.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        with open(cert_path, "wb") as file_descriptor:
            file_descriptor.write(cert.public_bytes(serialization.Encoding.PEM))

        return cert_path, key_path
    except Exception as error:
        logging.warning(f"Falha SSL, caindo para HTTP: {error}")
        return None, None

RATE_LIMIT = {}
MAX_REQUESTS_PER_MINUTE = 200

def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()

    if ip not in RATE_LIMIT:
        RATE_LIMIT[ip] = []

    RATE_LIMIT[ip] = [timestamp for timestamp in RATE_LIMIT[ip] if now - timestamp < 60]

    if len(RATE_LIMIT[ip]) > MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit excedido.")

    RATE_LIMIT[ip].append(now)

    keys_to_remove = [key for key, timestamps in RATE_LIMIT.items() if not timestamps]
    for key in keys_to_remove:
        del RATE_LIMIT[key]

security = HTTPBasic(auto_error=False)

def verify_credentials(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    if request.url.path in ["/favicon.ico"]:
        return "system_bypass"

    check_rate_limit(request)

    cookie_token = request.cookies.get("magic_cookie")
    if cookie_token and secrets.compare_digest(cookie_token, MAGIC_TOKEN):
        return "qr_user"

    if credentials:
        if secrets.compare_digest(credentials.username, AUTH_USER) and secrets.compare_digest(credentials.password, AUTH_PASS):
            return credentials.username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Basic"},
    )

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.last_triggered = {}

    def is_ignored(self, path: str) -> bool:
        return any(ignored in Path(path).parts for ignored in IGNORE_DIRS)

    def process_event(self, event):
        if event.is_directory or self.is_ignored(event.src_path):
            return

        current_time = time.time()
        path = event.src_path

        if path in self.last_triggered and (current_time - self.last_triggered[path]) < DEBOUNCE_DELAY:
            return

        self.last_triggered[path] = current_time
        filename = os.path.basename(path).lower()

        if filename.endswith('.log') or filename.startswith('.'):
            return

        action = "css" if filename.endswith('.css') else "image" if filename.endswith(('.png', '.jpg', '.jpeg', '.svg', '.webp')) else "reload"
        asyncio.run_coroutine_threadsafe(manager.broadcast(action), self.loop)

    def on_modified(self, event): self.process_event(event)
    def on_created(self, event): self.process_event(event)

JS_INJECT = """
<script>
(function() {
    window.addEventListener('load', () => {
        const scrollY = sessionStorage.getItem('_live_server_scroll');
        if (scrollY) { window.scrollTo(0, parseInt(scrollY)); sessionStorage.removeItem('_live_server_scroll'); }
        try {
            const savedInputs = JSON.parse(sessionStorage.getItem('_live_server_inputs') || '[]');
            savedInputs.forEach(saved => {
                const el = document.getElementById(saved.id) || (saved.name ? document.querySelector(`[name="${saved.name}"]`) : null);
                if (el) {
                    if (saved.type === 'checkbox' || saved.type === 'radio') el.checked = saved.checked;
                    else el.value = saved.value;
                }
            });
            sessionStorage.removeItem('_live_server_inputs');
        } catch(e) {}
    });

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=__WS_TOKEN_PLACEHOLDER__`);

    ws.onmessage = function(event) {
        if (event.data === "reload") {
            sessionStorage.setItem('_live_server_scroll', window.scrollY);
            const inputs = Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                id: el.id, name: el.name, value: el.value, type: el.type, checked: el.checked
            }));
            sessionStorage.setItem('_live_server_inputs', JSON.stringify(inputs));
            location.reload();
        } else if (event.data === "css") {
            document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
                const url = new URL(link.href, window.location.origin);
                url.searchParams.set('_v', Date.now()); link.href = url.href;
            });
        } else if (event.data === "image") {
            document.querySelectorAll('img').forEach(img => {
                const url = new URL(img.src, window.location.origin);
                url.searchParams.set('_v', Date.now()); img.src = url.href;
            });
        }
    };
    ws.onclose = () => setInterval(() => location.reload(), 2000);
})();
</script>
"""

observer = Observer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    event_handler = WatcherHandler(loop)
    observer.schedule(event_handler, path=str(WORK_DIR), recursive=True)
    observer.start()
    yield
    observer.stop()
    observer.join()

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    if not secrets.compare_digest(token, WS_TOKEN):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

@app.get("/_qr_login")
async def qr_login(request: Request, token: str):
    if secrets.compare_digest(token, MAGIC_TOKEN):
        html_content = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8"><title>A Autenticar...</title>
        <script>document.cookie = "magic_cookie={token}; path=/; max-age=2592000; SameSite=Lax"; setTimeout(() => window.location.replace("/"), 600);</script>
        </head><body><h2>Autorizado</h2></body></html>"""
        response = HTMLResponse(content=html_content)
        response.set_cookie(key="magic_cookie", value=token, max_age=2592000, httponly=True)
        return response
    return HTMLResponse("Invalido", status_code=403)

@app.get("/{path:path}")
async def catch_all(request: Request, path: str, username: str = Depends(verify_credentials)):
    requested_path = (WORK_DIR / path).resolve()

    if not requested_path.is_relative_to(WORK_DIR):
        raise HTTPException(status_code=403, detail="Acesso negado fora do diretorio raiz.")

    if requested_path.is_dir():
        index_file = requested_path / "index.html"
        if index_file.exists():
            requested_path = index_file
        else:
            raise HTTPException(status_code=403, detail="Listagem de diretorio desabilitada.")

    if not requested_path.exists() and "." not in requested_path.name:
        html_path = requested_path.with_suffix(".html")
        if html_path.exists():
            requested_path = html_path

    if not requested_path.exists():
        return Response(status_code=404)

    if requested_path.suffix.lower() in [".html", ".htm"]:
        js_code_secured = JS_INJECT.replace('__WS_TOKEN_PLACEHOLDER__', WS_TOKEN)

        try:
            with open(requested_path, "r", encoding="utf-8") as file_descriptor:
                content = file_descriptor.read()
            content_mod = re.sub(r'(?i)(</body>)', rf'{js_code_secured}\n\1', content, count=1)
            if js_code_secured not in content_mod:
                content_mod += js_code_secured
            return HTMLResponse(content=content_mod)
        except Exception as error:
            logging.error(f"Injecao falhou: {error}")
            return FileResponse(requested_path)

    return FileResponse(requested_path)

if __name__ == "__main__":
    local_ip = get_local_ip()
    cert_file, key_file = generate_self_signed_cert()
    protocolo = "https" if cert_file and not args.http else "http"

    porta_ativa = get_free_port(args.port)

    host_binding = "127.0.0.1" if protocolo == "http" else "0.0.0.0"

    print(f"\n{'='*55}")
    print(f" SERVIDOR EM EXECUCAO")
    print(f"{'='*55}")
    print(f"   Local: {protocolo}://localhost:{porta_ativa}")
    print(f"   [ Credenciais ] -> User: {AUTH_USER} | Pass: {AUTH_PASS}\n")

    if host_binding == "0.0.0.0" and local_ip != "127.0.0.1":
        network_url = f"{protocolo}://{local_ip}:{porta_ativa}"
        magic_url = f"{network_url}/_qr_login?token={MAGIC_TOKEN}"
        print(f"   Rede:  {network_url}")

        try:
            qr = qrcode.QRCode(version=1, box_size=1, border=2)
            qr.add_data(magic_url)
            qr.make(fit=True)
            qr.print_tty()
        except Exception:
            pass
    elif protocolo == "http":
        print(f"   [Aviso de Seguranca] Acesso remoto desabilitado no modo HTTP para evitar interceptacao de credenciais.")

    if args.open:
        local_magic_url = f"{protocolo}://localhost:{porta_ativa}/_qr_login?token={MAGIC_TOKEN}"
        threading.Timer(1.5, lambda: webbrowser.open(local_magic_url)).start()

    try:
        if protocolo == "https" and cert_file and key_file:
            uvicorn.run(app, host=host_binding, port=porta_ativa, log_level="error", ssl_keyfile=key_file, ssl_certfile=cert_file)
        else:
            uvicorn.run(app, host=host_binding, port=porta_ativa, log_level="error")
    except KeyboardInterrupt:
        sys.exit(0)
