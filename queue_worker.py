import os
import time
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ENGINE_URL = os.getenv("ENGINE_URL")
ENGINE_API_KEY = os.getenv("ENGINE_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def process_queue():
    # 1. Find the oldest pending job
    response = supabase.table('scan_queue')\
        .select('id, client_id')\
        .eq('status', 'PENDING')\
        .order('created_at', desc=False)\
        .limit(1)\
        .execute()

    if not response.data:
        return

    job = response.data[0]
    job_id = job['id']
    client_id = job['client_id']

    # 2. Mark as processing
    supabase.table('scan_queue').update({'status': 'PROCESSING'}).eq('id', job_id).execute()

    # 3. Get client PII
    client_data = supabase.table('clients').select('full_name, past_city').eq('id', client_id).single().execute()
    
    if not client_data.data:
        supabase.table('scan_queue').update({'status': 'FAILED'}).eq('id', job_id).execute()
        return

    # 4. Trigger the Python Engine
    try:
        res = requests.post(
            f"{ENGINE_URL}/start-scan",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ENGINE_API_KEY}'
            },
            json={
                'clientId': client_id,
                'full_name': client_data.data['full_name'],
                'past_city': client_data.data['past_city']
            },
            timeout=300 # 5 minute timeout for scraping
        )
        
        if res.status_code == 200:
            supabase.table('scan_queue').update({'status': 'COMPLETED'}).eq('id', job_id).execute()
            print(f"[+] Job {job_id} completed for client {client_id}")
        else:
            supabase.table('scan_queue').update({'status': 'FAILED'}).eq('id', job_id).execute()
            print(f"[-] Job {job_id} failed. Engine returned {res.status_code}")
            
    except Exception as e:
        supabase.table('scan_queue').update({'status': 'FAILED'}).eq('id', job_id).execute()
        print(f"[-] Job {job_id} crashed: {e}")

if __name__ == "__main__":
    print("[*] Queue Worker started. Polling every 10 seconds...")
    while True:
        try:
            process_queue()
        except Exception as e:
            print(f"[!] Worker error: {e}")
        time.sleep(10)