"""
COLAB SETUP UTILITY - Cyber Dome 2026
--------------------------------------
Paste this into a Colab cell to initialize the GPU Bridge:
!pip install requests opencv-python-headless
!python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/Sai03SkAr/Railway-Surveillance-BitsGoa/vauldy/backend/docs/remote_ai_server.py', 'remote_ai_server.py')"
!python remote_ai_server.py
"""
import os
import sys

def main():
    print("="*60)
    print("  RAILGUARD AI - COLAB GPU BRIDGE SETUP")
    print("="*60)
    print("\n[INFO] Initializing environment for remote inference...")
    
    # Check for GPU
    try:
        import torch
        if torch.cuda.is_available():
            print(f"[OK] GPU Detected: {torch.cuda.get_device_name(0)}")
        else:
            print("[WARNING] No GPU detected. Bridge will run on CPU (SLOW).")
    except ImportError:
        print("[!] Torch not found. Falling back to CPU inference.")

    print("\n[INSTRUCTIONS]")
    print("1. Ensure 'ngrok' is installed and authenticated if using tunneling.")
    print("2. Run the remote_ai_server.py script directly.")
    print("\n[COMMAND TO RUN]")
    print("-" * 20)
    print("python remote_ai_server.py")
    print("-" * 20)

if __name__ == "__main__":
    main()
