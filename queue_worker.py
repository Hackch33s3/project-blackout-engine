import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ENGINE_URL = os.getenv("ENGINE_URL")
ENGINE_API_KEY = os.getenv("ENGINE_API_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def supabase_get(table, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

def supabase_update(table, id_value, data, id_column="id"):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{id_column}=eq.{id_value}"
    r = requests.patch(url, headers=HEADERS, json=data)
    r.raise_for_status()

def supabase_insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers={**HEADERS, "Prefer": "return=representation"}, json=data)
    r.raise_for_status()
    return r.json()

def process_queue():
    # 1. Find the oldest pending job
    data = supabase_get("scan_queue", {
        "status": "eq.PENDING",
        "order": "created_at.asc",
        "limit": "1",
        "select": "id,client_id"
    })

    if not data:
        return

    job = data[0]
    job_id = job["id"]
    client_id = job["client_id"]

    # 2. Mark as processing
    supabase_update("scan_queue", job_id, {"status": "PROCESSING"})
    supabase_update("clients", client_id, {"status": "SCANNING"})

    # 3. Get client PII
    client_data = supabase_get("clients", {
        "id": f"eq.{client_id}",
        "select": "full_name,past_city"
    })

    if not client_data:
        supabase_update("scan_queue", job_id, {"status": "FAILED"})
        return

    client = client_data[0]

    # 4. Trigger the Python Engine
    try:
        res = requests.post(
            f"{ENGINE_URL}/start-scan",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ENGINE_API_KEY}"
            },
            json={
                "clientId": client_id,
                "full_name": client["full_name"],
                "past_city": client["past_city"]
            },
            timeout=300
        )

        if res.status_code == 200:
            data = res.json()
            targets = data.get("targets", [])

            for t in targets:
                supabase_insert("targets", {
                    "client_id": client_id,
                    "broker_name": t.get("broker_name", t.get("source", "unknown")),
                    "profile_url": t["url"],
                    "status": "EXPOSED"
                })

            supabase_update("scan_queue", job_id, {"status": "COMPLETED"})
            supabase_update("clients", client_id, {"status": "AUDIT_COMPLETE"})
            print(f"[+] Job {job_id} completed for client {client_id} — {len(targets)} targets found")
        else:
            supabase_update("scan_queue", job_id, {"status": "FAILED"})
            print(f"[-] Job {job_id} failed. Engine returned {res.status_code}")

    except Exception as e:
        supabase_update("scan_queue", job_id, {"status": "FAILED"})
        print(f"[-] Job {job_id} crashed: {e}")

if __name__ == "__main__":
    print("[*] Queue Worker started. Polling every 10 seconds...")
    while True:
        try:
            process_queue()
        except Exception as e:
            print(f"[!] Worker error: {e}")
        time.sleep(10)
