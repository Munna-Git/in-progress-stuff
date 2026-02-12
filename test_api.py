
import requests
import sys
import time

def test_api():
    base_url = "http://localhost:8081"
    
    # Wait for server to start
    print("Waiting for server...")
    for _ in range(10):
        try:
            resp = requests.get(f"{base_url}/health")
            if resp.status_code == 200:
                print("Server is up!")
                break
        except:
            time.sleep(1)
    else:
        print("Server failed to start.")
        sys.exit(1)
        
    # Test query
    query = "What is the power of freeSpace 3?"
    print(f"Testing query: '{query}'")
    resp = requests.post(f"{base_url}/api/query", json={"query": query})
    
    if resp.status_code == 200:
        data = resp.json()
        print("Response received:")
        print(f"Answer: {data['answer'][:100]}...")
        print(f"Confidence: {data['confidence']}")
        print(f"Products Used: {data['products_used']}")
        print("SUCCESS")
    else:
        print(f"Query failed: {resp.status_code} {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    test_api()
