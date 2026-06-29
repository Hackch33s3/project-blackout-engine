from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
from scanner import run_scan

load_dotenv()

app = FastAPI()

ENGINE_API_KEY = os.getenv("ENGINE_API_KEY")

class ScanRequest(BaseModel):
    clientId: str
    full_name: str
    past_city: str

async def verify_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    if token != ENGINE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token

@app.get("/")
def root():
    return {"status": "ok", "service": "project-blackout-engine"}

@app.post("/start-scan")
async def start_scan(request: ScanRequest, api_key: str = Depends(verify_api_key)):
    try:
        print(f"[+] Scan triggered for client: {request.clientId}")
        
        result = await run_scan(
            client_id=request.clientId,
            full_name=request.full_name,
            past_city=request.past_city
        )
        
        return {
            "status": "success",
            "client_id": request.clientId,
            "targets_found": len(result.get("targets", [])),
            "targets": result.get("targets", [])
        }
        
    except Exception as e:
        print(f"[-] Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))