import subprocess
import sys
import os
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)
import config

def main():
    print("=" * 60)
    print("  Starting all distributed nodes...")
    print("=" * 60)

    processes = []
    for i, node in enumerate(config.NODES):
        print(f"  Starting {node['name']} on port {node['port']}...")
        proc = subprocess.Popen(
            [sys.executable, os.path.join(PROJECT_DIR, "nodes", "node_server.py"), str(i)],
            cwd=PROJECT_DIR
        )
        processes.append(proc)

    time.sleep(2)
    print("\n  All nodes started. Press Ctrl+C to stop all.\n")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n  Stopping all nodes...")
        for p in processes:
            p.terminate()
        print("  All nodes stopped.")

if __name__ == '__main__':
    main()
