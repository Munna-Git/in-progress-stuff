
import uvicorn
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Bose Product Engine UI...")
    print("--------------------------------------------------")
    print(">>> Open http://localhost:8081 in your browser <<<")
    print("--------------------------------------------------")
    
    # Run the API server
    # reload=True allows auto-restart on code changes (dev mode)
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8081, reload=True)
