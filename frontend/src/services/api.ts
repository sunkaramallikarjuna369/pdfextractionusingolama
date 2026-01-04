import type {
  UploadResponse,
  OutlineResponse,
  JobResponse,
  LogResponse,
  Section,
  MindMapSpec,
  AgentInfo,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${API_URL}/api/v1`;
  }

  async uploadPdf(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/pdf/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async getOutline(pdfId: string): Promise<OutlineResponse> {
    const response = await fetch(`${this.baseUrl}/pdf/${pdfId}/outline`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get outline');
    }

    return response.json();
  }

  async createJob(
    pdfId: string,
    granularity: string,
    selectedSections?: string[]
  ): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pdf_id: pdfId,
        granularity,
        selected_sections: selectedSections,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create job');
    }

    return response.json();
  }

  async getJob(jobId: string): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get job');
    }

    return response.json();
  }

  async updatePlan(
    jobId: string,
    sections: Array<Record<string, unknown>>,
    granularity: string,
    approved: boolean
  ): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/plan`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sections, granularity, approved }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update plan');
    }

    return response.json();
  }

  async startJob(jobId: string): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/start`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start job');
    }

    return response.json();
  }

  async pauseJob(jobId: string): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/pause`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to pause job');
    }

    return response.json();
  }

  async resumeJob(jobId: string): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/resume`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to resume job');
    }

    return response.json();
  }

  async cancelJob(jobId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to cancel job');
    }
  }

  async getSections(jobId: string): Promise<Array<{ section: Section; mindmap: MindMapSpec | null }>> {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/sections`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get sections');
    }

    return response.json();
  }

  async retrySection(sectionId: string): Promise<{ section: Section; mindmap: MindMapSpec | null }> {
    const response = await fetch(`${this.baseUrl}/sections/${sectionId}/retry`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to retry section');
    }

    return response.json();
  }

  async getMindmaps(jobId: string): Promise<{ job_id: string; sections: MindMapSpec[]; format: string }> {
    const response = await fetch(`${this.baseUrl}/mindmaps/${jobId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get mindmaps');
    }

    return response.json();
  }

  async downloadMindmap(jobId: string, format: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/mindmaps/${jobId}/download?format=${format}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to download mindmap');
    }

    return response.blob();
  }

  async getAgentStatus(): Promise<{ agents: AgentInfo[] }> {
    const response = await fetch(`${this.baseUrl}/agents/status`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get agent status');
    }

    return response.json();
  }

  async getLogs(params: {
    job_id?: string;
    section_id?: string;
    agent_name?: string;
    event_type?: string;
    level?: string;
    limit?: number;
    offset?: number;
  }): Promise<LogResponse> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });

    const response = await fetch(`${this.baseUrl}/logs?${searchParams}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get logs');
    }

    return response.json();
  }

  async exportLogs(jobId: string, format: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/logs/export?job_id=${jobId}&format=${format}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to export logs');
    }

    return response.blob();
  }

  createWebSocket(jobId: string): WebSocket {
    const wsUrl = API_URL.replace('http', 'ws');
    return new WebSocket(`${wsUrl}/api/v1/ws/events/${jobId}`);
  }
}

export const api = new ApiService();
