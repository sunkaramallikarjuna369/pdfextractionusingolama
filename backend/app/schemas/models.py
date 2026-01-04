from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())[:8]


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
    NEEDS_REVIEW = "needs_review"


class AgentStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"


class EventType(str, Enum):
    # Job Events
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_PAUSED = "job_paused"
    JOB_RESUMED = "job_resumed"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    PLAN_APPROVED = "plan_approved"
    
    # Section Events
    SECTION_QUEUED = "section_queued"
    SECTION_STARTED = "section_started"
    SECTION_EXTRACTED = "section_extracted"
    SECTION_BUILT = "section_built"
    SECTION_VALIDATED = "section_validated"
    SECTION_COMPLETED = "section_completed"
    SECTION_FAILED = "section_failed"
    SECTION_RETRIED = "section_retried"
    
    # Agent Events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    
    # Validation Events
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    REPAIR_STARTED = "repair_started"
    REPAIR_COMPLETED = "repair_completed"
    
    # Log Events
    LOG_MESSAGE = "log_message"


class PDFDocument(BaseModel):
    id: str = Field(default_factory=generate_id)
    filename: str
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    page_count: int = 0
    has_toc: bool = False
    file_path: str = ""


class OutlineNode(BaseModel):
    id: str = Field(default_factory=generate_id)
    title: str
    level: int  # 1=chapter, 2=section, 3=subsection
    page_start: int
    page_end: int
    children: List["OutlineNode"] = []
    selected: bool = False
    text_content: Optional[str] = None


class Section(BaseModel):
    id: str = Field(default_factory=generate_id)
    job_id: str
    title: str
    level: int = 1
    page_start: int
    page_end: int
    status: SectionStatus = SectionStatus.PENDING
    assigned_worker: Optional[str] = None
    extracted_content: Optional[str] = None
    mindmap_spec: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkPlan(BaseModel):
    job_id: str
    sections: List[Section] = []
    granularity: str = "section"  # "chapter" or "section"
    human_approved: bool = False
    approved_at: Optional[datetime] = None
    supervisor_recommendation: Optional[str] = None


class Job(BaseModel):
    id: str = Field(default_factory=generate_id)
    pdf_id: str
    pdf_filename: str = ""
    status: JobStatus = JobStatus.PENDING
    work_plan: Optional[WorkPlan] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_sections: int = 0
    completed_sections: int = 0
    failed_sections: int = 0
    current_section: Optional[str] = None


class MindMapNode(BaseModel):
    id: str = Field(default_factory=generate_id)
    label: str
    parent_id: Optional[str] = None
    level: int = 0
    citations: List[str] = []  # Page references
    metadata: Dict[str, Any] = {}


class MindMapSpec(BaseModel):
    job_id: str
    section_id: str
    section_title: str = ""
    root_node: str
    nodes: List[MindMapNode] = []
    edges: List[Dict[str, str]] = []  # {source, target}
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated: bool = False


class Event(BaseModel):
    id: str = Field(default_factory=generate_id)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType
    job_id: str
    section_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    correlation_id: str = Field(default_factory=generate_id)
    message: str
    level: str = "INFO"
    metadata: Dict[str, Any] = {}


class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    current_section: Optional[str] = None
    tasks_completed: int = 0
    last_activity: Optional[datetime] = None


class ValidationResult(BaseModel):
    passed: bool
    issues: List[str] = []
    warnings: List[str] = []
    node_count: int = 0
    max_depth: int = 0
    has_citations: bool = False


# Enable forward references
OutlineNode.model_rebuild()
