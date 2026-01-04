import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Download,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { api } from '../services/api';
import type { Event, LogResponse } from '../types';

interface LogDashboardProps {
  jobId?: string;
}

const levelColors: Record<string, string> = {
  INFO: 'bg-blue-500',
  WARNING: 'bg-yellow-500',
  ERROR: 'bg-red-500',
  DEBUG: 'bg-gray-500',
};

const eventTypeLabels: Record<string, string> = {
  job_created: 'Job Created',
  job_started: 'Job Started',
  job_paused: 'Job Paused',
  job_resumed: 'Job Resumed',
  job_completed: 'Job Completed',
  job_failed: 'Job Failed',
  plan_approved: 'Plan Approved',
  section_queued: 'Section Queued',
  section_started: 'Section Started',
  section_extracted: 'Section Extracted',
  section_built: 'Section Built',
  section_validated: 'Section Validated',
  section_completed: 'Section Completed',
  section_failed: 'Section Failed',
  section_retried: 'Section Retried',
  agent_started: 'Agent Started',
  agent_completed: 'Agent Completed',
  agent_error: 'Agent Error',
  validation_passed: 'Validation Passed',
  validation_failed: 'Validation Failed',
  repair_started: 'Repair Started',
  repair_completed: 'Repair Completed',
  log_message: 'Log Message',
};

export function LogDashboard({ jobId }: LogDashboardProps) {
  const [logs, setLogs] = useState<Event[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    job_id: jobId || '',
    section_id: '',
    agent_name: '',
    event_type: '',
    level: '',
    limit: 50,
    offset: 0,
  });

  const fetchLogs = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: Record<string, string | number | undefined> = {};
      
      if (filters.job_id) params.job_id = filters.job_id;
      if (filters.section_id) params.section_id = filters.section_id;
      if (filters.agent_name) params.agent_name = filters.agent_name;
      if (filters.event_type) params.event_type = filters.event_type;
      if (filters.level) params.level = filters.level;
      params.limit = filters.limit;
      params.offset = filters.offset;

      const response = await api.getLogs(params);
      setLogs(response.events);
      setTotal(response.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      offset: 0,
    }));
  };

  const handlePageChange = (direction: 'prev' | 'next') => {
    setFilters((prev) => ({
      ...prev,
      offset: direction === 'next'
        ? prev.offset + prev.limit
        : Math.max(0, prev.offset - prev.limit),
    }));
  };

  const handleExport = async (format: string) => {
    if (!filters.job_id) {
      setError('Please select a job to export logs');
      return;
    }

    try {
      const blob = await api.exportLogs(filters.job_id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `logs_${filters.job_id}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export logs');
    }
  };

  const currentPage = Math.floor(filters.offset / filters.limit) + 1;
  const totalPages = Math.ceil(total / filters.limit);

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Log Dashboard
            </CardTitle>
            <CardDescription>
              Search and filter system logs
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => handleExport('json')}>
              <Download className="h-4 w-4 mr-2" />
              JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport('csv')}>
              <Download className="h-4 w-4 mr-2" />
              CSV
            </Button>
            <Button variant="outline" size="sm" onClick={fetchLogs}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="space-y-2">
            <Label>Job ID</Label>
            <Input
              placeholder="Filter by job..."
              value={filters.job_id}
              onChange={(e) => handleFilterChange('job_id', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Section ID</Label>
            <Input
              placeholder="Filter by section..."
              value={filters.section_id}
              onChange={(e) => handleFilterChange('section_id', e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Agent</Label>
            <Select
              value={filters.agent_name}
              onValueChange={(value) => handleFilterChange('agent_name', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="All agents" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All agents</SelectItem>
                <SelectItem value="Supervisor">Supervisor</SelectItem>
                <SelectItem value="Extractor">Extractor</SelectItem>
                <SelectItem value="Builder">Builder</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Event Type</Label>
            <Select
              value={filters.event_type}
              onValueChange={(value) => handleFilterChange('event_type', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="All events" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All events</SelectItem>
                {Object.entries(eventTypeLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Level</Label>
            <Select
              value={filters.level}
              onValueChange={(value) => handleFilterChange('level', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="All levels" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All levels</SelectItem>
                <SelectItem value="INFO">INFO</SelectItem>
                <SelectItem value="WARNING">WARNING</SelectItem>
                <SelectItem value="ERROR">ERROR</SelectItem>
                <SelectItem value="DEBUG">DEBUG</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <ScrollArea className="h-96 rounded-lg border">
          <div className="p-4 space-y-2">
            {logs.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                No logs found matching your filters.
              </p>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50"
                >
                  <div className={`w-2 h-2 rounded-full mt-2 ${levelColors[log.level] || 'bg-gray-500'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground font-mono">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {log.level}
                      </Badge>
                      {log.agent_name && (
                        <Badge variant="secondary" className="text-xs">
                          {log.agent_name}
                        </Badge>
                      )}
                      <Badge className="text-xs">
                        {eventTypeLabels[log.event_type] || log.event_type}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm">{log.message}</p>
                    {log.section_id && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Section: {log.section_id}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {filters.offset + 1} - {Math.min(filters.offset + filters.limit, total)} of {total} logs
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange('prev')}
              disabled={filters.offset === 0}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm">
              Page {currentPage} of {totalPages || 1}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange('next')}
              disabled={filters.offset + filters.limit >= total}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
