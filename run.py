import subprocess
import sys
import os
import time
import threading

def run_fastapi():
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "src.backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
    ])

def run_streamlit():
    time.sleep(3)
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/frontend/app.py",
        "--server.port", "5000",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "dark",
        "--theme.primaryColor", "#4CAF50",
        "--theme.backgroundColor", "#0e1117",
        "--theme.secondaryBackgroundColor", "#1a1d24",
        "--theme.textColor", "#e0e0e0",
    ])

if __name__ == "__main__":
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()
    run_streamlit()
