import { useState, useEffect, useCallback } from 'react';
import {
  Download,
  FileJson,
  FileText,
  Image,
  ChevronRight,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { api } from '../services/api';
import type { MindMapSpec, MindMapNode } from '../types';

interface MindMapViewerProps {
  jobId: string;
  onBack: () => void;
}

export function MindMapViewer({ jobId, onBack }: MindMapViewerProps) {
  const [mindmaps, setMindmaps] = useState<MindMapSpec[]>([]);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const fetchMindmaps = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await api.getMindmaps(jobId);
      setMindmaps(response.sections);
      if (response.sections.length > 0 && !selectedSection) {
        setSelectedSection(response.sections[0].section_id);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch mindmaps');
    } finally {
      setIsLoading(false);
    }
  }, [jobId, selectedSection]);

  useEffect(() => {
    fetchMindmaps();
  }, [fetchMindmaps]);

  const handleDownload = async (format: string) => {
    try {
      const blob = await api.downloadMindmap(jobId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mindmap_${jobId}.${format === 'mermaid' ? 'mmd' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download');
    }
  };

  const toggleNode = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const expandAll = () => {
    const allIds = new Set<string>();
    mindmaps.forEach((mm) => {
      mm.nodes.forEach((node) => allIds.add(node.id));
    });
    setExpandedNodes(allIds);
  };

  const collapseAll = () => {
    setExpandedNodes(new Set());
  };

  const renderMindMapTree = (mindmap: MindMapSpec) => {
    const nodeMap = new Map<string, MindMapNode>();
    mindmap.nodes.forEach((node) => nodeMap.set(node.id, node));

    const childrenMap = new Map<string | null, MindMapNode[]>();
    mindmap.nodes.forEach((node) => {
      const parentId = node.parent_id;
      if (!childrenMap.has(parentId)) {
        childrenMap.set(parentId, []);
      }
      childrenMap.get(parentId)!.push(node);
    });

    const renderNode = (node: MindMapNode, depth: number = 0): JSX.Element => {
      const children = childrenMap.get(node.id) || [];
      const hasChildren = children.length > 0;
      const isExpanded = expandedNodes.has(node.id);

      return (
        <div key={node.id} className="select-none">
          <div
            className={`
              flex items-start gap-2 py-1.5 px-2 rounded-md hover:bg-muted/50
              ${depth > 0 ? 'ml-4' : ''}
            `}
            style={{ marginLeft: depth * 16 }}
          >
            {hasChildren ? (
              <button
                onClick={() => toggleNode(node.id)}
                className="p-0.5 hover:bg-muted rounded mt-0.5"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
            ) : (
              <div className="w-5" />
            )}

            <div className="flex-1 min-w-0">
              <p
                className={`
                  ${depth === 0 ? 'font-bold text-lg' : ''}
                  ${depth === 1 ? 'font-semibold' : ''}
                  ${depth >= 2 ? 'text-sm' : ''}
                `}
              >
                {node.label}
              </p>
              {node.citations.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {node.citations.join(', ')}
                </p>
              )}
            </div>

            <Badge variant="outline" className="text-xs">
              L{node.level}
            </Badge>
          </div>

          {hasChildren && isExpanded && (
            <div className="border-l border-muted ml-4">
              {children.map((child) => renderNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    };

    const rootNodes = childrenMap.get(null) || [];
    return (
      <div className="space-y-1">
        {rootNodes.map((node) => renderNode(node))}
      </div>
    );
  };

  const generateMermaidCode = (mindmap: MindMapSpec): string => {
    const lines = ['mindmap'];
    
    const nodeMap = new Map<string, MindMapNode>();
    mindmap.nodes.forEach((node) => nodeMap.set(node.id, node));

    const childrenMap = new Map<string | null, MindMapNode[]>();
    mindmap.nodes.forEach((node) => {
      const parentId = node.parent_id;
      if (!childrenMap.has(parentId)) {
        childrenMap.set(parentId, []);
      }
      childrenMap.get(parentId)!.push(node);
    });

    const renderNode = (node: MindMapNode, indent: number) => {
      const prefix = '  '.repeat(indent);
      const label = node.label.replace(/[()[\]{}]/g, '');
      
      if (indent === 1) {
        lines.push(`${prefix}root((${label}))`);
      } else {
        lines.push(`${prefix}(${label})`);
      }

      const children = childrenMap.get(node.id) || [];
      children.forEach((child) => renderNode(child, indent + 1));
    };

    const rootNodes = childrenMap.get(null) || [];
    rootNodes.forEach((node) => renderNode(node, 1));

    return lines.join('\n');
  };

  const selectedMindmap = mindmaps.find((mm) => mm.section_id === selectedSection);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (mindmaps.length === 0) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No mind maps generated yet.</p>
          <Button onClick={onBack} className="mt-4">
            Go Back
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Mind Map Results</CardTitle>
              <CardDescription>
                {mindmaps.length} section(s) generated
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => handleDownload('json')}>
                <FileJson className="h-4 w-4 mr-2" />
                JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleDownload('mermaid')}>
                <FileText className="h-4 w-4 mr-2" />
                Mermaid
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleDownload('markdown')}>
                <Download className="h-4 w-4 mr-2" />
                Markdown
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="text-sm text-destructive mb-4">{error}</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="md:col-span-1">
              <h3 className="font-semibold mb-3">Sections</h3>
              <ScrollArea className="h-96">
                <div className="space-y-2">
                  {mindmaps.map((mm) => (
                    <button
                      key={mm.section_id}
                      onClick={() => setSelectedSection(mm.section_id)}
                      className={`
                        w-full text-left p-3 rounded-lg transition-colors
                        ${selectedSection === mm.section_id
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted/50 hover:bg-muted'
                        }
                      `}
                    >
                      <p className="font-medium truncate">{mm.section_title}</p>
                      <p className="text-xs opacity-70">
                        {mm.nodes.length} nodes - v{mm.version}
                      </p>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>

            <div className="md:col-span-3">
              {selectedMindmap && (
                <Tabs defaultValue="tree">
                  <div className="flex items-center justify-between mb-4">
                    <TabsList>
                      <TabsTrigger value="tree">Tree View</TabsTrigger>
                      <TabsTrigger value="mermaid">Mermaid Code</TabsTrigger>
                      <TabsTrigger value="json">JSON</TabsTrigger>
                    </TabsList>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={expandAll}>
                        Expand All
                      </Button>
                      <Button variant="ghost" size="sm" onClick={collapseAll}>
                        Collapse All
                      </Button>
                    </div>
                  </div>

                  <TabsContent value="tree">
                    <ScrollArea className="h-96 rounded-lg border p-4">
                      {renderMindMapTree(selectedMindmap)}
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="mermaid">
                    <ScrollArea className="h-96 rounded-lg border">
                      <pre className="p-4 text-sm font-mono">
                        {generateMermaidCode(selectedMindmap)}
                      </pre>
                    </ScrollArea>
                  </TabsContent>

                  <TabsContent value="json">
                    <ScrollArea className="h-96 rounded-lg border">
                      <pre className="p-4 text-sm font-mono">
                        {JSON.stringify(selectedMindmap, null, 2)}
                      </pre>
                    </ScrollArea>
                  </TabsContent>
                </Tabs>
              )}
            </div>
          </div>

          <div className="flex justify-between mt-6">
            <Button variant="outline" onClick={onBack}>
              Back to Monitor
            </Button>
            <Button onClick={fetchMindmaps}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
