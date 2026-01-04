import json
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from ..config import get_settings


class AgentLogType(str, Enum):
    DECISION = "decision"
    REASONING = "reasoning"
    ACTION = "action"
    RESULT = "result"
    ERROR = "error"
    VALIDATION = "validation"
    REPAIR = "repair"


class LokiLogger:
    def __init__(self):
        self.settings = get_settings()
        self.loki_url = f"{self.settings.loki_host}/loki/api/v1/push"
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_size = 10
        self._lock = asyncio.Lock()
    
    async def log_agent_activity(
        self,
        agent_name: str,
        log_type: AgentLogType,
        job_id: str,
        section_id: Optional[str] = None,
        section_title: Optional[str] = None,
        message: str = "",
        reasoning: Optional[str] = None,
        decision: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
    ):
        timestamp = datetime.utcnow()
        timestamp_ns = str(int(timestamp.timestamp() * 1e9))
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "agent_name": agent_name,
            "log_type": log_type.value,
            "job_id": job_id,
            "section_id": section_id,
            "section_title": section_title,
            "message": message,
            "reasoning": reasoning,
            "decision": decision,
            "level": level,
        }
        
        if input_data:
            log_entry["input_summary"] = self._summarize_data(input_data)
        if output_data:
            log_entry["output_summary"] = self._summarize_data(output_data)
        if metrics:
            log_entry["metrics"] = metrics
        
        print(f"[AGENT_LOG] {json.dumps(log_entry)}")
        
        loki_entry = {
            "streams": [
                {
                    "stream": {
                        "job": "pdf-mindmap",
                        "agent": agent_name,
                        "log_type": log_type.value,
                        "level": level,
                        "job_id": job_id,
                    },
                    "values": [
                        [timestamp_ns, json.dumps(log_entry)]
                    ]
                }
            ]
        }
        
        if section_id:
            loki_entry["streams"][0]["stream"]["section_id"] = section_id
        
        await self._send_to_loki(loki_entry)
        
        return log_entry
    
    async def log_supervisor_decision(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        decision: str,
        reasoning: str,
        factors: Dict[str, Any],
    ):
        return await self.log_agent_activity(
            agent_name="Supervisor",
            log_type=AgentLogType.DECISION,
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            message=f"Supervisor decision for section: {section_title}",
            decision=decision,
            reasoning=reasoning,
            input_data=factors,
        )
    
    async def log_extractor_activity(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        page_start: int,
        page_end: int,
        action: str,
        reasoning: str,
        extracted_concepts: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        input_data = {
            "section_title": section_title,
            "page_range": f"{page_start}-{page_end}",
            "page_count": page_end - page_start + 1,
        }
        
        output_data = None
        if extracted_concepts:
            output_data = {
                "concept_count": len(extracted_concepts),
                "concepts_preview": extracted_concepts[:5],
            }
        
        return await self.log_agent_activity(
            agent_name="Extractor",
            log_type=AgentLogType.ACTION,
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            message=action,
            reasoning=reasoning,
            input_data=input_data,
            output_data=output_data,
            metrics=metrics,
        )
    
    async def log_builder_activity(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        action: str,
        reasoning: str,
        node_count: Optional[int] = None,
        depth: Optional[int] = None,
        structure_summary: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        output_data = {}
        if node_count is not None:
            output_data["node_count"] = node_count
        if depth is not None:
            output_data["max_depth"] = depth
        if structure_summary:
            output_data["structure"] = structure_summary
        
        return await self.log_agent_activity(
            agent_name="Builder",
            log_type=AgentLogType.ACTION,
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            message=action,
            reasoning=reasoning,
            output_data=output_data if output_data else None,
            metrics=metrics,
        )
    
    async def log_validation_result(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        passed: bool,
        issues: List[str],
        warnings: List[str],
        metrics: Dict[str, Any],
    ):
        return await self.log_agent_activity(
            agent_name="Supervisor",
            log_type=AgentLogType.VALIDATION,
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            message=f"Validation {'passed' if passed else 'failed'} for {section_title}",
            reasoning=f"Issues: {issues}" if issues else "All validation checks passed",
            decision="approve" if passed else "repair_needed",
            output_data={
                "passed": passed,
                "issues": issues,
                "warnings": warnings,
            },
            metrics=metrics,
            level="INFO" if passed else "WARNING",
        )
    
    async def log_repair_attempt(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        attempt_number: int,
        issues_to_fix: List[str],
        repair_strategy: str,
        success: bool,
    ):
        return await self.log_agent_activity(
            agent_name="Builder",
            log_type=AgentLogType.REPAIR,
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            message=f"Repair attempt {attempt_number} {'succeeded' if success else 'failed'}",
            reasoning=f"Strategy: {repair_strategy}. Issues to fix: {', '.join(issues_to_fix)}",
            decision="repair_complete" if success else "retry_repair",
            input_data={
                "attempt": attempt_number,
                "issues": issues_to_fix,
            },
            output_data={
                "success": success,
                "strategy": repair_strategy,
            },
            level="INFO" if success else "WARNING",
        )
    
    async def log_mindmap_generation_summary(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        total_nodes: int,
        max_depth: int,
        branch_count: int,
        has_citations: bool,
        generation_time_ms: float,
        llm_calls: int,
    ):
        return await self.log_agent_activity(
            agent_name="Builder",
            log_type=AgentLogType.RESULT,
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            message=f"Mind map generated for {section_title}",
            reasoning=f"Created hierarchical structure with {total_nodes} nodes across {max_depth} levels",
            output_data={
                "total_nodes": total_nodes,
                "max_depth": max_depth,
                "branch_count": branch_count,
                "has_citations": has_citations,
            },
            metrics={
                "generation_time_ms": generation_time_ms,
                "llm_calls": llm_calls,
                "nodes_per_second": total_nodes / (generation_time_ms / 1000) if generation_time_ms > 0 else 0,
            },
        )
    
    def _summarize_data(self, data: Dict[str, Any], max_length: int = 500) -> Dict[str, Any]:
        summary = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > max_length:
                summary[key] = value[:max_length] + "..."
            elif isinstance(value, list) and len(value) > 10:
                summary[key] = f"[{len(value)} items]"
            elif isinstance(value, dict) and len(str(value)) > max_length:
                summary[key] = f"{{...{len(value)} keys...}}"
            else:
                summary[key] = value
        return summary
    
    async def _send_to_loki(self, entry: Dict[str, Any]):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.loki_url,
                    json=entry,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code not in [200, 204]:
                    print(f"[LOKI_ERROR] Failed to send log: {response.status_code}")
        except Exception as e:
            print(f"[LOKI_ERROR] Connection failed: {str(e)}")


loki_logger = LokiLogger()
