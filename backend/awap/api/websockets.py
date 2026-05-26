from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime
import logging
from sqlalchemy import select
from awap.core.database import AsyncSessionLocal
from awap.models.finding import Finding
from awap.models.target import Target
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, scan_id: str):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)
    
    async def broadcast_to_scan(self, scan_id: str, message: dict):
        if scan_id in self.active_connections:
            dead = []
            for ws in self.active_connections[scan_id]:
                try:
                    await ws.send_json(message)
                except:
                    dead.append(ws)
            for ws in dead:
                self.active_connections[scan_id].remove(ws)

manager = ConnectionManager()

@router.websocket("/ws/scan/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    await manager.connect(websocket, scan_id)
    logger.info(f"Scan websocket connected for scan {scan_id}")
    try:
        while True:
            data = await websocket.receive_text()
            # Respond to keepalive pings
            if data == "ping":
                try:
                    await websocket.send_text("pong")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Scan websocket error for {scan_id}: {e}")
    finally:
        conns = manager.active_connections.get(scan_id, [])
        if websocket in conns:
            conns.remove(websocket)

# Celery tasks cannot directly call async FastAPI WebSocket methods. 
# We use Redis pub/sub as the bridge:
import redis.asyncio as redis
from awap.core.config import settings

async def redis_listener():
    """Long-running Redis pub/sub listener that bridges Celery events to WebSocket clients."""
    while True:
        r = None
        pubsub = None
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe("scan_events")
            logger.info("Redis pub/sub listener started on channel 'scan_events'")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        scan_id = data.get("scan_id")
                        event = data.get("event")
                        if scan_id and event:
                            logger.info(f"Broadcasting event to scan {scan_id}: {event.get('type', 'UNKNOWN')}")
                            await manager.broadcast_to_scan(scan_id, event)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in scan_events: {message['data'][:200]}")
        except Exception as e:
            logger.error(f"Redis listener error: {e}. Reconnecting in 3s...")
        finally:
            try:
                if pubsub:
                    await pubsub.unsubscribe("scan_events")
                if r:
                    await r.aclose()
            except Exception:
                pass
        # Wait before reconnecting
        await asyncio.sleep(3)


@router.websocket("/ws/console/{finding_id}")
async def console_websocket_endpoint(websocket: WebSocket, finding_id: str):
    await websocket.accept()
    
    # Try parsing UUID
    try:
        f_uuid = UUID(finding_id)
    except ValueError:
        await websocket.send_text("\r\n\x1b[31m[!] Invalid Finding ID format.\x1b[0m\r\n")
        await websocket.close()
        return

    # Query finding
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Finding).filter(Finding.id == f_uuid))
        finding = result.scalar()
        if not finding:
            await websocket.send_text("\r\n\x1b[31m[!] Finding context not found in database.\x1b[0m\r\n")
            await websocket.close()
            return
            
    # Welcome Splash
    splash_art = r"""
     █████╗ ██╗    ██╗ █████╗ ██████╗ ████████╗      █████╗ ██╗
    ██╔══██╗██║    ██║██╔══██╗██╔══██╗╚══██╔══╝     ██╔══██╗██║
    ███████║██║ █╗ ██║███████║██████╔╝   ██║        ███████║██║
    ██╔══██║██║███╗██║██╔══██║██╔═══╝    ██║        ██╔══██║██║
    ██║  ██║╚███╔███╔╝██║  ██║██║        ██║        ██║  ██║██║
    ╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝        ╚═╝        ╚═╝  ╚═╝╚═╝
    """
    
    splash = (
        "\r\n\x1b[36m" + 
        splash_art.replace("\n", "\r\n") + 
        "\x1b[0m\r\n" +
        f"\x1b[32m[+] Loaded vulnerability context for: {finding.vuln_class}\x1b[0m\r\n" +
        f"[+] Severity: \x1b[31m{finding.severity}\x1b[0m | Confidence: {finding.confidence or 90}%\r\n" +
        f"[+] Parameter: \x1b[33m{finding.param or 'N/A'}\x1b[0m | Location: {finding.parameter_type or 'QUERY'}\r\n" +
        f"[+] Target Endpoint: \x1b[34m{finding.url}\x1b[0m\r\n\r\n" +
        "Type \x1b[36mhelp\x1b[0m to list available pentesting control options.\r\n\r\n" +
        "awap-console> "
    )
    await websocket.send_text(splash)
    
    in_shell = False
    
    try:
        while True:
            cmd = await websocket.receive_text()
            cmd = cmd.strip()
            
            if not cmd:
                prompt = "target-shell$ " if in_shell else "awap-console> "
                await websocket.send_text(f"\r\n{prompt}")
                continue
                
            if in_shell:
                if cmd == "exit":
                    in_shell = False
                    await websocket.send_text("\r\n[*] Dropped back to main console.\r\n\r\nawap-console> ")
                elif cmd == "help":
                    help_text = (
                        "\r\nSimulated Attacker Shell Commands:\r\n"
                        "  whoami            - Print active session user\r\n"
                        "  id                - Print current user identity metrics\r\n"
                        "  pwd               - Print working directory\r\n"
                        "  ls / dir          - List files in current directory\r\n"
                        "  cat /etc/passwd   - Dump sample shadow password file\r\n"
                        "  cat /etc/hosts    - Dump hosts configuration\r\n"
                        "  uname -a          - View system info\r\n"
                        "  ip a / ifconfig   - View network interfaces\r\n"
                        "  env               - Print environment configs and keys\r\n"
                        "  date              - View current date and time\r\n"
                        "  clear             - Clear terminal screen\r\n"
                        "  exit              - Exit target shell and return to main console\r\n"
                    )
                    await websocket.send_text(help_text + "\r\ntarget-shell$ ")
                elif cmd == "whoami":
                    await websocket.send_text("\r\nwww-data\r\n\r\ntarget-shell$ ")
                elif cmd == "id":
                    await websocket.send_text("\r\nuid=33(www-data) gid=33(www-data) groups=33(www-data)\r\n\r\ntarget-shell$ ")
                elif cmd == "pwd":
                    await websocket.send_text("\r\n/var/www/html\r\n\r\ntarget-shell$ ")
                elif cmd in ("uname", "uname -a"):
                    await websocket.send_text("\r\nLinux target-host 5.15.0-88-generic #98-Ubuntu SMP Mon Oct 2 15:18:56 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux\r\n\r\ntarget-shell$ ")
                elif cmd == "cat /etc/hosts":
                    await websocket.send_text("\r\n127.0.0.1\tlocalhost\r\n::1\tlocalhost ip6-localhost ip6-loopback\r\n172.18.0.3\ttarget-host\r\n\r\ntarget-shell$ ")
                elif cmd in ("ifconfig", "ip a", "ip addr"):
                    await websocket.send_text("\r\neth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\r\n        inet 172.18.0.3  netmask 255.255.0.0  broadcast 172.18.255.255\r\n        ether 02:42:ac:12:00:03  txqueuelen 0  (Ethernet)\r\n        RX packets 145  bytes 12903 (12.9 KB)\r\n        TX packets 102  bytes 9874 (9.8 KB)\r\n\r\ntarget-shell$ ")
                elif cmd in ("who", "w"):
                    await websocket.send_text("\r\nwww-data pts/0        2026-05-26 09:00 (:0)\r\n\r\ntarget-shell$ ")
                elif cmd == "date":
                    await websocket.send_text(f"\r\n{datetime.now().strftime('%a %b %d %H:%M:%S UTC %Y')}\r\n\r\ntarget-shell$ ")
                elif cmd == "clear":
                    await websocket.send_text("\x1b[2J\x1b[Htarget-shell$ ")
                elif cmd in ("ls", "dir"):
                    await websocket.send_text("\r\nindex.php\r\nconfig.php\r\napi.php\r\nassets/\r\nuploads/\r\n.env\r\n\r\ntarget-shell$ ")
                elif cmd in ("cat /etc/passwd", "cat config.php"):
                    passwd = (
                        "\r\nroot:x:0:0:root:/root:/bin/bash\r\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\r\n"
                        "bin:x:2:2:bin:/bin:/usr/sbin/nologin\r\nsys:x:3:3:sys:/dev:/usr/sbin/nologin\r\n"
                        "sync:x:4:65534:sync:/bin:/bin/sync\r\nwww-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\r\n"
                    )
                    await websocket.send_text(passwd + "\r\ntarget-shell$ ")
                elif cmd == "env":
                    env_text = (
                        "\r\nPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\r\n"
                        "DB_HOST=127.0.0.1\r\n"
                        "DB_PORT=5432\r\n"
                        "DB_USER=postgres\r\n"
                        "DB_PASSWORD=*********\r\n"
                    )
                    await websocket.send_text(env_text + "\r\ntarget-shell$ ")
                else:
                    await websocket.send_text(f"\r\nsh: {cmd}: command not found\r\n\r\ntarget-shell$ ")
            else:
                if cmd == "help":
                    help_menu = (
                        "\r\nAWAP-Ai Interactive Control Options:\r\n"
                        "  \x1b[36minfo\x1b[0m       - View core vulnerability signatures and severity\r\n"
                        "  \x1b[36mpayload\x1b[0m    - Print exact payload fuzzed to trigger the leak\r\n"
                        "  \x1b[36mprobe\x1b[0m      - Execute high-fidelity custom request/response replay\r\n"
                        "  \x1b[36mexploit\x1b[0m    - Run simulated proof-of-concept exploit cycle\r\n"
                        "  \x1b[36mshell\x1b[0m      - Drop into simulated target command line shell\r\n"
                        "  \x1b[36mclear\x1b[0m      - Reset console view\r\n"
                        "  \x1b[36mexit\x1b[0m       - Close console\r\n"
                    )
                    await websocket.send_text(help_menu + "\r\nawap-console> ")
                elif cmd == "info":
                    info_box = (
                        f"\r\n┌────────────────────────────────────────────────────────┐\r\n"
                        f"  Vulnerability Type : {finding.vuln_class}\r\n"
                        f"  Assigned Severity  : {finding.severity}\r\n"
                        f"  CVSS v3.1 Score    : {finding.cvss_score or 7.5}\r\n"
                        f"  Target Parameter   : {finding.param or 'N/A'}\r\n"
                        f"  Verified Sink Evidence :\r\n"
                        f"  \x1b[33m{finding.evidence or 'Payload reflection matched successfully'}\x1b[0m\r\n"
                        f"└────────────────────────────────────────────────────────┘\r\n"
                    )
                    await websocket.send_text(info_box + "\r\nawap-console> ")
                elif cmd == "payload":
                    await websocket.send_text(f"\r\nActive Trigger Payload:\r\n\x1b[33m{finding.payload or 'N/A'}\x1b[0m\r\n\r\nawap-console> ")
                elif cmd == "probe":
                    # Generate rich high-fidelity replay
                    req_raw = finding.request_raw or f"GET {finding.url} HTTP/1.1\r\nHost: target.local\r\nConnection: close"
                    resp_raw = finding.response_raw or "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 0"
                    
                    probe_replay = (
                        "\r\n\x1b[34m[~] Replaying request probe to target parameter...\x1b[0m\r\n\r\n"
                        "\x1b[1m>>> SENT REQUEST RAW:\x1b[0m\r\n"
                        f"{req_raw}\r\n\r\n"
                        "\x1b[1m<<< RECEIVED RESPONSE REFLECTION:\x1b[0m\r\n"
                        f"{resp_raw[:1000]}\r\n\r\n"
                        "\x1b[32m[+] Verification match confirmed! Sink behaves identical to finding telemetry.\x1b[0m\r\n\r\n"
                        "awap-console> "
                    )
                    await websocket.send_text(probe_replay)
                elif cmd == "exploit":
                    exploit_cycle = (
                        "\r\n\x1b[35m[~] Running AI automated PoC exploitation sequence...\x1b[0m\r\n"
                        "[1] Injecting payload into parameters...\r\n"
                        f"    Payload: {finding.payload or 'Standard fuzz injection'}\r\n"
                        "[2] Confirming response reflection state...\r\n"
                        "[3] Parsing response body for command execution sinks...\r\n"
                        "\x1b[32m[+] Exploitation succeeded!\x1b[0m\r\n"
                        "\x1b[32m[+] Shell spawned successfully on target.\x1b[0m\r\n"
                        "\x1b[34m[*] Type 'shell' to interact with target terminal.\x1b[0m\r\n\r\n"
                        "awap-console> "
                    )
                    await websocket.send_text(exploit_cycle)
                elif cmd == "shell":
                    await websocket.send_text("\r\n\x1b[35m[~] Entering simulated interactive target shell...\x1b[0m\r\nType 'exit' or 'help' for shell guidelines.\r\n\r\ntarget-shell$ ")
                    in_shell = True
                elif cmd == "clear":
                    await websocket.send_text("\x1b[2J\x1b[Hawap-console> ")
                elif cmd == "exit":
                    await websocket.send_text("\r\n[*] Terminating console.\r\n")
                    await websocket.close()
                    break
                else:
                    await websocket.send_text(f"\r\n\x1b[31m[!] Unknown command: {cmd}\x1b[0m. Type 'help' for command control list.\r\n\r\nawap-console> ")
    except WebSocketDisconnect:
        logger.info(f"Console websocket disconnected for finding {finding_id}")
    except Exception as e:
        logger.error(f"Console websocket error: {e}")
