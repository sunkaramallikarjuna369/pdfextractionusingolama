import { useState, useCallback } from 'react';
import { FileText, Activity, BarChart3 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PDFUploader } from './components/PDFUploader';
import { OutlineSelector } from './components/OutlineSelector';
import { JobMonitor } from './components/JobMonitor';
import { MindMapViewer } from './components/MindMapViewer';
import { LogDashboard } from './components/LogDashboard';
import { api } from './services/api';
import type { UploadResponse, OutlineResponse, JobResponse } from './types';

type AppState = 'upload' | 'outline' | 'monitor' | 'results';

function App() {
  const [state, setState] = useState<AppState>('upload');
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [outlineResponse, setOutlineResponse] = useState<OutlineResponse | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('workflow');
  const [error, setError] = useState<string | null>(null);

  const handleUploadComplete = useCallback(async (response: UploadResponse) => {
    setUploadResponse(response);
    setError(null);
    
    try {
      const outline = await api.getOutline(response.pdf_id);
      setOutlineResponse(outline);
      setState('outline');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get outline');
    }
  }, []);

  const handleApprove = useCallback(async (selectedIds: string[], granularity: string) => {
    if (!uploadResponse) return;
    
    setError(null);
    
    try {
      const jobResponse = await api.createJob(
        uploadResponse.pdf_id,
        granularity,
        selectedIds
      );
      
      const sections = jobResponse.sections.map((s) => ({
        id: s.id,
        title: s.title,
        page_start: s.page_start,
        page_end: s.page_end,
        level: s.level,
      }));
      
      await api.updatePlan(jobResponse.job.id, sections, granularity, true);
      
      setCurrentJobId(jobResponse.job.id);
      setState('monitor');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job');
    }
  }, [uploadResponse]);

  const handleBackToUpload = useCallback(() => {
    setState('upload');
    setUploadResponse(null);
    setOutlineResponse(null);
    setCurrentJobId(null);
    setError(null);
  }, []);

  const handleBackToOutline = useCallback(() => {
    setState('outline');
  }, []);

  const handleJobComplete = useCallback(() => {
    setState('results');
  }, []);

  const handleBackToMonitor = useCallback(() => {
    setState('monitor');
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-xl font-bold">PDF Mind Map Generator</h1>
                <p className="text-sm text-muted-foreground">
                  AI-powered mind map generation with CrewAI
                </p>
              </div>
            </div>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="workflow" className="flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Workflow
                </TabsTrigger>
                <TabsTrigger value="logs" className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Logs
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-destructive/10 border border-destructive rounded-lg">
            <p className="text-destructive">{error}</p>
          </div>
        )}

        {activeTab === 'workflow' && (
          <>
            {state === 'upload' && (
              <PDFUploader onUploadComplete={handleUploadComplete} />
            )}

            {state === 'outline' && outlineResponse && (
              <OutlineSelector
                outline={outlineResponse}
                onApprove={handleApprove}
                onBack={handleBackToUpload}
              />
            )}

            {state === 'monitor' && currentJobId && (
              <JobMonitor
                jobId={currentJobId}
                onComplete={handleJobComplete}
                onBack={handleBackToOutline}
              />
            )}

            {state === 'results' && currentJobId && (
              <MindMapViewer
                jobId={currentJobId}
                onBack={handleBackToMonitor}
              />
            )}
          </>
        )}

        {activeTab === 'logs' && (
          <LogDashboard jobId={currentJobId || undefined} />
        )}
      </main>

      <footer className="border-t mt-auto">
        <div className="container mx-auto px-4 py-4">
          <p className="text-sm text-muted-foreground text-center">
            PDF Mind Map Generator - Powered by CrewAI & Local Ollama
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
