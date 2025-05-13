import sys
import platform
import subprocess
import os

VENV_DIR = ".venv"

def get_venv_executable_path(executable_name):
    """Constructs the path to an executable within the virtual environment."""
    system = platform.system()
    if system == "Windows":
        path = os.path.join(VENV_DIR, "Scripts", f"{executable_name}.exe")
    else: # Linux, macOS
        path = os.path.join(VENV_DIR, "bin", executable_name)
    
    if not os.path.exists(VENV_DIR):
        print(f"Error: Virtual environment directory '{VENV_DIR}' not found.")
        print(f"Please create it first, e.g., by running 'uv venv'")
        sys.exit(1)
    if not os.path.exists(path):
        print(f"Error: Executable '{executable_name}' not found at '{path}'.")
        print(f"Ensure it's installed in the virtual environment (e.g., 'uv pip install {executable_name} fastapi uvicorn').")
        sys.exit(1)
    return path

def run_local_server():
    print("Starting FastAPI server locally...")
    uvicorn_path = get_venv_executable_path("uvicorn")
    cmd = [
        uvicorn_path,
        "app.main:app",
        "--host", "localhost", # For local browser access
        "--port", "8000",
        "--reload"
    ]
    print(f"Executing: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\nUvicorn server stopped by user (KeyboardInterrupt).")
        if process.poll() is None: # Check if child process is still running
            process.terminate()
            process.wait() # Wait for termination
        sys.exit(0) # Exit gracefully
    except FileNotFoundError:
        print(f"Error: Could not execute '{uvicorn_path}'. Ensure the path is correct and uvicorn is installed in the venv.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while running uvicorn: {e}")
        sys.exit(1)
    finally:
        if 'process' in locals() and process.returncode is not None:
             sys.exit(process.returncode)

def run_docker_server():
    print("Building and running the application with Docker Compose...")
    try:
        subprocess.run(["docker", "ps"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    except FileNotFoundError:
        print("Error: 'docker' command not found. Please ensure Docker is installed and in your PATH.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: Docker command timed out. Docker might be unresponsive.")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("Error: Docker is not running or not responding correctly. Please start Docker.")
        sys.exit(1)

    original_cwd = os.getcwd()
    docker_compose_dir_to_cd_into = None # Will be "docker" or remain None (if root)
    
    if os.path.exists(os.path.join("docker", "docker-compose.yml")):
        print("Using docker-compose.yml from docker/ directory.")
        docker_compose_dir_to_cd_into = "docker"
    elif os.path.exists("docker-compose.yml"):
        print("Using docker-compose.yml from project root directory.")
    else:
        print("Error: Cannot find docker-compose.yml in project root or in docker/ directory.")
        sys.exit(1)

    cmd = ["docker", "compose", "up", "--build"]
    
    current_exec_dir = original_cwd
    if docker_compose_dir_to_cd_into:
        current_exec_dir = os.path.join(original_cwd, docker_compose_dir_to_cd_into)
        
    print(f"Executing: {' '.join(cmd)} (in directory: {current_exec_dir})")
    try:
        # Execute in the directory where docker-compose.yml is expected
        process = subprocess.run(cmd, check=False, cwd=current_exec_dir)
        sys.exit(process.returncode)
    except FileNotFoundError:
        print(f"Error: 'docker compose' command failed. Ensure Docker is installed and configured correctly.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while running Docker Compose: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["local", "docker"]:
        print("Usage: python run.py [local|docker]")
        print("  local   - Runs the application locally using the development server.")
        print("  docker  - Builds and runs the application using Docker Compose.")
        sys.exit(1)

    command = sys.argv[1]

    if command == "local":
        run_local_server()
    elif command == "docker":
        run_docker_server()
