import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ..schemas.models import (
    Section,
    SectionStatus,
    MindMapSpec,
    MindMapNode,
    AgentStatus,
    EventType,
    ValidationResult,
    generate_id,
)
from ..config import get_settings
from .event_service import event_service
from .job_service import job_service
from .pdf_service import pdf_service
from ..agents.crew_runner import CrewRunner


class RunnerService:
    def __init__(self):
        self.settings = get_settings()
        self.crew_runner = CrewRunner()
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def start_processing(self, job_id: str):
        async with self._lock:
            if job_id in self.running_jobs:
                return
            
            task = asyncio.create_task(self._process_job(job_id))
            self.running_jobs[job_id] = task
    
    async def stop_processing(self, job_id: str):
        async with self._lock:
            if job_id in self.running_jobs:
                self.running_jobs[job_id].cancel()
                del self.running_jobs[job_id]
    
    async def _process_job(self, job_id: str):
        job = job_service.get_job(job_id)
        if not job or not job.work_plan:
            return
        
        try:
            await job_service.update_agent_status(
                "supervisor", AgentStatus.PROCESSING, "Coordinating job", None
            )
            
            sections = job.work_plan.sections
            
            for section in sections:
                if job.status.value == "paused":
                    await event_service.emit(
                        EventType.LOG_MESSAGE,
                        job_id=job_id,
                        message="Job paused, waiting...",
                        level="INFO",
                    )
                    while job.status.value == "paused":
                        await asyncio.sleep(1)
                        job = job_service.get_job(job_id)
                        if not job:
                            return
                
                if job.status.value not in ["running"]:
                    break
                
                await self._process_section(job_id, section)
            
            all_completed = all(
                s.status == SectionStatus.COMPLETED
                for s in job_service.get_job_sections(job_id)
            )
            
            if all_completed:
                await job_service.complete_job(job_id)
            else:
                failed_count = sum(
                    1 for s in job_service.get_job_sections(job_id)
                    if s.status == SectionStatus.FAILED
                )
                if failed_count > 0:
                    await event_service.emit(
                        EventType.LOG_MESSAGE,
                        job_id=job_id,
                        message=f"Job completed with {failed_count} failed sections",
                        level="WARNING",
                    )
            
            await job_service.update_agent_status(
                "supervisor", AgentStatus.IDLE, None, None
            )
            
        except asyncio.CancelledError:
            await event_service.emit(
                EventType.LOG_MESSAGE,
                job_id=job_id,
                message="Job processing cancelled",
                level="WARNING",
            )
        except Exception as e:
            await job_service.fail_job(job_id, str(e))
            await job_service.update_agent_status(
                "supervisor", AgentStatus.ERROR, str(e), None
            )
        finally:
            async with self._lock:
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]
    
    async def _process_section(self, job_id: str, section: Section):
        job = job_service.get_job(job_id)
        if not job:
            return
        
        await event_service.emit(
            EventType.SECTION_STARTED,
            job_id=job_id,
            section_id=section.id,
            message=f"Started processing section: {section.title}",
            agent_name="Supervisor",
        )
        
        section.started_at = datetime.utcnow()
        await job_service.update_section_status(section.id, SectionStatus.EXTRACTING)
        
        try:
            await job_service.update_agent_status(
                "extractor", AgentStatus.PROCESSING, "Extracting content", section.id
            )
            
            await event_service.emit(
                EventType.AGENT_STARTED,
                job_id=job_id,
                section_id=section.id,
                agent_id="extractor",
                agent_name="Extractor",
                message=f"Extracting content from pages {section.page_start}-{section.page_end}",
            )
            
            text_content = await pdf_service.extract_section_text(
                job.pdf_id, section.page_start, section.page_end
            )
            
            extracted_content = await self.crew_runner.extract_content(
                section.title, text_content, section.page_start, section.page_end
            )
            
            section.extracted_content = extracted_content
            
            await event_service.emit(
                EventType.SECTION_EXTRACTED,
                job_id=job_id,
                section_id=section.id,
                agent_id="extractor",
                agent_name="Extractor",
                message="Content extraction completed",
            )
            
            await job_service.update_agent_status(
                "extractor", AgentStatus.IDLE, None, None
            )
            
            await job_service.update_section_status(section.id, SectionStatus.BUILDING)
            await job_service.update_agent_status(
                "builder", AgentStatus.PROCESSING, "Building mind map", section.id
            )
            
            await event_service.emit(
                EventType.AGENT_STARTED,
                job_id=job_id,
                section_id=section.id,
                agent_id="builder",
                agent_name="Builder",
                message="Building mind map structure",
            )
            
            mindmap = await self.crew_runner.build_mindmap(
                job_id, section.id, section.title, extracted_content
            )
            
            await event_service.emit(
                EventType.SECTION_BUILT,
                job_id=job_id,
                section_id=section.id,
                agent_id="builder",
                agent_name="Builder",
                message=f"Mind map built with {len(mindmap.nodes)} nodes",
            )
            
            await job_service.update_agent_status(
                "builder", AgentStatus.IDLE, None, None
            )
            
            await job_service.update_section_status(section.id, SectionStatus.VALIDATING)
            
            validation = await self._validate_mindmap(mindmap)
            
            if not validation.passed:
                await event_service.emit(
                    EventType.VALIDATION_FAILED,
                    job_id=job_id,
                    section_id=section.id,
                    message=f"Validation failed: {', '.join(validation.issues)}",
                    level="WARNING",
                )
                
                for attempt in range(self.settings.max_repair_attempts):
                    await job_service.update_section_status(
                        section.id, SectionStatus.REPAIRING
                    )
                    
                    await event_service.emit(
                        EventType.REPAIR_STARTED,
                        job_id=job_id,
                        section_id=section.id,
                        message=f"Repair attempt {attempt + 1}",
                    )
                    
                    mindmap = await self.crew_runner.repair_mindmap(
                        mindmap, validation.issues
                    )
                    
                    validation = await self._validate_mindmap(mindmap)
                    
                    if validation.passed:
                        await event_service.emit(
                            EventType.REPAIR_COMPLETED,
                            job_id=job_id,
                            section_id=section.id,
                            message="Repair successful",
                        )
                        break
                
                if not validation.passed:
                    await job_service.update_section_status(
                        section.id,
                        SectionStatus.NEEDS_REVIEW,
                        f"Validation failed after repairs: {', '.join(validation.issues)}",
                    )
                    return
            
            await event_service.emit(
                EventType.VALIDATION_PASSED,
                job_id=job_id,
                section_id=section.id,
                message="Mind map validation passed",
            )
            
            await job_service.save_mindmap(section.id, mindmap)
            await job_service.update_section_status(section.id, SectionStatus.COMPLETED)
            
            await event_service.emit(
                EventType.SECTION_COMPLETED,
                job_id=job_id,
                section_id=section.id,
                message=f"Section completed: {section.title}",
                metadata={
                    "node_count": len(mindmap.nodes),
                    "max_depth": validation.max_depth,
                },
            )
            
        except Exception as e:
            await job_service.update_section_status(
                section.id, SectionStatus.FAILED, str(e)
            )
            
            await event_service.emit(
                EventType.SECTION_FAILED,
                job_id=job_id,
                section_id=section.id,
                message=f"Section failed: {str(e)}",
                level="ERROR",
            )
            
            section.retry_count += 1
            
            await job_service.update_agent_status(
                "extractor", AgentStatus.IDLE, None, None
            )
            await job_service.update_agent_status(
                "builder", AgentStatus.IDLE, None, None
            )
    
    async def _validate_mindmap(self, mindmap: MindMapSpec) -> ValidationResult:
        issues = []
        warnings = []
        
        if not mindmap.nodes:
            issues.append("Mind map has no nodes")
        
        if len(mindmap.nodes) < 3:
            issues.append("Mind map has fewer than 3 nodes")
        
        root_nodes = [n for n in mindmap.nodes if n.parent_id is None]
        if len(root_nodes) != 1:
            issues.append(f"Expected 1 root node, found {len(root_nodes)}")
        
        node_ids = {n.id for n in mindmap.nodes}
        for node in mindmap.nodes:
            if node.parent_id and node.parent_id not in node_ids:
                issues.append(f"Node {node.id} references non-existent parent {node.parent_id}")
        
        max_depth = 0
        for node in mindmap.nodes:
            depth = self._calculate_depth(node, mindmap.nodes)
            max_depth = max(max_depth, depth)
        
        if max_depth > 6:
            warnings.append(f"Mind map depth ({max_depth}) exceeds recommended maximum of 6")
        
        has_citations = any(n.citations for n in mindmap.nodes)
        if not has_citations:
            warnings.append("Mind map has no page citations")
        
        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            node_count=len(mindmap.nodes),
            max_depth=max_depth,
            has_citations=has_citations,
        )
    
    def _calculate_depth(self, node: MindMapNode, all_nodes: list) -> int:
        depth = 0
        current = node
        visited = set()
        
        while current.parent_id and current.parent_id not in visited:
            visited.add(current.id)
            parent = next((n for n in all_nodes if n.id == current.parent_id), None)
            if parent:
                depth += 1
                current = parent
            else:
                break
        
        return depth
    
    async def retry_section(self, section_id: str) -> Section:
        section = job_service.get_section(section_id)
        if not section:
            raise ValueError(f"Section {section_id} not found")
        
        section.status = SectionStatus.PENDING
        section.error_message = None
        section.retry_count += 1
        
        await event_service.emit(
            EventType.SECTION_RETRIED,
            job_id=section.job_id,
            section_id=section_id,
            message=f"Section queued for retry (attempt {section.retry_count})",
        )
        
        asyncio.create_task(self._process_section(section.job_id, section))
        
        return section


runner_service = RunnerService()
