import os
import uuid
from typing import List, Optional, Tuple
from datetime import datetime
import pdfplumber
from pypdf import PdfReader

from ..schemas.models import PDFDocument, OutlineNode, generate_id
from ..config import get_settings


class PDFService:
    def __init__(self):
        self.settings = get_settings()
        self.documents: dict[str, PDFDocument] = {}
        self.outlines: dict[str, List[OutlineNode]] = {}
        self._ensure_directories()
    
    def _ensure_directories(self):
        os.makedirs(self.settings.upload_path, exist_ok=True)
        os.makedirs(self.settings.artifacts_path, exist_ok=True)
    
    async def upload_pdf(self, filename: str, content: bytes) -> PDFDocument:
        pdf_id = generate_id()
        file_path = os.path.join(self.settings.upload_path, f"{pdf_id}_{filename}")
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        page_count, has_toc = self._analyze_pdf(file_path)
        
        doc = PDFDocument(
            id=pdf_id,
            filename=filename,
            upload_time=datetime.utcnow(),
            page_count=page_count,
            has_toc=has_toc,
            file_path=file_path,
        )
        
        self.documents[pdf_id] = doc
        return doc
    
    def _analyze_pdf(self, file_path: str) -> Tuple[int, bool]:
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            has_toc = len(reader.outline) > 0 if reader.outline else False
            return page_count, has_toc
        except Exception:
            return 0, False
    
    async def extract_outline(self, pdf_id: str) -> List[OutlineNode]:
        if pdf_id in self.outlines:
            return self.outlines[pdf_id]
        
        doc = self.documents.get(pdf_id)
        if not doc:
            raise ValueError(f"PDF document {pdf_id} not found")
        
        outline = await self._extract_outline_from_pdf(doc.file_path, doc.page_count)
        self.outlines[pdf_id] = outline
        return outline
    
    async def _extract_outline_from_pdf(
        self, file_path: str, total_pages: int
    ) -> List[OutlineNode]:
        outline_nodes = []
        
        try:
            reader = PdfReader(file_path)
            
            if reader.outline:
                outline_nodes = self._parse_pdf_outline(reader.outline, reader, total_pages)
            
            if not outline_nodes:
                outline_nodes = self._generate_page_based_outline(file_path, total_pages)
            
        except Exception as e:
            outline_nodes = self._generate_page_based_outline(file_path, total_pages)
        
        return outline_nodes
    
    def _parse_pdf_outline(
        self, outline: list, reader: PdfReader, total_pages: int, level: int = 1
    ) -> List[OutlineNode]:
        nodes = []
        
        for i, item in enumerate(outline):
            if isinstance(item, list):
                if nodes:
                    nodes[-1].children = self._parse_pdf_outline(
                        item, reader, total_pages, level + 1
                    )
            else:
                try:
                    page_num = reader.get_destination_page_number(item) + 1
                except Exception:
                    page_num = 1
                
                next_page = total_pages
                for j in range(i + 1, len(outline)):
                    if not isinstance(outline[j], list):
                        try:
                            next_page = reader.get_destination_page_number(outline[j]) + 1
                            break
                        except Exception:
                            pass
                
                node = OutlineNode(
                    id=generate_id(),
                    title=item.title if hasattr(item, 'title') else str(item),
                    level=level,
                    page_start=page_num,
                    page_end=next_page,
                    children=[],
                    selected=False,
                )
                nodes.append(node)
        
        return nodes
    
    def _generate_page_based_outline(
        self, file_path: str, total_pages: int
    ) -> List[OutlineNode]:
        nodes = []
        pages_per_section = max(5, total_pages // 10)
        
        with pdfplumber.open(file_path) as pdf:
            section_num = 1
            current_page = 1
            
            while current_page <= total_pages:
                end_page = min(current_page + pages_per_section - 1, total_pages)
                
                title = f"Section {section_num}"
                try:
                    page = pdf.pages[current_page - 1]
                    text = page.extract_text() or ""
                    lines = text.strip().split('\n')
                    if lines and len(lines[0]) < 100:
                        title = lines[0].strip() or title
                except Exception:
                    pass
                
                node = OutlineNode(
                    id=generate_id(),
                    title=title,
                    level=1,
                    page_start=current_page,
                    page_end=end_page,
                    children=[],
                    selected=False,
                )
                nodes.append(node)
                
                current_page = end_page + 1
                section_num += 1
        
        return nodes
    
    async def extract_section_text(
        self, pdf_id: str, page_start: int, page_end: int
    ) -> str:
        doc = self.documents.get(pdf_id)
        if not doc:
            raise ValueError(f"PDF document {pdf_id} not found")
        
        text_parts = []
        
        with pdfplumber.open(doc.file_path) as pdf:
            for page_num in range(page_start - 1, min(page_end, len(pdf.pages))):
                page = pdf.pages[page_num]
                text = page.extract_text() or ""
                if text:
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")
        
        return "\n\n".join(text_parts)
    
    def get_document(self, pdf_id: str) -> Optional[PDFDocument]:
        return self.documents.get(pdf_id)
    
    def get_supervisor_recommendation(
        self, outline: List[OutlineNode], total_pages: int
    ) -> str:
        total_sections = self._count_nodes(outline)
        avg_pages_per_section = total_pages / max(total_sections, 1)
        
        if avg_pages_per_section > 20:
            return (
                f"Recommended: Section-level granularity. "
                f"The document has {total_sections} sections with an average of "
                f"{avg_pages_per_section:.0f} pages each. Breaking into smaller sections "
                f"will produce more detailed and focused mind maps."
            )
        elif avg_pages_per_section < 5:
            return (
                f"Recommended: Chapter-level granularity. "
                f"The document has many small sections ({total_sections} sections, "
                f"~{avg_pages_per_section:.0f} pages each). Combining into chapters "
                f"will produce more coherent mind maps."
            )
        else:
            return (
                f"Recommended: Current structure looks good. "
                f"The document has {total_sections} sections with ~{avg_pages_per_section:.0f} "
                f"pages each, which is suitable for mind map generation."
            )
    
    def _count_nodes(self, nodes: List[OutlineNode]) -> int:
        count = len(nodes)
        for node in nodes:
            count += self._count_nodes(node.children)
        return count


pdf_service = PDFService()
