import sys
import time
import os

print("--- STARTING GRANULAR IMPORT DEBUG ---")
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print(f"PID: {os.getpid()}")

def trace_import(module_name):
    print(f"[DEBUG] Attempting to import {module_name}...", flush=True)
    start = time.time()
    try:
        __import__(module_name)
        print(f"[DEBUG] ✓ {module_name} imported in {time.time() - start:.2f}s", flush=True)
    except Exception as e:
        print(f"[DEBUG] ✗ {module_name} FAILED: {e}", flush=True)

# Test base libraries
trace_import("numpy")
trace_import("cv2")
trace_import("PIL")

# Test torch sub-modules
trace_import("torch._C")
trace_import("torch.version")
trace_import("torch")

print("--- DEBUG COMPLETE ---")
