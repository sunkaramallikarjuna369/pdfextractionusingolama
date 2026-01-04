from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import (
    PDFDocument,
    OutlineNode,
    Section,
    Job,
    JobStatus,
    MindMapSpec,
    AgentInfo,
    Event,
)


class UploadResponse(BaseModel):
    success: bool
    pdf_id: str
    filename: str
    page_count: int
    has_toc: bool
    message: str = ""


class OutlineResponse(BaseModel):
    pdf_id: str
    filename: str
    outline: List[OutlineNode]
    total_pages: int
    supervisor_recommendation: Optional[str] = None


class JobCreateRequest(BaseModel):
    pdf_id: str
    granularity: str = "section"  # "chapter" or "section"
    selected_sections: Optional[List[str]] = None  # IDs of selected outline nodes


class PlanUpdateRequest(BaseModel):
    sections: List[Dict[str, Any]]  # Section updates from human
    granularity: str = "section"
    approved: bool = False


class SectionUpdateRequest(BaseModel):
    reassign_to: Optional[str] = None  # Worker ID to reassign to


class JobResponse(BaseModel):
    job: Job
    sections: List[Section] = []
    agents: List[AgentInfo] = []


class SectionResponse(BaseModel):
    section: Section
    mindmap: Optional[MindMapSpec] = None


class MindMapResponse(BaseModel):
    job_id: str
    sections: List[Dict[str, Any]]  # Section ID -> MindMapSpec
    combined_mindmap: Optional[MindMapSpec] = None
    format: str = "json"


class AgentStatusResponse(BaseModel):
    agents: List[AgentInfo]


class LogQueryRequest(BaseModel):
    job_id: Optional[str] = None
    section_id: Optional[str] = None
    agent_name: Optional[str] = None
    event_type: Optional[str] = None
    level: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class LogResponse(BaseModel):
    events: List[Event]
    total: int
    has_more: bool


class ExportRequest(BaseModel):
    job_id: str
    format: str = "json"  # "json", "png", "svg", "mermaid", "zip"
    include_logs: bool = False


class ExportResponse(BaseModel):
    success: bool
    download_url: Optional[str] = None
    content: Optional[str] = None
    format: str
