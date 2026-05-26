import httpx
import time

API_URL = "http://localhost:8000/api/v1"
TARGET_ID = "9065b95f-841c-4981-aa1a-7bcbe42e2b60"

def run_scan():
    print(f"Triggering scan for target {TARGET_ID}...")
    try:
        response = httpx.post(f"{API_URL}/scans", json={
            "target_id": TARGET_ID,
            "profile": "standard"
        }, timeout=10.0)
        
        if response.status_code != 200:
            print("Failed to trigger scan:", response.status_code, response.text)
            return
            
        scan_data = response.json()
        scan_id = scan_data["id"]
        print(f"Successfully started scan! Scan ID: {scan_id}")
        
        print("Polling scan status...")
        while True:
            status_res = httpx.get(f"{API_URL}/scans/{scan_id}")
            if status_res.status_code == 200:
                scan = status_res.json()
                print(f"State: {scan['state']} | Progress: {scan['progress']}%")
                if scan['state'] in ["COMPLETE", "FAILED", "ABORTED"]:
                    print(f"Scan finished with state: {scan['state']}")
                    break
            else:
                print("Failed to get status:", status_res.status_code)
            time.sleep(5)
            
    except Exception as e:
        print("Error during scan run:", e)

if __name__ == "__main__":
    run_scan()
