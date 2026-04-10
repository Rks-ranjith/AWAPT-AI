import os
import struct
import select
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio

if os.name != 'nt':
    import pty
    import fcntl
    import termios

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/console/{finding_id}")
async def interactive_console(websocket: WebSocket, finding_id: int):
    """
    Spawns an interactive PTY session connected over WebSocket.
    This simulates a remote interactive exploit/shell drop.
    Note: On Windows this needs a winpty equivalent or a subprocess wrapper.
    For this prototype, since we are on Windows, we'll use a simulated shell loop using subprocess.
    """
    await websocket.accept()
    logger.info(f"Interactive console connected for finding {finding_id}")
    
    # Check if we're on unix or windows to determine how to run the shell
    if os.name == 'nt':
        # Simulated Windows PTY for cross-platform
        import subprocess
        
        await websocket.send_text("\r\n\033[1;32m[AWAP-AI]\033[0m \033[1;31mINTERACTIVE ATTACK CONSOLE ESTABLISHED\033[0m\r\n")
        await websocket.send_text(f"Proxying traffic through vulnerability context {finding_id}...\r\n\r\n")
        await websocket.send_text("C:\\Windows\\System32> ")
        
        try:
            while True:
                data = await websocket.receive_text()
                # Basic mock logic for executing commands 
                # (A real weaponized engine would route this directly into the Blind RCE vulnerability)
                if data.strip() == "exit":
                    await websocket.send_text("\r\nTerminating OOB connection...\r\n")
                    break
                    
                if data.strip():
                    try:
                        # Actually execute on the worker node for demonstration
                        output = subprocess.check_output(data, shell=True, stderr=subprocess.STDOUT, timeout=5)
                        await websocket.send_text("\r\n" + output.decode("utf-8", "replace").replace('\n', '\r\n'))
                    except subprocess.CalledProcessError as e:
                        await websocket.send_text("\r\n" + e.output.decode("utf-8", "replace").replace('\n', '\r\n'))
                    except subprocess.TimeoutExpired:
                        await websocket.send_text("\r\nCommand timed out.\r\n")
                
                await websocket.send_text("C:\\Windows\\System32> ")
                
        except WebSocketDisconnect:
            logger.info("Terminal disconnected by user.")
        except Exception as e:
            logger.error(f"Console error: {e}")
    else:
        # PTY logic for Linux
        pid, fd = pty.fork()
        if pid == 0:
            os.execlp("bash", "bash")
            return
            
        try:
            while True:
                r, w, e = select.select([fd, websocket.client_state], [], [], 0.1)
                if fd in r:
                    output = os.read(fd, 1024)
                    if output:
                        await websocket.send_bytes(output)
                        
                # Async read from websocket
                try:
                    data = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.1)
                    os.write(fd, data)
                except asyncio.TimeoutError:
                    pass
        except Exception:
            pass
        finally:
            os.close(fd)

# Needed for Real-Time UI Link
try:
    import redis.asyncio as redis
except ImportError:
    import redis

from pydantic_settings import BaseSettings

class WSSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"

@router.websocket("/ws/monitor/{scan_id}")
async def monitor_stream(websocket: WebSocket, scan_id: int):
    """
    Connects to the Redis Pub/Sub stream to pipe raw autonomous engine logs
    directly into the React LiveMonitor.
    """
    await websocket.accept()
    settings = WSSettings()
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    last_id = "0"
    stream_key = f"livestream:scan:{scan_id}"
    
    try:
        while True:
            # Block for up to 1 second waiting for new messages
            messages = await redis_client.xread({stream_key: last_id}, count=10, block=1000)
            if messages:
                for stream, msg_list in messages:
                    for msg_id, payload in msg_list:
                        last_id = msg_id
                        if "data" in payload:
                            await websocket.send_text(payload["data"])
            
            # Keepalive / check if client disconnected
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        logger.info(f"Monitor stream disconnected for scan {scan_id}")
    except Exception as e:
        logger.error(f"Redis Stream Error: {e}")
    finally:
        await redis_client.aclose()
