export interface PDFDocument {
  id: string;
  filename: string;
  upload_time: string;
  page_count: number;
  has_toc: boolean;
  file_path: string;
}

export interface OutlineNode {
  id: string;
  title: string;
  level: number;
  page_start: number;
  page_end: number;
  children: OutlineNode[];
  selected: boolean;
}

export type JobStatus = 
  | 'pending'
  | 'planning'
  | 'awaiting_approval'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed';

export type SectionStatus =
  | 'pending'
  | 'extracting'
  | 'building'
  | 'validating'
  | 'repairing'
  | 'completed'
  | 'failed'
  | 'needs_review';

export type AgentStatus = 'idle' | 'processing' | 'waiting' | 'error';

export interface Section {
  id: string;
  job_id: string;
  title: string;
  level: number;
  page_start: number;
  page_end: number;
  status: SectionStatus;
  assigned_worker: string | null;
  extracted_content: string | null;
  mindmap_spec: Record<string, unknown> | null;
  retry_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkPlan {
  job_id: string;
  sections: Section[];
  granularity: string;
  human_approved: boolean;
  approved_at: string | null;
  supervisor_recommendation: string | null;
}

export interface Job {
  id: string;
  pdf_id: string;
  pdf_filename: string;
  status: JobStatus;
  work_plan: WorkPlan | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  total_sections: number;
  completed_sections: number;
  failed_sections: number;
  current_section: string | null;
}

export interface MindMapNode {
  id: string;
  label: string;
  parent_id: string | null;
  level: number;
  citations: string[];
  metadata: Record<string, unknown>;
}

export interface MindMapSpec {
  job_id: string;
  section_id: string;
  section_title: string;
  root_node: string;
  nodes: MindMapNode[];
  edges: { source: string; target: string }[];
  version: number;
  created_at: string;
  validated: boolean;
}

export interface AgentInfo {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  current_task: string | null;
  current_section: string | null;
  tasks_completed: number;
  last_activity: string | null;
}

export interface Event {
  id: string;
  timestamp: string;
  event_type: string;
  job_id: string;
  section_id: string | null;
  agent_id: string | null;
  agent_name: string | null;
  correlation_id: string;
  message: string;
  level: string;
  metadata: Record<string, unknown>;
}

export interface UploadResponse {
  success: boolean;
  pdf_id: string;
  filename: string;
  page_count: number;
  has_toc: boolean;
  message: string;
}

export interface OutlineResponse {
  pdf_id: string;
  filename: string;
  outline: OutlineNode[];
  total_pages: number;
  supervisor_recommendation: string | null;
}

export interface JobResponse {
  job: Job;
  sections: Section[];
  agents: AgentInfo[];
}

export interface LogResponse {
  events: Event[];
  total: number;
  has_more: boolean;
}
