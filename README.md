# PDF Mind Map Generator

AI-powered PDF mind map generation system using CrewAI with a supervisor pattern, FastAPI backend, React UI, and local time-series database for monitoring.

## Features

- **PDF Upload & Processing**: Upload PDF documents and extract structured outlines
- **Human-in-the-Loop**: Select chapters/sections for mind map generation with supervisor recommendations
- **Multi-Agent System**: CrewAI supervisor pattern with specialized agents (Supervisor, Extractor, Builder)
- **Real-Time Monitoring**: WebSocket-based live progress updates and agent status
- **Mind Map Generation**: Hierarchical mind maps with page citations
- **Export Options**: JSON, Mermaid, Markdown formats
- **Logging Dashboard**: Search, filter, and export logs
- **Monitoring Stack**: Loki + Prometheus + Grafana for observability

## Architecture

```
+------------------+     +-------------------+     +------------------+
|   React UI       |<--->|   FastAPI         |<--->|   CrewAI         |
|   (Dashboard)    | WS  |   Backend         |     |   Orchestrator   |
+------------------+     +-------------------+     +------------------+
                               |     |                    |
                               v     v                    v
                    +----------+     +------------+  +------------------+
                    |  Loki    |     | Prometheus |  |   Local Ollama   |
                    |  (Logs)  |     | (Metrics)  |  |   LLM Server     |
                    +----------+     +------------+  +------------------+
                          \              /
                           \            /
                            v          v
                         +----------------+
                         |    Grafana     |
                         |   Dashboard    |
                         +----------------+
```

## Platform Support

This project supports both Linux/macOS and Windows:

- **Linux/macOS**: Follow the instructions below
- **Windows**: See [README.windows.md](README.windows.md) for Windows-specific setup with PowerShell scripts

## Prerequisites

- Docker & Docker Compose (or Docker Desktop on Windows)
- Ollama (for local LLM)
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/sunkaramallikarjuna369/pdfextractionusingolama.git
cd pdfextractionusingolama
```

### 2. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Pull Ollama model (run once)
docker exec -it pdf-mindmap-ollama ollama pull llama2
```

### 3. Access the application

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Local Development

### Backend

```bash
cd backend

# Install dependencies
pip install poetry
poetry install

# Create .env file
cp .env.example .env

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Ollama

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama2

# Start Ollama server
ollama serve
```

## Usage

### 1. Upload PDF

Upload a PDF document through the web interface. The system will extract the document structure and outline.

### 2. Select Sections

Review the extracted outline and select which chapters/sections to generate mind maps for. The supervisor agent will provide recommendations based on document structure.

### 3. Approve & Start

Approve the work plan and start the mind map generation process. Monitor progress in real-time through the dashboard.

### 4. View Results

Once complete, view the generated mind maps in tree view, Mermaid code, or JSON format. Export in your preferred format.

### 5. Monitor Logs

Use the Logs tab to search, filter, and export system logs. Access Grafana for advanced monitoring and dashboards.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pdf/upload` | POST | Upload PDF file |
| `/api/v1/pdf/{pdf_id}/outline` | GET | Get document outline |
| `/api/v1/jobs/create` | POST | Create mind map job |
| `/api/v1/jobs/{job_id}` | GET | Get job status |
| `/api/v1/jobs/{job_id}/plan` | PUT | Update work plan |
| `/api/v1/jobs/{job_id}/start` | POST | Start processing |
| `/api/v1/mindmaps/{job_id}` | GET | Get generated mind maps |
| `/api/v1/ws/events/{job_id}` | WS | Real-time events |

## Agent Roles

### Supervisor Agent
- Coordinates the extraction and mind map generation process
- Proposes chunk plans (chapter vs section granularity)
- Validates outputs and issues repair prompts

### Extractor Agent
- Extracts key concepts from PDF sections
- Produces citation-anchored bullet points
- Outputs structured content with page references

### Builder Agent
- Transforms extracted content into mind map structures
- Builds hierarchical node relationships
- Generates MindMapSpec JSON

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model to use | `llama2` |
| `LOKI_HOST` | Loki server URL | `http://localhost:3100` |
| `MAX_RETRIES` | Max retry attempts | `3` |
| `MAX_REPAIR_ATTEMPTS` | Max repair attempts | `2` |

## Monitoring

### Grafana Dashboards

Access Grafana at http://localhost:3000 with default credentials (admin/admin).

Pre-configured dashboards include:
- Application logs (Loki)
- Request rates and latencies (Prometheus)
- System metrics (CPU, Memory)

### Log Queries

Example Loki queries:
```
{job="pdf-mindmap"} |= "error"
{job="pdf-mindmap", agent="Extractor"}
{job="pdf-mindmap"} | json | level="ERROR"
```

## Project Structure

```
pdfextractionusingolama/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── agents/        # CrewAI agents
│   │   ├── schemas/       # Pydantic models
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI app
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   ├── services/      # API client
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── monitoring/
│   ├── prometheus.yml
│   ├── loki-config.yml
│   └── grafana/
├── scripts/               # PowerShell helper scripts (Windows)
│   ├── start.ps1
│   ├── stop.ps1
│   ├── pull-model.ps1
│   ├── logs.ps1
│   ├── status.ps1
│   └── cleanup.ps1
├── docker-compose.yml
├── SYSTEM_DESIGN.md
├── README.md
└── README.windows.md      # Windows setup guide
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
