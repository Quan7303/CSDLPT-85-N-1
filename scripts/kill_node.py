"""Kill a node process by port number."""
import subprocess
import sys
import platform

def kill_by_port(port: int):
    print(f"Killing process on port {port}...")
    if platform.system() == "Windows":
        result = subprocess.run(
            f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr LISTENING ^| findstr :{port}\') do taskkill /F /PID %a',
            shell=True, capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            f"lsof -ti:{port} | xargs kill -9",
            shell=True, capture_output=True, text=True
        )
    print(result.stdout or result.stderr or f"Port {port} process killed.")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    kill_by_port(port)
