import httpx
import json

def run():
    url = "http://127.0.0.1:8000/api/v1/scans"
    payload = {
        "target_id": "9450f5d5-5512-446f-ba35-a945e9048c38",
        "profile": "standard"
    }
    resp = httpx.post(url, json=payload)
    print("Response Status:", resp.status_code)
    print("Response Body:")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    run()
