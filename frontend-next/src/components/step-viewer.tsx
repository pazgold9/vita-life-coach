"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { StepRecord } from "@/lib/api";

function moduleColor(module: string): string {
  if (module.includes("Orchestrator")) return "bg-blue-100 text-blue-800";
  if (module.includes("Nutrition")) return "bg-green-100 text-green-800";
  if (module.includes("Science")) return "bg-amber-100 text-amber-800";
  if (module.includes("Wellness")) return "bg-purple-100 text-purple-800";
  return "bg-gray-100 text-gray-800";
}

function extractThought(resp: Record<string, unknown>): string {
  try {
    const choices = resp.choices as Array<{ message: { content: string } }>;
    if (choices?.[0]?.message?.content) {
      const content = choices[0].message.content;
      const match = content.match(/Thought:\s*(.+?)(?=\nAction:|\n\n|$)/);

      return match ? match[1].trim().slice(0, 200) : content.slice(0, 200);
    }
  } catch { /* ignore */ }
  return "";
}

export function StepViewer({ steps }: { steps: StepRecord[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (!steps.length) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Execution Trace — {steps.length} steps
      </h3>
      {steps.map((step, i) => (
        <Collapsible
          key={i}
          open={expandedIdx === i}
          onOpenChange={(open) => setExpandedIdx(open ? i : null)}
        >
          <Card className="p-0 overflow-hidden">
            <CollapsibleTrigger className="w-full px-4 py-3 flex items-center gap-3 hover:bg-muted/50 transition-colors text-left cursor-pointer">
              <span className="text-xs font-mono text-muted-foreground w-6">
                {i + 1}
              </span>
              <Badge variant="secondary" className={moduleColor(step.module)}>
                {step.module}
              </Badge>
              <span className="text-sm text-muted-foreground truncate flex-1">
                {extractThought(step.response)}
              </span>
              <span className="text-xs text-muted-foreground">
                {expandedIdx === i ? "▲" : "▼"}
              </span>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 pb-4 space-y-3 border-t">
                <div className="pt-3">
                  <p className="text-xs font-semibold text-muted-foreground mb-1">
                    Prompt
                  </p>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap break-words">
                    {JSON.stringify(step.prompt, null, 2)}
                  </pre>
                </div>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">
                    Response
                  </p>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap break-words">
                    {JSON.stringify(step.response, null, 2)}
                  </pre>
                </div>
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      ))}
    </div>
  );
}
