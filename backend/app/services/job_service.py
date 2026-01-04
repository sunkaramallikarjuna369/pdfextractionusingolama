import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..schemas.models import (
    Job,
    JobStatus,
    Section,
    SectionStatus,
    WorkPlan,
    OutlineNode,
    MindMapSpec,
    AgentInfo,
    AgentStatus,
    EventType,
    generate_id,
)
from ..config import get_settings
from .event_service import event_service
from .pdf_service import pdf_service


class JobService:
    def __init__(self):
        self.settings = get_settings()
        self.jobs: Dict[str, Job] = {}
        self.sections: Dict[str, Section] = {}
        self.mindmaps: Dict[str, MindMapSpec] = {}
        self.agents: Dict[str, AgentInfo] = {}
        self._init_agents()
    
    def _init_agents(self):
        self.agents = {
            "supervisor": AgentInfo(
                id="supervisor",
                name="Supervisor",
                role="PDF Mind Map Orchestrator",
                status=AgentStatus.IDLE,
            ),
            "extractor": AgentInfo(
                id="extractor",
                name="Extractor",
                role="Content Extractor & Summarizer",
                status=AgentStatus.IDLE,
            ),
            "builder": AgentInfo(
                id="builder",
                name="Builder",
                role="Mind Map Architect",
                status=AgentStatus.IDLE,
            ),
        }
    
    async def create_job(
        self,
        pdf_id: str,
        granularity: str = "section",
        selected_sections: Optional[List[str]] = None,
    ) -> Job:
        doc = pdf_service.get_document(pdf_id)
        if not doc:
            raise ValueError(f"PDF document {pdf_id} not found")
        
        outline = await pdf_service.extract_outline(pdf_id)
        
        job_id = generate_id()
        job = Job(
            id=job_id,
            pdf_id=pdf_id,
            pdf_filename=doc.filename,
            status=JobStatus.PLANNING,
            created_at=datetime.utcnow(),
        )
        
        sections = self._create_sections_from_outline(
            job_id, pdf_id, outline, granularity, selected_sections
        )
        
        recommendation = pdf_service.get_supervisor_recommendation(
            outline, doc.page_count
        )
        
        work_plan = WorkPlan(
            job_id=job_id,
            sections=sections,
            granularity=granularity,
            human_approved=False,
            supervisor_recommendation=recommendation,
        )
        
        job.work_plan = work_plan
        job.total_sections = len(sections)
        job.status = JobStatus.AWAITING_APPROVAL
        
        self.jobs[job_id] = job
        for section in sections:
            self.sections[section.id] = section
        
        await event_service.emit(
            EventType.JOB_CREATED,
            job_id=job_id,
            message=f"Job created with {len(sections)} sections",
            metadata={"pdf_id": pdf_id, "granularity": granularity},
        )
        
        return job
    
    def _create_sections_from_outline(
        self,
        job_id: str,
        pdf_id: str,
        outline: List[OutlineNode],
        granularity: str,
        selected_sections: Optional[List[str]] = None,
    ) -> List[Section]:
        sections = []
        
        def process_node(node: OutlineNode, include_children: bool = True):
            if selected_sections and node.id not in selected_sections:
                if include_children:
                    for child in node.children:
                        process_node(child, include_children)
                return
            
            if granularity == "chapter" and node.level == 1:
                section = Section(
                    id=generate_id(),
                    job_id=job_id,
                    title=node.title,
                    level=node.level,
                    page_start=node.page_start,
                    page_end=node.page_end,
                    status=SectionStatus.PENDING,
                )
                sections.append(section)
            elif granularity == "section":
                if node.children:
                    for child in node.children:
                        process_node(child, include_children=False)
                else:
                    section = Section(
                        id=generate_id(),
                        job_id=job_id,
                        title=node.title,
                        level=node.level,
                        page_start=node.page_start,
                        page_end=node.page_end,
                        status=SectionStatus.PENDING,
                    )
                    sections.append(section)
            else:
                section = Section(
                    id=generate_id(),
                    job_id=job_id,
                    title=node.title,
                    level=node.level,
                    page_start=node.page_start,
                    page_end=node.page_end,
                    status=SectionStatus.PENDING,
                )
                sections.append(section)
        
        for node in outline:
            process_node(node)
        
        if not sections:
            for node in outline:
                section = Section(
                    id=generate_id(),
                    job_id=job_id,
                    title=node.title,
                    level=node.level,
                    page_start=node.page_start,
                    page_end=node.page_end,
                    status=SectionStatus.PENDING,
                )
                sections.append(section)
        
        return sections
    
    async def update_plan(
        self,
        job_id: str,
        sections_data: List[Dict[str, Any]],
        granularity: str,
        approved: bool,
    ) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status not in [JobStatus.AWAITING_APPROVAL, JobStatus.PLANNING]:
            raise ValueError(f"Job {job_id} is not awaiting approval")
        
        updated_sections = []
        for section_data in sections_data:
            section_id = section_data.get("id")
            if section_id and section_id in self.sections:
                section = self.sections[section_id]
                section.title = section_data.get("title", section.title)
                section.page_start = section_data.get("page_start", section.page_start)
                section.page_end = section_data.get("page_end", section.page_end)
                updated_sections.append(section)
            else:
                new_section = Section(
                    id=generate_id(),
                    job_id=job_id,
                    title=section_data.get("title", "Untitled"),
                    level=section_data.get("level", 1),
                    page_start=section_data.get("page_start", 1),
                    page_end=section_data.get("page_end", 1),
                    status=SectionStatus.PENDING,
                )
                self.sections[new_section.id] = new_section
                updated_sections.append(new_section)
        
        job.work_plan.sections = updated_sections
        job.work_plan.granularity = granularity
        job.work_plan.human_approved = approved
        job.total_sections = len(updated_sections)
        
        if approved:
            job.work_plan.approved_at = datetime.utcnow()
            job.status = JobStatus.PENDING
            
            await event_service.emit(
                EventType.PLAN_APPROVED,
                job_id=job_id,
                message=f"Work plan approved with {len(updated_sections)} sections",
            )
        
        return job
    
    async def start_job(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if not job.work_plan or not job.work_plan.human_approved:
            raise ValueError(f"Job {job_id} work plan not approved")
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        await event_service.emit(
            EventType.JOB_STARTED,
            job_id=job_id,
            message="Job started processing",
        )
        
        return job
    
    async def pause_job(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != JobStatus.RUNNING:
            raise ValueError(f"Job {job_id} is not running")
        
        job.status = JobStatus.PAUSED
        
        await event_service.emit(
            EventType.JOB_PAUSED,
            job_id=job_id,
            message="Job paused",
        )
        
        return job
    
    async def resume_job(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != JobStatus.PAUSED:
            raise ValueError(f"Job {job_id} is not paused")
        
        job.status = JobStatus.RUNNING
        
        await event_service.emit(
            EventType.JOB_RESUMED,
            job_id=job_id,
            message="Job resumed",
        )
        
        return job
    
    async def complete_job(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        
        await event_service.emit(
            EventType.JOB_COMPLETED,
            job_id=job_id,
            message="Job completed successfully",
        )
        
        return job
    
    async def fail_job(self, job_id: str, error: str) -> Job:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = JobStatus.FAILED
        job.completed_at = datetime.utcnow()
        
        await event_service.emit(
            EventType.JOB_FAILED,
            job_id=job_id,
            message=f"Job failed: {error}",
            level="ERROR",
        )
        
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)
    
    def get_job_sections(self, job_id: str) -> List[Section]:
        return [s for s in self.sections.values() if s.job_id == job_id]
    
    def get_section(self, section_id: str) -> Optional[Section]:
        return self.sections.get(section_id)
    
    async def update_section_status(
        self,
        section_id: str,
        status: SectionStatus,
        error_message: Optional[str] = None,
    ) -> Section:
        section = self.sections.get(section_id)
        if not section:
            raise ValueError(f"Section {section_id} not found")
        
        section.status = status
        if error_message:
            section.error_message = error_message
        
        if status == SectionStatus.COMPLETED:
            section.completed_at = datetime.utcnow()
            job = self.jobs.get(section.job_id)
            if job:
                job.completed_sections += 1
        elif status == SectionStatus.FAILED:
            job = self.jobs.get(section.job_id)
            if job:
                job.failed_sections += 1
        
        return section
    
    async def save_mindmap(
        self, section_id: str, mindmap: MindMapSpec
    ) -> MindMapSpec:
        self.mindmaps[section_id] = mindmap
        
        section = self.sections.get(section_id)
        if section:
            section.mindmap_spec = mindmap.model_dump()
        
        artifacts_dir = os.path.join(
            self.settings.artifacts_path,
            mindmap.job_id,
            section_id,
        )
        os.makedirs(artifacts_dir, exist_ok=True)
        
        with open(os.path.join(artifacts_dir, "mindmap.json"), "w") as f:
            json.dump(mindmap.model_dump(), f, default=str, indent=2)
        
        return mindmap
    
    def get_mindmap(self, section_id: str) -> Optional[MindMapSpec]:
        return self.mindmaps.get(section_id)
    
    def get_job_mindmaps(self, job_id: str) -> Dict[str, MindMapSpec]:
        return {
            section_id: mindmap
            for section_id, mindmap in self.mindmaps.items()
            if mindmap.job_id == job_id
        }
    
    def get_agents(self) -> List[AgentInfo]:
        return list(self.agents.values())
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        current_task: Optional[str] = None,
        current_section: Optional[str] = None,
    ):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = status
            agent.current_task = current_task
            agent.current_section = current_section
            agent.last_activity = datetime.utcnow()
            
            if status == AgentStatus.IDLE and current_task is None:
                agent.tasks_completed += 1


job_service = JobService()
