import asyncio
import time
from fastapi import FastAPI, Request, Response, Query, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="Vulnerability Playground Target")

# HTML Index Page for Crawler Discovery
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Vulnerability Playground Target</title>
  <style>
    body { font-family: sans-serif; padding: 40px; background: #0f172a; color: #f1f5f9; }
    h1 { color: #10b981; }
    a { color: #38bdf8; text-decoration: none; font-weight: bold; }
    a:hover { text-decoration: underline; }
    li { margin-bottom: 12px; }
  </style>
</head>
<body>
  <h1>AWAP-Ai Security Test Playground</h1>
  <p>This is a custom target built to test all vulnerability modules of AWAP-Ai DAST scanner.</p>
  <ul>
    <li><a href="/api/sqli?id=1">SQL Injection Endpoint</a></li>
    <li><a href="/api/xss?name=guest">Reflected XSS Endpoint</a></li>
    <li><a href="/api/traversal?file=welcome.txt">Path Traversal Endpoint</a></li>
    <li><a href="/api/cmd?ip=127.0.0.1">Command Injection Endpoint</a></li>
    <li><a href="/api/ssrf?url=http://example.com">SSRF Endpoint</a></li>
    <li><a href="/api/redirect?url=http://example.com">Open Redirect Endpoint</a></li>
    <li><a href="/api/cors">CORS Misconfiguration Endpoint</a></li>
    <li><a href="/api/headers">Security Headers Leak Endpoint</a></li>
    <li><a href="/api/prototype?__proto__[polluted]=true">Prototype Pollution Endpoint</a></li>
    <li><a href="/api/llm?prompt=hello">LLM Prompt Injection Endpoint</a></li>
    <li><a href="/graphql">GraphQL Introspection Endpoint</a></li>
    <li><a href="/api/jwt">JWT Verification Endpoint</a></li>
    <li><a href="/api/users/1">IDOR Endpoint</a></li>
    <li><a href="/api/nosql?username[$ne]=admin">NoSQL Injection Endpoint</a></li>
    <li><a href="/api/upload">Unrestricted File Upload Endpoint</a></li>
  </ul>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML

# 1. SQL Injection
@app.get("/api/sqli")
async def sqli(id: str = "1", q: str = ""):
    param = q or id
    param_lower = param.lower()
    
    # Time-based SQLi simulation
    if "sleep" in param_lower:
        await asyncio.sleep(5.0)
        return JSONResponse({"status": "success", "result": "Delayed query response"})
        
    # Error-based SQLi simulation
    error_sigs = ["'", "''", "or 1=1", "union select"]
    if any(sig in param_lower for sig in error_sigs):
        return Response(
            content="sqlite_error: near \"'\": syntax error. Unclosed quotation mark.",
            status_code=500,
            media_type="text/plain"
        )
        
    return JSONResponse({"status": "success", "data": {"id": id, "name": "Item Name", "category": "General"}})

# 2. Reflected XSS
@app.get("/api/xss", response_class=HTMLResponse)
async def xss(name: str = "guest", q: str = ""):
    param = q or name
    # Echo back input unsanitized
    return f"""
    <html>
      <body>
        <h1>Hello User!</h1>
        <div id="user-display">Welcome back, {param}!</div>
      </body>
    </html>
    """

# 3. Path Traversal
@app.get("/api/traversal")
async def traversal(file: str = "welcome.txt", path: str = ""):
    param = path or file
    if ".." in param or "/etc/passwd" in param or "passwd" in param:
        passwd_content = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
            "sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
            "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
        )
        return Response(content=passwd_content, status_code=200, media_type="text/plain")
    return JSONResponse({"status": "success", "content": f"Contents of file {param}: Welcome to the app!"})

# 4. Command Injection
@app.get("/api/cmd")
async def cmd(ip: str = "127.0.0.1", cmd: str = ""):
    param = cmd or ip
    # Check for command injection shell characters
    injection_chars = [";", "|", "&", "`", "$"]
    if any(char in param for char in injection_chars):
        cmd_output = "uid=33(www-data) gid=33(www-data) groups=33(www-data)\nroot:x:0:0:root"
        return JSONResponse({"status": "success", "output": cmd_output})
    return JSONResponse({"status": "success", "output": f"PING {param} (127.0.0.1) 56(84) bytes of data.\n64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.03 ms"})

# 5. SSRF
@app.get("/api/ssrf")
async def ssrf(url: str = "http://example.com"):
    # Simulate requesting internal metadata
    if "169.254.169.254" in url or "metadata" in url:
        return JSONResponse({
            "ami-id": "ami-12345678",
            "instance-id": "i-0abcdef123456",
            "role": "admin-secrets-reader"
        })
    return JSONResponse({"status": "success", "resolved_url": url, "response_status": 200})

# 6. Open Redirect
@app.get("/api/redirect")
async def redirect(url: str = "http://example.com"):
    # Simple open redirect
    return RedirectResponse(url=url, status_code=302)

# 7. CORS Misconfiguration
@app.get("/api/cors")
async def cors(request: Request):
    origin = request.headers.get("origin", "*")
    headers = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS"
    }
    return JSONResponse(content={"status": "success", "message": "Sensitive account details exposed"}, headers=headers)

# 8. Security Headers Leak (Returns response lacking security headers)
@app.get("/api/headers")
async def headers():
    response = Response(content="Check response headers for security controls.", status_code=200, media_type="text/plain")
    # Explicitly clear headers standard security tools look for
    if "X-Frame-Options" in response.headers: del response.headers["X-Frame-Options"]
    if "X-Content-Type-Options" in response.headers: del response.headers["X-Content-Type-Options"]
    if "Content-Security-Policy" in response.headers: del response.headers["Content-Security-Policy"]
    return response

# 9. Prototype Pollution
@app.get("/api/prototype")
async def prototype(request: Request):
    query_params = str(request.query_params)
    if "__proto__" in query_params or "constructor" in query_params:
        return JSONResponse({"status": "success", "polluted": True, "evidence": "Prototype parameter successfully parsed"})
    return JSONResponse({"status": "success", "polluted": False})

# 10. LLM Prompt Injection
@app.get("/api/llm")
async def llm(prompt: str = "hello"):
    prompt_lower = prompt.lower()
    if "ignore instructions" in prompt_lower or "system instructions" in prompt_lower or "leak" in prompt_lower:
        return JSONResponse({
            "response": "Understood. Leaking core configuration key: [FLAG_API_SECURE_TOKEN_55819]",
            "injected": True
        })
    return JSONResponse({"response": "This is a simulated AI assistant agent response.", "injected": False})

# 11. GraphQL Introspection
@app.post("/graphql")
@app.get("/graphql")
async def graphql(request: Request):
    # If introspection query is made
    body = ""
    try:
        body = (await request.body()).decode()
    except:
        pass
        
    query = request.query_params.get("query", "") + body
    if "__schema" in query or "__type" in query:
        introspection_schema = {
            "data": {
                "__schema": {
                    "queryType": {"name": "Query"},
                    "mutationType": {"name": "Mutation"},
                    "types": [
                        {"name": "User", "kind": "OBJECT", "description": "System database user schema"},
                        {"name": "AdminSecrets", "kind": "OBJECT", "description": "Intentionally vulnerable schema"}
                    ]
                }
            }
        }
        return JSONResponse(introspection_schema)
    return JSONResponse({"data": {"message": "GraphQL query received"}})

# 12. JWT None Algorithm
@app.get("/api/jwt")
async def jwt_endpoint(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            parts = token.split(".")
            import base64
            import json
            header_json = base64.b64decode(parts[0] + "==").decode()
            header = json.loads(header_json)
            if header.get("alg") == "none":
                return JSONResponse({"status": "success", "message": "Bypassed JWT verification via 'none' algorithm!"})
        except:
            pass
    return JSONResponse({"status": "error", "message": "Invalid JWT signature"}, status_code=401)

# 13. IDOR
@app.get("/api/users/{user_id}")
async def idor(user_id: int):
    # Vulnerable IDOR endpoint
    users_db = {
        1: {"username": "john_doe", "role": "user", "bio": "Short bio for John."},
        2: {"username": "jane_doe_with_a_very_long_biography_field_to_trigger_idor", "role": "user", "bio": "Jane has a very long biography description field designed to trigger DAST IDOR difference checks."},
        99: {"username": "admin", "role": "administrator", "secret_key": "FLAG_SUPER_ADMIN_PASSWORD_9981"}
    }
    user = users_db.get(user_id)
    if user:
        return JSONResponse({"status": "success", "data": user})
    return JSONResponse({"status": "error", "message": "User not found"}, status_code=404)

# 14. NoSQL Injection
@app.get("/api/nosql")
async def nosql(request: Request):
    query_params = str(request.query_params)
    if "$ne" in query_params or "$gt" in query_params or "$where" in query_params:
        return JSONResponse({
            "status": "success",
            "message": "Filtered accounts successfully via custom query",
            "data": [
                {"username": "admin", "role": "administrator", "secret_key": "FLAG_NOSQL_SECRET_TOKEN_892"},
                {"username": "john_doe", "role": "user", "secret_key": "FLAG_USER_KEY_123"}
            ]
        })
    return JSONResponse({
        "status": "success",
        "data": [{"username": "guest", "role": "user"}]
    })

# 15. Unrestricted File Upload
@app.get("/api/upload", response_class=HTMLResponse)
async def upload_form():
    return """
    <html>
      <head>
        <title>Vulnerable File Upload Target</title>
        <style>
          body { font-family: sans-serif; padding: 40px; background: #0f172a; color: #f1f5f9; }
          h1 { color: #f43f5e; }
        </style>
      </head>
      <body>
        <h1>Upload Management Terminal</h1>
        <p>This portal uploads documents directly to the public webroot.</p>
        <form action="/api/upload" method="post" enctype="multipart/form-data">
          <input type="file" name="file"><br><br>
          <input type="submit" value="Upload Asset">
        </form>
      </body>
    </html>
    """

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or "unknown.txt"
    content = await file.read()
    return JSONResponse({
        "status": "success",
        "message": f"Asset uploaded successfully to /uploads/{filename}",
        "url": f"/uploads/{filename}",
        "bytes_written": len(content),
        "vulnerable": True
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("awap.playground.app:app", host="0.0.0.0", port=8080, reload=False)
