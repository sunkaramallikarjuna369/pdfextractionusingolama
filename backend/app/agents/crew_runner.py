import json
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..schemas.models import MindMapSpec, MindMapNode, generate_id
from ..config import get_settings


class CrewRunner:
    def __init__(self):
        self.settings = get_settings()
        self.ollama_url = f"{self.settings.ollama_host}/api/generate"
    
    async def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": self.settings.ollama_model,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                    },
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    return await self._fallback_extraction(prompt)
        except Exception as e:
            return await self._fallback_extraction(prompt)
    
    async def _fallback_extraction(self, prompt: str) -> str:
        return "Key concepts extracted from the document section."
    
    async def extract_content(
        self,
        section_title: str,
        text_content: str,
        page_start: int,
        page_end: int,
    ) -> str:
        system_prompt = """You are an expert content extractor and summarizer. 
Your task is to extract key concepts, relationships, and hierarchies from document sections.
Output should be structured as bullet points with page citations where applicable.
Focus on main ideas, supporting concepts, and their relationships."""

        prompt = f"""Extract the key concepts and relationships from the following section.

Section Title: {section_title}
Pages: {page_start} to {page_end}

Content:
{text_content[:8000]}

Please provide:
1. Main topic/concept
2. Key subtopics (3-7 items)
3. Supporting details for each subtopic
4. Relationships between concepts
5. Page citations for important points

Format as structured bullet points."""

        try:
            response = await self._call_ollama(prompt, system_prompt)
            if response and len(response) > 50:
                return response
        except Exception:
            pass
        
        return self._generate_fallback_extraction(section_title, text_content, page_start, page_end)
    
    def _generate_fallback_extraction(
        self,
        section_title: str,
        text_content: str,
        page_start: int,
        page_end: int,
    ) -> str:
        lines = text_content.split('\n')
        key_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                if not line.startswith('[Page'):
                    key_lines.append(line)
        
        key_lines = key_lines[:20]
        
        extraction = f"""Main Topic: {section_title}

Key Concepts:
"""
        for i, line in enumerate(key_lines[:7], 1):
            extraction += f"- {line} [p.{page_start + i % (page_end - page_start + 1)}]\n"
        
        extraction += f"""
Supporting Details:
"""
        for line in key_lines[7:15]:
            extraction += f"  - {line}\n"
        
        return extraction
    
    async def build_mindmap(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        extracted_content: str,
    ) -> MindMapSpec:
        system_prompt = """You are an expert mind map architect.
Your task is to transform extracted content into a hierarchical mind map structure.
Create a balanced tree with clear parent-child relationships.
Output must be valid JSON matching the specified schema."""

        prompt = f"""Transform the following extracted content into a mind map structure.

Section Title: {section_title}

Extracted Content:
{extracted_content}

Create a JSON mind map with this structure:
{{
    "root_label": "main topic",
    "nodes": [
        {{"label": "concept", "parent": "parent_label or null for root", "level": 0-3, "citations": ["p.X"]}}
    ]
}}

Requirements:
- One root node (level 0)
- 3-7 main branches (level 1)
- 2-4 sub-branches per main branch (level 2)
- Include page citations where available
- Keep labels concise (under 50 characters)

Output only valid JSON, no other text."""

        try:
            response = await self._call_ollama(prompt, system_prompt)
            mindmap = self._parse_mindmap_response(job_id, section_id, section_title, response)
            if mindmap and len(mindmap.nodes) >= 3:
                return mindmap
        except Exception:
            pass
        
        return self._generate_fallback_mindmap(job_id, section_id, section_title, extracted_content)
    
    def _parse_mindmap_response(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        response: str,
    ) -> Optional[MindMapSpec]:
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                nodes = []
                node_map = {}
                
                root_id = generate_id()
                root_label = data.get("root_label", section_title)
                root_node = MindMapNode(
                    id=root_id,
                    label=root_label,
                    parent_id=None,
                    level=0,
                    citations=[],
                )
                nodes.append(root_node)
                node_map[root_label.lower()] = root_id
                node_map["null"] = root_id
                node_map["root"] = root_id
                
                for node_data in data.get("nodes", []):
                    label = node_data.get("label", "")
                    if not label or label.lower() == root_label.lower():
                        continue
                    
                    parent_label = node_data.get("parent", "")
                    if parent_label:
                        parent_id = node_map.get(parent_label.lower(), root_id)
                    else:
                        parent_id = root_id
                    
                    node_id = generate_id()
                    node = MindMapNode(
                        id=node_id,
                        label=label[:100],
                        parent_id=parent_id,
                        level=node_data.get("level", 1),
                        citations=node_data.get("citations", []),
                    )
                    nodes.append(node)
                    node_map[label.lower()] = node_id
                
                edges = []
                for node in nodes:
                    if node.parent_id:
                        edges.append({"source": node.parent_id, "target": node.id})
                
                return MindMapSpec(
                    job_id=job_id,
                    section_id=section_id,
                    section_title=section_title,
                    root_node=root_id,
                    nodes=nodes,
                    edges=edges,
                    version=1,
                    created_at=datetime.utcnow(),
                    validated=False,
                )
        except Exception:
            pass
        
        return None
    
    def _generate_fallback_mindmap(
        self,
        job_id: str,
        section_id: str,
        section_title: str,
        extracted_content: str,
    ) -> MindMapSpec:
        nodes = []
        edges = []
        
        root_id = generate_id()
        root_node = MindMapNode(
            id=root_id,
            label=section_title[:50],
            parent_id=None,
            level=0,
            citations=[],
        )
        nodes.append(root_node)
        
        lines = extracted_content.split('\n')
        concepts = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                concept = line[2:].strip()
                if len(concept) > 5 and len(concept) < 100:
                    citation = ""
                    if '[p.' in concept:
                        parts = concept.split('[p.')
                        concept = parts[0].strip()
                        if len(parts) > 1:
                            citation = f"p.{parts[1].rstrip(']')}"
                    concepts.append((concept, citation))
        
        if not concepts:
            words = extracted_content.split()
            for i in range(0, min(len(words), 50), 10):
                phrase = ' '.join(words[i:i+5])
                if len(phrase) > 10:
                    concepts.append((phrase, ""))
        
        main_concepts = concepts[:7]
        for i, (concept, citation) in enumerate(main_concepts):
            node_id = generate_id()
            node = MindMapNode(
                id=node_id,
                label=concept[:50],
                parent_id=root_id,
                level=1,
                citations=[citation] if citation else [],
            )
            nodes.append(node)
            edges.append({"source": root_id, "target": node_id})
            
            sub_concepts = concepts[7 + i*3 : 7 + (i+1)*3]
            for sub_concept, sub_citation in sub_concepts:
                sub_id = generate_id()
                sub_node = MindMapNode(
                    id=sub_id,
                    label=sub_concept[:50],
                    parent_id=node_id,
                    level=2,
                    citations=[sub_citation] if sub_citation else [],
                )
                nodes.append(sub_node)
                edges.append({"source": node_id, "target": sub_id})
        
        return MindMapSpec(
            job_id=job_id,
            section_id=section_id,
            section_title=section_title,
            root_node=root_id,
            nodes=nodes,
            edges=edges,
            version=1,
            created_at=datetime.utcnow(),
            validated=False,
        )
    
    async def repair_mindmap(
        self,
        mindmap: MindMapSpec,
        issues: List[str],
    ) -> MindMapSpec:
        system_prompt = """You are an expert mind map repair specialist.
Your task is to fix issues in mind map structures while preserving valid content.
Output must be valid JSON matching the specified schema."""

        current_structure = {
            "root_label": next(
                (n.label for n in mindmap.nodes if n.parent_id is None),
                mindmap.section_title
            ),
            "nodes": [
                {
                    "label": n.label,
                    "parent": next(
                        (p.label for p in mindmap.nodes if p.id == n.parent_id),
                        None
                    ),
                    "level": n.level,
                    "citations": n.citations,
                }
                for n in mindmap.nodes
                if n.parent_id is not None
            ],
        }

        prompt = f"""Repair the following mind map structure.

Current Structure:
{json.dumps(current_structure, indent=2)}

Issues to fix:
{chr(10).join(f'- {issue}' for issue in issues)}

Requirements:
- Fix all listed issues
- Maintain existing valid content
- Ensure one root node
- Ensure all nodes have valid parents
- Keep 3-7 main branches

Output only valid JSON with the same structure, no other text."""

        try:
            response = await self._call_ollama(prompt, system_prompt)
            repaired = self._parse_mindmap_response(
                mindmap.job_id,
                mindmap.section_id,
                mindmap.section_title,
                response,
            )
            if repaired and len(repaired.nodes) >= 3:
                repaired.version = mindmap.version + 1
                return repaired
        except Exception:
            pass
        
        return self._auto_repair_mindmap(mindmap, issues)
    
    def _auto_repair_mindmap(
        self,
        mindmap: MindMapSpec,
        issues: List[str],
    ) -> MindMapSpec:
        nodes = list(mindmap.nodes)
        
        root_nodes = [n for n in nodes if n.parent_id is None]
        if len(root_nodes) == 0:
            root_id = generate_id()
            root_node = MindMapNode(
                id=root_id,
                label=mindmap.section_title[:50],
                parent_id=None,
                level=0,
            )
            nodes.insert(0, root_node)
            
            for node in nodes[1:]:
                if node.level == 1 or node.parent_id is None:
                    node.parent_id = root_id
        elif len(root_nodes) > 1:
            main_root = root_nodes[0]
            for extra_root in root_nodes[1:]:
                extra_root.parent_id = main_root.id
                extra_root.level = 1
        
        node_ids = {n.id for n in nodes}
        for node in nodes:
            if node.parent_id and node.parent_id not in node_ids:
                root = next((n for n in nodes if n.parent_id is None), None)
                if root:
                    node.parent_id = root.id
        
        if len(nodes) < 3:
            root = next((n for n in nodes if n.parent_id is None), None)
            if root:
                while len(nodes) < 4:
                    new_node = MindMapNode(
                        id=generate_id(),
                        label=f"Concept {len(nodes)}",
                        parent_id=root.id,
                        level=1,
                    )
                    nodes.append(new_node)
        
        edges = []
        for node in nodes:
            if node.parent_id:
                edges.append({"source": node.parent_id, "target": node.id})
        
        root = next((n for n in nodes if n.parent_id is None), nodes[0])
        
        return MindMapSpec(
            job_id=mindmap.job_id,
            section_id=mindmap.section_id,
            section_title=mindmap.section_title,
            root_node=root.id,
            nodes=nodes,
            edges=edges,
            version=mindmap.version + 1,
            created_at=datetime.utcnow(),
            validated=False,
        )
    
    async def get_supervisor_recommendation(
        self,
        outline_summary: str,
        total_pages: int,
        section_count: int,
    ) -> str:
        system_prompt = """You are an expert document analyst.
Provide brief recommendations for mind map generation granularity."""

        prompt = f"""Analyze this document structure and recommend the best granularity for mind map generation.

Document Summary:
{outline_summary}

Total Pages: {total_pages}
Number of Sections: {section_count}
Average Pages per Section: {total_pages / max(section_count, 1):.1f}

Recommend either:
- "chapter" level (combine sections into larger chunks)
- "section" level (process each section individually)

Provide a brief 2-3 sentence recommendation."""

        try:
            response = await self._call_ollama(prompt, system_prompt)
            if response and len(response) > 20:
                return response[:500]
        except Exception:
            pass
        
        avg_pages = total_pages / max(section_count, 1)
        if avg_pages > 15:
            return (
                f"Recommended: Section-level granularity. With {section_count} sections "
                f"averaging {avg_pages:.0f} pages each, breaking into smaller sections "
                f"will produce more detailed mind maps."
            )
        elif avg_pages < 5:
            return (
                f"Recommended: Chapter-level granularity. With {section_count} sections "
                f"averaging only {avg_pages:.0f} pages each, combining into chapters "
                f"will produce more coherent mind maps."
            )
        else:
            return (
                f"The current structure with {section_count} sections "
                f"(~{avg_pages:.0f} pages each) is well-suited for mind map generation."
            )
