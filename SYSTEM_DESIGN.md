# PDF Mind Map Generation System - Comprehensive Design Document

## Executive Summary

This document outlines the architecture and design for a PDF Mind Map Generation System using CrewAI with a supervisor pattern, FastAPI backend, React UI, and local time-series database for monitoring. The system enables users to upload PDFs, have AI agents collaboratively generate mind maps with human-in-the-loop decision making, and monitor the entire process through a real-time dashboard.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Technology Stack Recommendations](#2-technology-stack-recommendations)
3. [CrewAI Supervisor Pattern Design](#3-crewai-supervisor-pattern-design)
4. [FastAPI Backend Design](#4-fastapi-backend-design)
5. [React UI Design](#5-react-ui-design)
6. [Time-Series Database & Monitoring](#6-time-series-database--monitoring)
7. [Data Models & Schemas](#7-data-models--schemas)
8. [Workflow & State Management](#8-workflow--state-management)
9. [Error Handling & Resilience](#9-error-handling--resilience)
10. [Improvements & Best Practices](#10-improvements--best-practices)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
+------------------+     +-------------------+     +------------------+
|                  |     |                   |     |                  |
|   React UI       |<--->|   FastAPI         |<--->|   CrewAI         |
|   (Dashboard)    | WS  |   Backend         |     |   Orchestrator   |
|                  |     |                   |     |                  |
+------------------+     +-------------------+     +------------------+
                               |     |                    |
                               |     |                    v
                               |     |           +------------------+
                               |     |           |   Local Ollama   |
                               |     |           |   LLM Server     |
                               |     |           +------------------+
                               |     |
                               v     v
                    +----------+     +------------+
                    |  Loki    |     | Prometheus |
                    |  (Logs)  |     | (Metrics)  |
                    +----------+     +------------+
                          \              /
                           \            /
                            v          v
                         +----------------+
                         |    Grafana     |
                         |   Dashboard    |
                         +----------------+
```

### 1.2 Component Interaction Flow

```
User Upload PDF
       |
       v
+------+-------+
| PDF Parser   |  --> Extract TOC, Headings, Text by Page
+------+-------+
       |
       v
+------+-------+
| UI: Outline  |  --> Human selects Chapter/Section boundaries
| Selection    |
+------+-------+
       |
       v
+------+-------+
| Supervisor   |  --> Creates work plan, dispatches to workers
| Agent        |
+------+-------+
       |
   +---+---+
   |       |
   v       v
+--+--+ +--+--+
|W1   | |W2   |  --> Worker agents process sections
+--+--+ +--+--+
   |       |
   +---+---+
       |
       v
+------+-------+
| Validator    |  --> Schema + Quality validation
+------+-------+
       |
       v
+------+-------+
| Mind Map     |  --> Render final visualization
| Renderer     |
+------+-------+
```

---

## 2. Technology Stack Recommendations

### 2.1 Core Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Backend | FastAPI | Async support, WebSocket, OpenAPI docs |
| Frontend | React + TypeScript | Type safety, component reusability |
| UI Library | Tailwind CSS + shadcn/ui | Modern, customizable components |
| AI Framework | CrewAI | Native supervisor pattern, agent orchestration |
| LLM | Ollama (local) | Privacy, no API costs, customizable |
| Time-Series DB | Loki + Prometheus | Free, lightweight, Grafana integration |
| Dashboard | Grafana | Powerful visualization, free, local |
| Mind Map Render | Markmap / Mermaid | Browser-native, exportable |

### 2.2 Why Loki + Prometheus + Grafana?

**Loki (for Logs)**
- Designed for log aggregation with label-based filtering
- Perfect for agent activity logs (job_id, section_id, agent_name)
- Low resource footprint for local machines
- Native Grafana integration

**Prometheus (for Metrics)**
- Industry standard for numeric metrics
- Tracks latencies, success/fail counts, queue depth
- Alerting capabilities built-in

**Grafana (for Dashboard)**
- Free and open source
- Supports both Loki and Prometheus
- Real-time dashboards with auto-refresh
- Search, filter, and downloadable reports

### 2.3 Alternative Options Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| InfluxDB | SQL-like queries | More complex schema design | Good alternative |
| TimescaleDB | Powerful, PostgreSQL-based | Heavier, overkill for MVP | Future option |
| SQLite + Custom | Simple, no setup | No native time-series features | Not recommended |

---

## 3. CrewAI Supervisor Pattern Design

### 3.1 Agent Architecture

```
                    +----------------------+
                    |   SUPERVISOR AGENT   |
                    |   (Orchestrator)     |
                    +----------+-----------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
    +---------+----------+           +---------+----------+
    |   EXTRACTOR AGENT  |           |   BUILDER AGENT    |
    |   (Worker 1)       |           |   (Worker 2)       |
    +--------------------+           +--------------------+
```

### 3.2 Agent Roles & Responsibilities

#### Supervisor Agent
```python
Role: "PDF Mind Map Orchestrator"
Goal: "Coordinate the extraction and mind map generation process"
Backstory: "Expert project manager specializing in document analysis workflows"

Responsibilities:
1. Receive structured PDF outline from backend
2. Propose chunk plan (chapter vs section) to human
3. Wait for human confirmation/adjustment
4. Dispatch immutable work items to workers
5. Validate outputs from workers
6. Issue repair prompts if validation fails
7. Aggregate final results
```

#### Extractor Agent (Worker 1)
```python
Role: "Content Extractor & Summarizer"
Goal: "Extract and summarize key concepts from PDF sections"
Backstory: "Expert at distilling complex documents into structured insights"

Responsibilities:
1. Process assigned section text
2. Extract key concepts, relationships, hierarchies
3. Produce citation-anchored bullet points
4. Output structured JSON with page references
```

#### Builder Agent (Worker 2)
```python
Role: "Mind Map Architect"
Goal: "Transform structured content into visual mind maps"
Backstory: "Specialist in information visualization and knowledge graphs"

Responsibilities:
1. Receive structured bullet points from Extractor
2. Build hierarchical node structure
3. Establish parent-child relationships
4. Generate MindMapSpec JSON
5. Ensure proper depth and balance
```

### 3.3 CrewAI Implementation Pattern

```python
from crewai import Agent, Task, Crew, Process

# Supervisor Agent
supervisor = Agent(
    role="PDF Mind Map Orchestrator",
    goal="Coordinate extraction and mind map generation",
    backstory="Expert project manager for document analysis",
    llm=ollama_llm,
    verbose=True,
    allow_delegation=True
)

# Worker Agents
extractor = Agent(
    role="Content Extractor",
    goal="Extract key concepts from PDF sections",
    backstory="Expert at distilling documents into insights",
    llm=ollama_llm,
    verbose=True
)

builder = Agent(
    role="Mind Map Builder",
    goal="Transform content into mind map structures",
    backstory="Specialist in information visualization",
    llm=ollama_llm,
    verbose=True
)

# Crew with Hierarchical Process (Supervisor Pattern)
crew = Crew(
    agents=[supervisor, extractor, builder],
    tasks=[...],
    process=Process.hierarchical,
    manager_agent=supervisor,
    verbose=True
)
```

### 3.4 Task Flow Design

```
Phase 1: Planning (Supervisor)
├── Analyze PDF structure
├── Propose chapter/section boundaries
└── Wait for human approval

Phase 2: Extraction (Worker 1 - Extractor)
├── For each approved section:
│   ├── Extract text content
│   ├── Identify key concepts
│   ├── Create structured summary
│   └── Add citations (page numbers)

Phase 3: Building (Worker 2 - Builder)
├── For each extracted section:
│   ├── Transform to node hierarchy
│   ├── Establish relationships
│   └── Generate MindMapSpec JSON

Phase 4: Validation (Supervisor)
├── Validate schema compliance
├── Check coverage completeness
├── If failed: Issue repair prompt
└── If passed: Aggregate results

Phase 5: Rendering
└── Convert MindMapSpec to visual format
```

---

## 4. FastAPI Backend Design

### 4.1 API Endpoints

```
/api/v1/
├── /pdf/
│   ├── POST   /upload              # Upload PDF file
│   ├── GET    /{job_id}/outline    # Get extracted outline
│   └── GET    /{job_id}/status     # Get processing status
│
├── /jobs/
│   ├── POST   /create              # Create mind map job
│   ├── GET    /{job_id}            # Get job details
│   ├── PUT    /{job_id}/plan       # Human approves/modifies plan
│   ├── POST   /{job_id}/start      # Start processing
│   ├── POST   /{job_id}/pause      # Pause processing
│   ├── POST   /{job_id}/resume     # Resume processing
│   └── DELETE /{job_id}            # Cancel job
│
├── /sections/
│   ├── GET    /{job_id}/sections           # List all sections
│   ├── GET    /{section_id}                # Get section details
│   ├── POST   /{section_id}/retry          # Retry failed section
│   └── PUT    /{section_id}/reassign       # Reassign to different worker
│
├── /mindmaps/
│   ├── GET    /{job_id}                    # Get generated mind map
│   ├── GET    /{job_id}/download           # Download mind map (PNG/SVG/JSON)
│   └── GET    /{job_id}/revisions          # Get revision history
│
├── /agents/
│   ├── GET    /status                      # Get all agent statuses
│   └── GET    /{agent_id}/logs             # Get agent logs
│
├── /logs/
│   ├── GET    /                            # Query logs with filters
│   └── GET    /export                      # Export logs as report
│
└── /ws/
    └── /events/{job_id}            # WebSocket for real-time updates
```

### 4.2 Backend Architecture

```
app/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── models/
│   ├── __init__.py
│   ├── pdf.py              # PDF-related models
│   ├── job.py              # Job models
│   ├── section.py          # Section models
│   ├── mindmap.py          # Mind map models
│   └── agent.py            # Agent models
├── schemas/
│   ├── __init__.py
│   ├── requests.py         # Request schemas
│   └── responses.py        # Response schemas
├── services/
│   ├── __init__.py
│   ├── pdf_service.py      # PDF parsing service
│   ├── job_service.py      # Job management service
│   ├── crew_service.py     # CrewAI orchestration
│   ├── mindmap_service.py  # Mind map generation
│   └── logging_service.py  # Structured logging
├── agents/
│   ├── __init__.py
│   ├── supervisor.py       # Supervisor agent
│   ├── extractor.py        # Extractor agent
│   └── builder.py          # Builder agent
├── utils/
│   ├── __init__.py
│   ├── pdf_parser.py       # PDF text extraction
│   ├── validators.py       # Schema validators
│   └── metrics.py          # Prometheus metrics
├── websocket/
│   ├── __init__.py
│   └── events.py           # WebSocket event handlers
└── storage/
    ├── __init__.py
    └── artifacts.py        # Artifact storage management
```

### 4.3 Key Service Implementations

#### PDF Service
```python
class PDFService:
    async def upload(self, file: UploadFile) -> PDFDocument:
        """Upload and parse PDF, extract TOC and headings"""
        
    async def extract_outline(self, pdf_id: str) -> Outline:
        """Extract hierarchical outline from PDF"""
        
    async def extract_section_text(self, pdf_id: str, section: Section) -> str:
        """Extract text for a specific section"""
```

#### Job Service
```python
class JobService:
    async def create_job(self, pdf_id: str, config: JobConfig) -> Job:
        """Create new mind map generation job"""
        
    async def update_plan(self, job_id: str, plan: WorkPlan) -> Job:
        """Human updates the work plan"""
        
    async def start_job(self, job_id: str) -> Job:
        """Lock plan and start processing"""
        
    async def get_status(self, job_id: str) -> JobStatus:
        """Get current job status with section progress"""
```

#### Crew Service
```python
class CrewService:
    def __init__(self):
        self.supervisor = self._create_supervisor()
        self.workers = self._create_workers()
        
    async def process_section(self, section: Section) -> MindMapSpec:
        """Process a single section through the agent pipeline"""
        
    async def validate_output(self, output: MindMapSpec) -> ValidationResult:
        """Validate generated mind map against schema"""
        
    async def repair_output(self, output: MindMapSpec, issues: List[str]) -> MindMapSpec:
        """Issue repair prompt for failed validation"""
```

---

## 5. React UI Design

### 5.1 Screen Flow

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  1. Upload &     |---->|  2. Live Run     |---->|  3. Results &    |
|     Outline      |     |     Monitor      |     |     Export       |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
  - PDF Upload            - Agent Status           - Mind Map Preview
  - TOC Display           - Section Progress       - Revision History
  - Section Selection     - Real-time Logs         - Download Options
  - Granularity Choice    - ETA Indicators         - Report Export
```

### 5.2 Component Architecture

```
src/
├── components/
│   ├── upload/
│   │   ├── PDFUploader.tsx
│   │   ├── OutlineTree.tsx
│   │   └── SectionSelector.tsx
│   ├── monitor/
│   │   ├── AgentStatusCard.tsx
│   │   ├── SectionProgressList.tsx
│   │   ├── LiveLogViewer.tsx
│   │   └── ETAIndicator.tsx
│   ├── results/
│   │   ├── MindMapViewer.tsx
│   │   ├── RevisionHistory.tsx
│   │   └── ExportOptions.tsx
│   ├── dashboard/
│   │   ├── MetricsOverview.tsx
│   │   ├── JobHistory.tsx
│   │   └── LogSearch.tsx
│   └── common/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── StatusBadge.tsx
├── hooks/
│   ├── useWebSocket.ts
│   ├── useJobStatus.ts
│   └── useMindMap.ts
├── services/
│   ├── api.ts
│   └── websocket.ts
├── store/
│   ├── jobStore.ts
│   └── uiStore.ts
└── types/
    └── index.ts
```

### 5.3 Key UI Components

#### Screen 1: Upload & Outline Selection
```
+---------------------------------------------------------------+
|  PDF Mind Map Generator                              [Settings]|
+---------------------------------------------------------------+
|                                                               |
|  +---------------------------+  +---------------------------+ |
|  |                           |  |  Document Outline         | |
|  |     Drop PDF Here         |  |                           | |
|  |        or                 |  |  [ ] Chapter 1            | |
|  |     [Browse Files]        |  |    [x] Section 1.1        | |
|  |                           |  |    [x] Section 1.2        | |
|  +---------------------------+  |  [ ] Chapter 2            | |
|                                 |    [ ] Section 2.1        | |
|  Granularity:                   |    [ ] Section 2.2        | |
|  ( ) Chapter Level              |                           | |
|  (x) Section Level              |  Supervisor Recommendation:| |
|  ( ) Custom Selection           |  "Section level for Ch1,  | |
|                                 |   Chapter level for Ch2"  | |
|  [Start Generation]             +---------------------------+ |
|                                                               |
+---------------------------------------------------------------+
```

#### Screen 2: Live Run Monitor
```
+---------------------------------------------------------------+
|  Job: abc123                    Status: Running    ETA: 5 min |
+---------------------------------------------------------------+
|                                                               |
|  Agent Status                                                 |
|  +------------------+  +------------------+  +---------------+|
|  | Supervisor       |  | Extractor        |  | Builder       ||
|  | [Active]         |  | [Processing]     |  | [Waiting]     ||
|  | Dispatching...   |  | Section 1.2      |  | Queue: 2      ||
|  +------------------+  +------------------+  +---------------+|
|                                                               |
|  Section Progress                                             |
|  +-----------------------------------------------------------+|
|  | Section 1.1  [============================] 100% Complete ||
|  | Section 1.2  [==============              ]  60% Extract  ||
|  | Section 2.1  [                            ]   0% Pending  ||
|  +-----------------------------------------------------------+|
|                                                               |
|  Live Logs                                        [Filter: v] |
|  +-----------------------------------------------------------+|
|  | 10:23:45 [Extractor] Processing section 1.2...            ||
|  | 10:23:44 [Supervisor] Dispatched section 1.2 to Extractor ||
|  | 10:23:40 [Builder] Completed mind map for section 1.1     ||
|  +-----------------------------------------------------------+|
|                                                               |
|  [Pause] [Retry Failed] [Cancel]                              |
+---------------------------------------------------------------+
```

#### Screen 3: Results & Export
```
+---------------------------------------------------------------+
|  Mind Map Results                              [Download All] |
+---------------------------------------------------------------+
|                                                               |
|  +-----------------------------------------------------------+|
|  |                                                           ||
|  |                    [Mind Map Visualization]               ||
|  |                                                           ||
|  |              +-- Concept A                                ||
|  |             /                                             ||
|  |    Main ---+--- Concept B                                 ||
|  |             \                                             ||
|  |              +-- Concept C                                ||
|  |                                                           ||
|  +-----------------------------------------------------------+|
|                                                               |
|  Revision History                                             |
|  +-----------------------------------------------------------+|
|  | v3 (current) - 10:30:00 - All sections complete           ||
|  | v2           - 10:25:00 - Section 1.2 repaired            ||
|  | v1           - 10:20:00 - Initial generation              ||
|  +-----------------------------------------------------------+|
|                                                               |
|  Export Options:                                              |
|  [PNG] [SVG] [JSON] [Mermaid] [Full Report ZIP]              |
|                                                               |
+---------------------------------------------------------------+
```

### 5.4 Real-Time Features

```typescript
// WebSocket connection for real-time updates
const useJobEvents = (jobId: string) => {
  const [events, setEvents] = useState<Event[]>([]);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/events/${jobId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
      
      // Update relevant state based on event type
      switch(data.type) {
        case 'SECTION_STARTED':
        case 'SECTION_COMPLETED':
        case 'AGENT_STATUS_CHANGED':
        case 'VALIDATION_FAILED':
        case 'JOB_COMPLETED':
          // Handle each event type
      }
    };
    
    return () => ws.close();
  }, [jobId]);
  
  return events;
};
```

---

## 6. Time-Series Database & Monitoring

### 6.1 Architecture

```
+------------------+     +------------------+     +------------------+
|   FastAPI        |     |   Loki           |     |   Grafana        |
|   Application    |---->|   (Log Store)    |---->|   Dashboard      |
+------------------+     +------------------+     +------------------+
        |                                                 ^
        |                +------------------+             |
        +--------------->|   Prometheus     |-------------+
                         |   (Metrics)      |
                         +------------------+
```

### 6.2 Structured Logging Schema

```python
# Log event structure
{
    "timestamp": "2024-01-15T10:23:45.123Z",
    "level": "INFO",
    "job_id": "job_abc123",
    "section_id": "section_001",
    "agent_id": "extractor_01",
    "agent_name": "Extractor",
    "event_type": "SECTION_PROCESSING",
    "message": "Processing section 1.2",
    "metadata": {
        "page_start": 15,
        "page_end": 22,
        "token_count": 1500
    },
    "correlation_id": "corr_xyz789"
}
```

### 6.3 Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
sections_processed_total = Counter(
    'mindmap_sections_processed_total',
    'Total sections processed',
    ['job_id', 'agent', 'status']
)

# Histograms
section_processing_duration = Histogram(
    'mindmap_section_processing_seconds',
    'Time to process a section',
    ['agent'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

# Gauges
active_jobs = Gauge(
    'mindmap_active_jobs',
    'Number of currently active jobs'
)

queue_depth = Gauge(
    'mindmap_queue_depth',
    'Number of sections waiting in queue',
    ['agent']
)
```

### 6.4 Loki Log Labels

```yaml
# Labels for efficient querying
labels:
  - job_id        # Filter by specific job
  - section_id    # Filter by section
  - agent_name    # Filter by agent (Supervisor/Extractor/Builder)
  - event_type    # Filter by event type
  - level         # Filter by log level (INFO/WARN/ERROR)
```

### 6.5 Docker Compose for Monitoring Stack

```yaml
version: '3.8'

services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml

  prometheus:
    image: prom/prometheus:v2.47.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - loki
      - prometheus

volumes:
  loki-data:
  prometheus-data:
  grafana-data:
```

---

## 7. Data Models & Schemas

### 7.1 Core Data Models

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class SectionStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    BUILDING = "building"
    VALIDATING = "validating"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"

# PDF Document
class PDFDocument(BaseModel):
    id: str
    filename: str
    upload_time: datetime
    page_count: int
    has_toc: bool
    file_path: str

# Outline Node
class OutlineNode(BaseModel):
    id: str
    title: str
    level: int  # 1=chapter, 2=section, 3=subsection
    page_start: int
    page_end: int
    children: List['OutlineNode'] = []
    selected: bool = False

# Section
class Section(BaseModel):
    id: str
    job_id: str
    title: str
    page_start: int
    page_end: int
    status: SectionStatus
    assigned_worker: Optional[str]
    extracted_content: Optional[str]
    mindmap_spec: Optional[Dict[str, Any]]
    retry_count: int = 0
    error_message: Optional[str]

# Work Plan
class WorkPlan(BaseModel):
    job_id: str
    sections: List[Section]
    granularity: str  # "chapter" or "section"
    human_approved: bool = False
    approved_at: Optional[datetime]

# Job
class Job(BaseModel):
    id: str
    pdf_id: str
    status: JobStatus
    work_plan: Optional[WorkPlan]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_sections: int
    completed_sections: int
    failed_sections: int

# Mind Map Spec (Canonical Format)
class MindMapNode(BaseModel):
    id: str
    label: str
    parent_id: Optional[str]
    level: int
    citations: List[str] = []  # Page references
    metadata: Dict[str, Any] = {}

class MindMapSpec(BaseModel):
    job_id: str
    section_id: str
    root_node: str
    nodes: List[MindMapNode]
    edges: List[Dict[str, str]]  # {source, target}
    version: int
    created_at: datetime
    validated: bool = False
```

### 7.2 Event Schema

```python
class EventType(str, Enum):
    # Job Events
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_PAUSED = "job_paused"
    JOB_RESUMED = "job_resumed"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    
    # Section Events
    SECTION_QUEUED = "section_queued"
    SECTION_STARTED = "section_started"
    SECTION_EXTRACTED = "section_extracted"
    SECTION_BUILT = "section_built"
    SECTION_VALIDATED = "section_validated"
    SECTION_FAILED = "section_failed"
    SECTION_RETRIED = "section_retried"
    
    # Agent Events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    
    # Validation Events
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    REPAIR_STARTED = "repair_started"
    REPAIR_COMPLETED = "repair_completed"

class Event(BaseModel):
    id: str
    timestamp: datetime
    event_type: EventType
    job_id: str
    section_id: Optional[str]
    agent_id: Optional[str]
    correlation_id: str
    message: str
    metadata: Dict[str, Any] = {}
```

---

## 8. Workflow & State Management

### 8.1 State Machine

```
                    +----------+
                    |  PENDING |
                    +----+-----+
                         |
                         v
                    +----+-----+
                    | PLANNING |
                    +----+-----+
                         |
                         v
              +---------+----------+
              | AWAITING_APPROVAL  |<----+
              +---------+----------+     |
                        |                |
            [Human Approves]             |
                        |                |
                        v                |
                   +----+----+           |
            +----->| RUNNING |           |
            |      +----+----+           |
            |           |                |
       [Resume]    +----+----+      [Modify Plan]
            |      |         |           |
            |      v         v           |
       +----+----+ |    +----+----+      |
       | PAUSED  |-+    | Section |------+
       +---------+      | Failed  |
                        +----+----+
                             |
                    [All Complete]
                             |
                             v
                      +------+-----+
                      | COMPLETED  |
                      +------------+
```

### 8.2 Event Sourcing Pattern

```python
class EventStore:
    """Append-only event store for audit trail and replay"""
    
    async def append(self, event: Event) -> None:
        """Append event to store and emit to subscribers"""
        # 1. Persist to Loki
        await self.loki_client.push(event)
        
        # 2. Update Prometheus metrics
        self.update_metrics(event)
        
        # 3. Emit to WebSocket subscribers
        await self.websocket_manager.broadcast(event)
    
    async def get_events(
        self,
        job_id: str,
        event_types: List[EventType] = None,
        since: datetime = None
    ) -> List[Event]:
        """Query events with filters"""
        
    async def replay(self, job_id: str) -> JobState:
        """Replay events to reconstruct job state"""
```

### 8.3 Human-in-the-Loop Flow

```
1. PDF Upload
   └── Backend extracts TOC/headings
   
2. Outline Presentation
   └── UI displays selectable outline tree
   
3. Supervisor Recommendation
   └── Supervisor agent analyzes structure
   └── Recommends chapter vs section granularity
   
4. Human Decision
   └── User selects/modifies boundaries
   └── User chooses granularity per section
   └── User clicks "Approve Plan"
   
5. Plan Lock
   └── Work plan is immutable
   └── New job_id for any modifications
   
6. Execution
   └── Supervisor dispatches to workers
   └── Progress visible in real-time
   
7. Review Checkpoints
   └── Failed validations surface for human review
   └── User can retry, reassign, or skip sections
```

---

## 9. Error Handling & Resilience

### 9.1 Retry Strategy

```python
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

async def with_retry(
    func: Callable,
    config: RetryConfig = RetryConfig()
) -> Any:
    """Execute function with exponential backoff retry"""
    for attempt in range(config.max_retries):
        try:
            return await func()
        except (OllamaError, TimeoutError) as e:
            if attempt == config.max_retries - 1:
                raise
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            await asyncio.sleep(delay)
```

### 9.2 Validation & Repair Loop

```python
async def process_with_validation(
    section: Section,
    max_repair_attempts: int = 2
) -> MindMapSpec:
    """Process section with validation and repair loop"""
    
    # Extract content
    extracted = await extractor.process(section)
    
    # Build mind map
    mindmap = await builder.process(extracted)
    
    # Validate
    for attempt in range(max_repair_attempts):
        validation = await validator.validate(mindmap)
        
        if validation.passed:
            return mindmap
        
        # Attempt repair
        mindmap = await supervisor.repair(
            mindmap,
            issues=validation.issues
        )
    
    # Mark for human review if still failing
    raise NeedsHumanReviewError(
        section_id=section.id,
        issues=validation.issues,
        last_output=mindmap
    )
```

### 9.3 Checkpointing & Recovery

```python
class ArtifactStore:
    """Persist artifacts for recovery and debugging"""
    
    base_path: Path = Path("./artifacts")
    
    async def save_artifact(
        self,
        job_id: str,
        section_id: str,
        artifact_type: str,
        content: Any
    ) -> str:
        """Save artifact to disk"""
        path = self.base_path / job_id / section_id / f"{artifact_type}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(content, f)
        
        return str(path)
    
    async def load_artifact(
        self,
        job_id: str,
        section_id: str,
        artifact_type: str
    ) -> Optional[Any]:
        """Load artifact from disk"""
        path = self.base_path / job_id / section_id / f"{artifact_type}.json"
        
        if not path.exists():
            return None
        
        with open(path, 'r') as f:
            return json.load(f)
    
    async def resume_job(self, job_id: str) -> Job:
        """Resume job from checkpointed state"""
        # Load all artifacts and reconstruct state
        # Skip already completed sections
```

---

## 10. Improvements & Best Practices

### 10.1 Architecture Improvements

1. **Canonical Intermediate Format (MindMapSpec)**
   - Define a strict JSON schema for mind map data
   - All agents produce/consume this format
   - Enables validation, debugging, and format conversion

2. **Event Sourcing**
   - Every state transition is an immutable event
   - Full audit trail and replay capability
   - Real-time UI updates via event stream

3. **Separation of Concerns**
   - Planning (Supervisor) separate from Execution (Workers)
   - Validation as a distinct phase
   - Human decisions explicit and persisted

### 10.2 Quality Improvements

1. **Deterministic Extraction First**
   - Extract text by page before LLM processing
   - Constrain workers to section-sized chunks
   - Require citations (page numbers) for nodes

2. **Validation Gates**
   - Schema validation (structure correctness)
   - Coverage validation (minimum nodes per section)
   - Citation validation (references exist)
   - Depth validation (balanced hierarchy)

3. **Targeted Repair**
   - Specific repair prompts vs generic "make it better"
   - "Add missing concepts X, Y" instead of regeneration
   - Preserve working parts, fix specific issues

### 10.3 Performance Improvements

1. **Parallel Processing**
   - Multiple sections processed concurrently
   - Worker pool with configurable size
   - Queue-based work distribution

2. **Caching**
   - Cache extracted text per section
   - Cache intermediate results
   - Resume from checkpoints

3. **Streaming**
   - Stream LLM responses for progress indication
   - WebSocket for real-time updates
   - Avoid polling

### 10.4 UX Improvements

1. **Progressive Disclosure**
   - Show outline immediately after upload
   - Display supervisor recommendation
   - Allow granular control when needed

2. **Real-Time Feedback**
   - Live log streaming
   - Per-section progress bars
   - ETA estimation

3. **Error Recovery**
   - Clear error messages
   - One-click retry
   - Manual intervention options

### 10.5 Observability Improvements

1. **Correlation IDs**
   - Track requests end-to-end
   - Link logs across services
   - Debug complex flows

2. **Structured Logging**
   - Consistent log format
   - Searchable labels
   - Machine-parseable

3. **Metrics**
   - Latency percentiles
   - Success/failure rates
   - Queue depths
   - Token usage

---

## 11. Deployment Architecture

### 11.1 Local Development Setup

```
docker-compose.yml
├── ollama (LLM server)
├── loki (log aggregation)
├── prometheus (metrics)
├── grafana (dashboards)
└── app (FastAPI + React)
```

### 11.2 Directory Structure

```
pdf-mindmap-system/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── utils/
│   │   └── websocket/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── monitoring/
│   ├── prometheus.yml
│   ├── loki-config.yml
│   └── grafana/
│       └── provisioning/
│           ├── dashboards/
│           └── datasources/
├── docker-compose.yml
└── README.md
```

### 11.3 Docker Compose (Complete)

```yaml
version: '3.8'

services:
  # Ollama LLM Server
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # FastAPI Backend
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - LOKI_HOST=http://loki:3100
      - PROMETHEUS_HOST=http://prometheus:9090
    volumes:
      - ./artifacts:/app/artifacts
    depends_on:
      - ollama
      - loki
      - prometheus

  # React Frontend
  frontend:
    build: ./frontend
    ports:
      - "3001:80"
    depends_on:
      - backend

  # Loki (Logs)
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - ./monitoring/loki-config.yml:/etc/loki/local-config.yaml
      - loki-data:/loki

  # Prometheus (Metrics)
  prometheus:
    image: prom/prometheus:v2.47.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  # Grafana (Dashboard)
  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - loki
      - prometheus

volumes:
  ollama-data:
  loki-data:
  prometheus-data:
  grafana-data:
```

---

## 12. Future Enhancements

### 12.1 Short-Term

1. **OCR Support** - Handle scanned PDFs
2. **Multiple Output Formats** - Mermaid, Markmap, XMind
3. **Batch Processing** - Multiple PDFs in queue
4. **Template Library** - Pre-defined mind map styles

### 12.2 Medium-Term

1. **Collaborative Editing** - Multiple users on same job
2. **Version Control** - Git-like branching for mind maps
3. **API Access** - Programmatic mind map generation
4. **Custom Agents** - User-defined agent behaviors

### 12.3 Long-Term

1. **Distributed Processing** - Scale across machines
2. **Fine-tuned Models** - Domain-specific LLMs
3. **Knowledge Graph** - Cross-document linking
4. **Interactive Mind Maps** - Drill-down, expand/collapse

---

## Appendix A: API Reference

See separate API documentation for detailed endpoint specifications.

## Appendix B: Grafana Dashboard JSON

Pre-configured dashboards available in `/monitoring/grafana/provisioning/dashboards/`

## Appendix C: Sample MindMapSpec

```json
{
  "job_id": "job_abc123",
  "section_id": "section_001",
  "root_node": "node_001",
  "nodes": [
    {
      "id": "node_001",
      "label": "Machine Learning Fundamentals",
      "parent_id": null,
      "level": 0,
      "citations": ["p.15"],
      "metadata": {}
    },
    {
      "id": "node_002",
      "label": "Supervised Learning",
      "parent_id": "node_001",
      "level": 1,
      "citations": ["p.16-17"],
      "metadata": {}
    }
  ],
  "edges": [
    {"source": "node_001", "target": "node_002"}
  ],
  "version": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "validated": true
}
```

---

*Document Version: 1.0*
*Last Updated: 2024-01-15*
