import asyncio
import json
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from collections import defaultdict

from ..schemas.models import Event, EventType, generate_id
from ..config import get_settings


class EventService:
    def __init__(self):
        self.settings = get_settings()
        self.events: List[Event] = []
        self.subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def emit(
        self,
        event_type: EventType,
        job_id: str,
        message: str,
        section_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        level: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Event:
        event = Event(
            id=generate_id(),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            job_id=job_id,
            section_id=section_id,
            agent_id=agent_id,
            agent_name=agent_name,
            correlation_id=correlation_id or generate_id(),
            message=message,
            level=level,
            metadata=metadata or {},
        )
        
        async with self._lock:
            self.events.append(event)
        
        await self._broadcast(job_id, event)
        
        self._log_to_console(event)
        
        return event
    
    def _log_to_console(self, event: Event):
        log_data = {
            "timestamp": event.timestamp.isoformat(),
            "level": event.level,
            "job_id": event.job_id,
            "section_id": event.section_id,
            "agent_name": event.agent_name,
            "event_type": event.event_type.value,
            "message": event.message,
        }
        print(json.dumps(log_data))
    
    async def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self.subscribers[job_id].append(queue)
        return queue
    
    async def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        async with self._lock:
            if job_id in self.subscribers:
                try:
                    self.subscribers[job_id].remove(queue)
                except ValueError:
                    pass
    
    async def _broadcast(self, job_id: str, event: Event):
        async with self._lock:
            queues = self.subscribers.get(job_id, [])
            for queue in queues:
                try:
                    await queue.put(event)
                except Exception:
                    pass
    
    async def get_events(
        self,
        job_id: Optional[str] = None,
        section_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        event_type: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Event], int]:
        filtered = self.events.copy()
        
        if job_id:
            filtered = [e for e in filtered if e.job_id == job_id]
        if section_id:
            filtered = [e for e in filtered if e.section_id == section_id]
        if agent_name:
            filtered = [e for e in filtered if e.agent_name == agent_name]
        if event_type:
            filtered = [e for e in filtered if e.event_type.value == event_type]
        if level:
            filtered = [e for e in filtered if e.level == level]
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        filtered.sort(key=lambda e: e.timestamp, reverse=True)
        
        total = len(filtered)
        filtered = filtered[offset : offset + limit]
        
        return filtered, total
    
    async def get_job_events(self, job_id: str) -> List[Event]:
        return [e for e in self.events if e.job_id == job_id]
    
    async def export_events(
        self, job_id: str, format: str = "json"
    ) -> str:
        events, _ = await self.get_events(job_id=job_id, limit=10000)
        
        if format == "json":
            return json.dumps(
                [e.model_dump() for e in events],
                default=str,
                indent=2,
            )
        elif format == "csv":
            lines = ["timestamp,level,event_type,agent_name,section_id,message"]
            for e in events:
                lines.append(
                    f"{e.timestamp.isoformat()},{e.level},{e.event_type.value},"
                    f"{e.agent_name or ''},{e.section_id or ''},{e.message}"
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


event_service = EventService()
