# PDF Mind Map Generator - Windows Setup Guide

This guide provides Windows-specific instructions for running the PDF Mind Map Generator on Windows 10/11.

## Prerequisites

### 1. Install Docker Desktop for Windows

Download and install Docker Desktop from https://www.docker.com/products/docker-desktop/

During installation, ensure you select the WSL 2 backend option for best performance.

After installation:
1. Open Docker Desktop
2. Go to Settings > General
3. Ensure "Use the WSL 2 based engine" is checked
4. Go to Settings > Resources > WSL Integration
5. Enable integration with your default WSL 2 distro

### 2. Verify Docker Installation

Open PowerShell and run:

```powershell
docker --version
docker compose version
```

Both commands should return version information.

## Quick Start

### Option 1: Using PowerShell Scripts (Recommended)

We provide PowerShell helper scripts in the `scripts/` directory:

```powershell
# Start all services
.\scripts\start.ps1

# Pull Ollama model (run once after first start)
.\scripts\pull-model.ps1

# Stop all services
.\scripts\stop.ps1

# View logs
.\scripts\logs.ps1

# Clean up (remove volumes)
.\scripts\cleanup.ps1
```

### Option 2: Manual Commands

Open PowerShell as Administrator and navigate to the project directory:

```powershell
cd C:\path\to\pdfextractionusingolama

# Start all services
docker compose up -d

# Pull Ollama model (run once)
docker exec -it pdf-mindmap-ollama ollama pull llama2

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Accessing the Application

Once services are running, access:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3001 | - |
| Backend API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |

## Troubleshooting

### Port Conflicts

If you see port binding errors, check if other applications are using the ports:

```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :3001
netstat -ano | findstr :3000
```

To change ports, edit `docker-compose.yml` and modify the port mappings.

### WSL 2 Not Enabled

If Docker Desktop shows WSL 2 errors:

1. Open PowerShell as Administrator
2. Run: `wsl --install`
3. Restart your computer
4. Open Docker Desktop and enable WSL 2 backend

### Slow Performance

For best performance:
1. Ensure WSL 2 backend is enabled in Docker Desktop
2. Store the project files in WSL filesystem (`\\wsl$\Ubuntu\home\...`) rather than Windows filesystem
3. Allocate more memory to WSL 2 in `.wslconfig`

Create `C:\Users\<YourUsername>\.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=4
```

### Container Startup Issues

If containers fail to start:

```powershell
# Check container logs
docker compose logs ollama
docker compose logs backend
docker compose logs frontend

# Restart specific service
docker compose restart backend

# Full cleanup and restart
docker compose down -v
docker compose up -d
```

### Network Issues

If services can't communicate:

```powershell
# Check network
docker network ls
docker network inspect pdf-mindmap-network

# Recreate network
docker compose down
docker network rm pdf-mindmap-network
docker compose up -d
```

### Volume Permission Issues

If you encounter permission errors with volumes:

```powershell
# Remove all volumes and recreate
docker compose down -v
docker volume prune -f
docker compose up -d
```

## Local Development on Windows

### Backend Development

1. Install Python 3.11+ from https://www.python.org/downloads/
2. Install Poetry:
   ```powershell
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```
3. Navigate to backend and install dependencies:
   ```powershell
   cd backend
   poetry install
   ```
4. Create `.env` file:
   ```powershell
   Copy-Item .env.example .env
   ```
5. Start development server:
   ```powershell
   poetry run uvicorn app.main:app --reload --port 8000
   ```

### Frontend Development

1. Install Node.js 20+ from https://nodejs.org/
2. Navigate to frontend and install dependencies:
   ```powershell
   cd frontend
   npm install
   ```
3. Start development server:
   ```powershell
   npm run dev
   ```

### Ollama (Native Windows)

Ollama also has a native Windows installer:

1. Download from https://ollama.com/download/windows
2. Install and run Ollama
3. Pull a model:
   ```powershell
   ollama pull llama2
   ```
4. Update `backend/.env` to use `OLLAMA_HOST=http://localhost:11434`

## Windows-Specific Notes

### Line Endings

If you clone the repository on Windows, Git may convert line endings to CRLF. This shouldn't affect Docker builds, but if you encounter issues:

```powershell
git config core.autocrlf input
git rm --cached -r .
git reset --hard
```

### File Paths

The Docker Compose file uses relative paths (`./monitoring/...`) which work on Windows. If you need to use absolute paths, use forward slashes:

```yaml
volumes:
  - C:/Users/username/project/monitoring:/etc/monitoring
```

### Firewall

Windows Firewall may block Docker ports. If you can't access services:

1. Open Windows Defender Firewall
2. Click "Allow an app or feature through Windows Defender Firewall"
3. Ensure Docker Desktop is allowed for both Private and Public networks

## Getting Help

If you encounter issues not covered here:

1. Check Docker Desktop logs (right-click tray icon > Troubleshoot)
2. Check WSL logs: `wsl --status`
3. Open an issue on GitHub with:
   - Windows version (`winver`)
   - Docker Desktop version
   - Error messages and logs
