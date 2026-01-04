import { useState, useEffect, useCallback } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  XCircle,
  CheckCircle,
  AlertCircle,
  Clock,
  Loader2,
  User,
  Cpu,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import type { Job, Section, AgentInfo, Event } from '../types';

interface JobMonitorProps {
  jobId: string;
  onComplete: () => void;
  onBack: () => void;
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-500',
  extracting: 'bg-blue-500',
  building: 'bg-purple-500',
  validating: 'bg-yellow-500',
  repairing: 'bg-orange-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  needs_review: 'bg-amber-500',
};

const agentStatusColors: Record<string, string> = {
  idle: 'bg-gray-400',
  processing: 'bg-green-500',
  waiting: 'bg-yellow-500',
  error: 'bg-red-500',
};

export function JobMonitor({ jobId, onComplete, onBack }: JobMonitorProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { events, isConnected } = useWebSocket(jobId);

  const fetchJobData = useCallback(async () => {
    try {
      const response = await api.getJob(jobId);
      setJob(response.job);
      setSections(response.sections);
      setAgents(response.agents);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJobData();
    const interval = setInterval(fetchJobData, 5000);
    return () => clearInterval(interval);
  }, [fetchJobData]);

  useEffect(() => {
    if (events.length > 0) {
      fetchJobData();
    }
  }, [events, fetchJobData]);

  const handleStart = async () => {
    try {
      await api.startJob(jobId);
      fetchJobData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start job');
    }
  };

  const handlePause = async () => {
    try {
      await api.pauseJob(jobId);
      fetchJobData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause job');
    }
  };

  const handleResume = async () => {
    try {
      await api.resumeJob(jobId);
      fetchJobData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume job');
    }
  };

  const handleCancel = async () => {
    try {
      await api.cancelJob(jobId);
      fetchJobData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  };

  const handleRetrySection = async (sectionId: string) => {
    try {
      await api.retrySection(sectionId);
      fetchJobData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry section');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-8">
        <p className="text-destructive">Job not found</p>
        <Button onClick={onBack} className="mt-4">
          Go Back
        </Button>
      </div>
    );
  }

  const progress = job.total_sections > 0
    ? (job.completed_sections / job.total_sections) * 100
    : 0;

  const isRunning = job.status === 'running';
  const isPaused = job.status === 'paused';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';
  const canStart = job.status === 'pending' || job.status === 'awaiting_approval';

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                Job: {jobId}
                <Badge variant={isCompleted ? 'default' : isFailed ? 'destructive' : 'secondary'}>
                  {job.status}
                </Badge>
              </CardTitle>
              <CardDescription>{job.pdf_filename}</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>
                {job.completed_sections} / {job.total_sections} sections
              </span>
            </div>
            <Progress value={progress} />
          </div>

          <div className="flex gap-2">
            {canStart && (
              <Button onClick={handleStart}>
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
            )}
            {isRunning && (
              <Button onClick={handlePause} variant="outline">
                <Pause className="h-4 w-4 mr-2" />
                Pause
              </Button>
            )}
            {isPaused && (
              <Button onClick={handleResume}>
                <Play className="h-4 w-4 mr-2" />
                Resume
              </Button>
            )}
            {(isRunning || isPaused) && (
              <Button onClick={handleCancel} variant="destructive">
                <XCircle className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            )}
            {isCompleted && (
              <Button onClick={onComplete}>
                View Results
              </Button>
            )}
            <Button variant="outline" onClick={onBack}>
              Back
            </Button>
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <Card key={agent.id}>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${agentStatusColors[agent.status]}`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {agent.name === 'Supervisor' ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Cpu className="h-4 w-4" />
                    )}
                    <span className="font-medium">{agent.name}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{agent.role}</p>
                  {agent.current_task && (
                    <p className="text-xs text-primary mt-1">{agent.current_task}</p>
                  )}
                </div>
                <Badge variant="outline">{agent.tasks_completed}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Section Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sections.map((section) => (
              <div
                key={section.id}
                className="flex items-center gap-4 p-3 rounded-lg bg-muted/50"
              >
                <div className={`w-2 h-2 rounded-full ${statusColors[section.status]}`} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{section.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Pages {section.page_start} - {section.page_end}
                  </p>
                </div>
                <Badge variant="outline" className="capitalize">
                  {section.status.replace('_', ' ')}
                </Badge>
                {(section.status === 'failed' || section.status === 'needs_review') && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRetrySection(section.id)}
                  >
                    <RotateCcw className="h-3 w-3 mr-1" />
                    Retry
                  </Button>
                )}
                {section.status === 'completed' && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                {section.status === 'failed' && (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                )}
                {['extracting', 'building', 'validating', 'repairing'].includes(section.status) && (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                )}
                {section.status === 'pending' && (
                  <Clock className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Live Logs</CardTitle>
          <CardDescription>Real-time event stream</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-64 rounded-md border p-4">
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No events yet. Start the job to see logs.
              </p>
            ) : (
              <div className="space-y-2">
                {events.map((event) => (
                  <div
                    key={event.id}
                    className={`text-sm font-mono ${
                      event.level === 'ERROR'
                        ? 'text-red-500'
                        : event.level === 'WARNING'
                        ? 'text-yellow-500'
                        : 'text-muted-foreground'
                    }`}
                  >
                    <span className="text-xs opacity-60">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>{' '}
                    {event.agent_name && (
                      <span className="text-primary">[{event.agent_name}]</span>
                    )}{' '}
                    {event.message}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
