import asyncio
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..schemas import (
    UploadResponse,
    OutlineResponse,
    JobCreateRequest,
    PlanUpdateRequest,
    JobResponse,
    SectionResponse,
    MindMapResponse,
)
from ..schemas.requests import (
    LogQueryRequest,
    LogResponse,
    AgentStatusResponse,
    ExportRequest,
    ExportResponse,
)
from ..schemas.models import JobStatus, SectionStatus
from ..services.pdf_service import pdf_service
from ..services.job_service import job_service
from ..services.event_service import event_service
from ..services.runner_service import runner_service

router = APIRouter()


@router.post("/pdf/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    try:
        doc = await pdf_service.upload_pdf(file.filename, content)
        return UploadResponse(
            success=True,
            pdf_id=doc.id,
            filename=doc.filename,
            page_count=doc.page_count,
            has_toc=doc.has_toc,
            message="PDF uploaded successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf/{pdf_id}/outline", response_model=OutlineResponse)
async def get_outline(pdf_id: str):
    doc = pdf_service.get_document(pdf_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    try:
        outline = await pdf_service.extract_outline(pdf_id)
        recommendation = pdf_service.get_supervisor_recommendation(outline, doc.page_count)
        
        return OutlineResponse(
            pdf_id=pdf_id,
            filename=doc.filename,
            outline=outline,
            total_pages=doc.page_count,
            supervisor_recommendation=recommendation,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/create", response_model=JobResponse)
async def create_job(request: JobCreateRequest):
    try:
        job = await job_service.create_job(
            pdf_id=request.pdf_id,
            granularity=request.granularity,
            selected_sections=request.selected_sections,
        )
        sections = job_service.get_job_sections(job.id)
        agents = job_service.get_agents()
        
        return JobResponse(job=job, sections=sections, agents=agents)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    sections = job_service.get_job_sections(job_id)
    agents = job_service.get_agents()
    
    return JobResponse(job=job, sections=sections, agents=agents)


@router.put("/jobs/{job_id}/plan", response_model=JobResponse)
async def update_plan(job_id: str, request: PlanUpdateRequest):
    try:
        job = await job_service.update_plan(
            job_id=job_id,
            sections_data=request.sections,
            granularity=request.granularity,
            approved=request.approved,
        )
        sections = job_service.get_job_sections(job_id)
        agents = job_service.get_agents()
        
        return JobResponse(job=job, sections=sections, agents=agents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/start", response_model=JobResponse)
async def start_job(job_id: str):
    try:
        job = await job_service.start_job(job_id)
        
        asyncio.create_task(runner_service.start_processing(job_id))
        
        sections = job_service.get_job_sections(job_id)
        agents = job_service.get_agents()
        
        return JobResponse(job=job, sections=sections, agents=agents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/pause", response_model=JobResponse)
async def pause_job(job_id: str):
    try:
        job = await job_service.pause_job(job_id)
        sections = job_service.get_job_sections(job_id)
        agents = job_service.get_agents()
        
        return JobResponse(job=job, sections=sections, agents=agents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/resume", response_model=JobResponse)
async def resume_job(job_id: str):
    try:
        job = await job_service.resume_job(job_id)
        sections = job_service.get_job_sections(job_id)
        agents = job_service.get_agents()
        
        return JobResponse(job=job, sections=sections, agents=agents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await runner_service.stop_processing(job_id)
    await job_service.fail_job(job_id, "Cancelled by user")
    
    return {"success": True, "message": "Job cancelled"}


@router.get("/jobs/{job_id}/sections", response_model=List[SectionResponse])
async def get_sections(job_id: str):
    sections = job_service.get_job_sections(job_id)
    result = []
    
    for section in sections:
        mindmap = job_service.get_mindmap(section.id)
        result.append(SectionResponse(section=section, mindmap=mindmap))
    
    return result


@router.get("/sections/{section_id}", response_model=SectionResponse)
async def get_section(section_id: str):
    section = job_service.get_section(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    mindmap = job_service.get_mindmap(section_id)
    return SectionResponse(section=section, mindmap=mindmap)


@router.post("/sections/{section_id}/retry", response_model=SectionResponse)
async def retry_section(section_id: str):
    try:
        section = await runner_service.retry_section(section_id)
        mindmap = job_service.get_mindmap(section_id)
        return SectionResponse(section=section, mindmap=mindmap)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/mindmaps/{job_id}", response_model=MindMapResponse)
async def get_mindmaps(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    mindmaps = job_service.get_job_mindmaps(job_id)
    
    sections_data = {}
    for section_id, mindmap in mindmaps.items():
        sections_data[section_id] = mindmap.model_dump()
    
    return MindMapResponse(
        job_id=job_id,
        sections=list(sections_data.values()),
        format="json",
    )


@router.get("/mindmaps/{job_id}/download")
async def download_mindmap(
    job_id: str,
    format: str = Query("json", enum=["json", "mermaid", "markdown"]),
):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    mindmaps = job_service.get_job_mindmaps(job_id)
    
    if format == "json":
        content = json.dumps(
            {section_id: mm.model_dump() for section_id, mm in mindmaps.items()},
            default=str,
            indent=2,
        )
        media_type = "application/json"
        filename = f"mindmap_{job_id}.json"
    elif format == "mermaid":
        content = generate_mermaid(mindmaps)
        media_type = "text/plain"
        filename = f"mindmap_{job_id}.mmd"
    elif format == "markdown":
        content = generate_markdown(mindmaps)
        media_type = "text/markdown"
        filename = f"mindmap_{job_id}.md"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def generate_mermaid(mindmaps: dict) -> str:
    lines = ["mindmap"]
    
    for section_id, mindmap in mindmaps.items():
        root = next((n for n in mindmap.nodes if n.parent_id is None), None)
        if not root:
            continue
        
        lines.append(f"  root(({root.label}))")
        
        def add_children(parent_id: str, indent: int):
            children = [n for n in mindmap.nodes if n.parent_id == parent_id]
            for child in children:
                lines.append("  " * indent + f"({child.label})")
                add_children(child.id, indent + 1)
        
        add_children(root.id, 2)
    
    return "\n".join(lines)


def generate_markdown(mindmaps: dict) -> str:
    lines = ["# Mind Map\n"]
    
    for section_id, mindmap in mindmaps.items():
        lines.append(f"## {mindmap.section_title}\n")
        
        root = next((n for n in mindmap.nodes if n.parent_id is None), None)
        if not root:
            continue
        
        def add_children(parent_id: str, indent: int):
            children = [n for n in mindmap.nodes if n.parent_id == parent_id]
            for child in children:
                citation = f" [{', '.join(child.citations)}]" if child.citations else ""
                lines.append("  " * indent + f"- {child.label}{citation}")
                add_children(child.id, indent + 1)
        
        lines.append(f"- **{root.label}**")
        add_children(root.id, 1)
        lines.append("")
    
    return "\n".join(lines)


@router.get("/agents/status", response_model=AgentStatusResponse)
async def get_agent_status():
    agents = job_service.get_agents()
    return AgentStatusResponse(agents=agents)


@router.get("/logs", response_model=LogResponse)
async def get_logs(
    job_id: Optional[str] = None,
    section_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    event_type: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
):
    events, total = await event_service.get_events(
        job_id=job_id,
        section_id=section_id,
        agent_name=agent_name,
        event_type=event_type,
        level=level,
        limit=limit,
        offset=offset,
    )
    
    return LogResponse(
        events=events,
        total=total,
        has_more=offset + len(events) < total,
    )


@router.get("/logs/export")
async def export_logs(
    job_id: str,
    format: str = Query("json", enum=["json", "csv"]),
):
    try:
        content = await event_service.export_events(job_id, format)
        
        media_type = "application/json" if format == "json" else "text/csv"
        filename = f"logs_{job_id}.{format}"
        
        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/events/{job_id}")
async def websocket_events(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    queue = await event_service.subscribe(job_id)
    
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event.model_dump(mode="json"))
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await event_service.unsubscribe(job_id, queue)
