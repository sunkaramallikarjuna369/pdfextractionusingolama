import { useState, useCallback } from 'react';
import { ChevronRight, ChevronDown, FileText, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { OutlineNode, OutlineResponse } from '../types';

interface OutlineSelectorProps {
  outline: OutlineResponse;
  onApprove: (selectedIds: string[], granularity: string) => void;
  onBack: () => void;
}

export function OutlineSelector({ outline, onApprove, onBack }: OutlineSelectorProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => {
    const ids = new Set<string>();
    const collectIds = (nodes: OutlineNode[]) => {
      nodes.forEach((node) => {
        ids.add(node.id);
        collectIds(node.children);
      });
    };
    collectIds(outline.outline);
    return ids;
  });
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [granularity, setGranularity] = useState<string>('section');

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleSelected = useCallback((id: string, node: OutlineNode) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      
      const toggleNode = (n: OutlineNode, selected: boolean) => {
        if (selected) {
          next.add(n.id);
        } else {
          next.delete(n.id);
        }
        n.children.forEach((child) => toggleNode(child, selected));
      };

      const isSelected = next.has(id);
      toggleNode(node, !isSelected);
      
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    const ids = new Set<string>();
    const collectIds = (nodes: OutlineNode[]) => {
      nodes.forEach((node) => {
        ids.add(node.id);
        collectIds(node.children);
      });
    };
    collectIds(outline.outline);
    setSelectedIds(ids);
  }, [outline.outline]);

  const selectNone = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleApprove = useCallback(() => {
    onApprove(Array.from(selectedIds), granularity);
  }, [selectedIds, granularity, onApprove]);

  const renderNode = (node: OutlineNode, depth: number = 0) => {
    const hasChildren = node.children.length > 0;
    const isExpanded = expandedIds.has(node.id);
    const isSelected = selectedIds.has(node.id);

    return (
      <div key={node.id} className="select-none">
        <div
          className={`
            flex items-center gap-2 py-2 px-2 rounded-md hover:bg-muted/50
            ${depth > 0 ? 'ml-6' : ''}
          `}
        >
          {hasChildren ? (
            <button
              onClick={() => toggleExpanded(node.id)}
              className="p-1 hover:bg-muted rounded"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          ) : (
            <div className="w-6" />
          )}

          <Checkbox
            checked={isSelected}
            onCheckedChange={() => toggleSelected(node.id, node)}
          />

          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{node.title}</p>
            <p className="text-xs text-muted-foreground">
              Pages {node.page_start} - {node.page_end}
            </p>
          </div>
        </div>

        {hasChildren && isExpanded && (
          <div className="border-l-2 border-muted ml-4">
            {node.children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-6 w-6" />
            Document Outline
          </CardTitle>
          <CardDescription>
            {outline.filename} - {outline.total_pages} pages
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {outline.supervisor_recommendation && (
            <Alert>
              <Lightbulb className="h-4 w-4" />
              <AlertDescription>
                <strong>Supervisor Recommendation:</strong>{' '}
                {outline.supervisor_recommendation}
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            <div>
              <Label className="text-base font-semibold">Granularity</Label>
              <p className="text-sm text-muted-foreground mb-3">
                Choose how to divide the document for mind map generation
              </p>
              <RadioGroup value={granularity} onValueChange={setGranularity}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="chapter" id="chapter" />
                  <Label htmlFor="chapter">Chapter Level</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="section" id="section" />
                  <Label htmlFor="section">Section Level</Label>
                </div>
              </RadioGroup>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={selectAll}>
                Select All
              </Button>
              <Button variant="outline" size="sm" onClick={selectNone}>
                Select None
              </Button>
            </div>

            <div className="border rounded-lg max-h-96 overflow-y-auto p-2">
              {outline.outline.map((node) => renderNode(node))}
            </div>

            <p className="text-sm text-muted-foreground">
              {selectedIds.size} section(s) selected
            </p>
          </div>

          <div className="flex justify-between">
            <Button variant="outline" onClick={onBack}>
              Back
            </Button>
            <Button onClick={handleApprove} disabled={selectedIds.size === 0}>
              Approve & Create Job
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
