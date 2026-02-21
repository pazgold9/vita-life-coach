"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { fetchHistory, type HistoryItem } from "@/lib/api";

export function HistoryPanel({
  refreshKey,
  onSelect,
}: {
  refreshKey: number;
  onSelect: (prompt: string) => void;
}) {
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    fetchHistory().then(setItems);
  }, [refreshKey]);

  if (!items.length) {
    return (
      <div className="text-sm text-muted-foreground px-1 py-4">
        No conversation history yet.
      </div>
    );
  }

  return (
    <ScrollArea className="h-[calc(100vh-12rem)]">
      <div className="space-y-2 pr-3">
        {items.map((item) => (
          <Card
            key={item.id}
            className="p-3 cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => onSelect(item.prompt)}
          >
            <p className="text-xs text-muted-foreground">
              {new Date(item.created_at).toLocaleString()}
            </p>
            <p className="text-sm font-medium truncate mt-0.5">
              {item.prompt}
            </p>
            <Separator className="my-1.5" />
            <p className="text-xs text-muted-foreground line-clamp-2">
              {item.response?.slice(0, 150)}
              {item.response && item.response.length > 150 ? "…" : ""}
            </p>
          </Card>
        ))}
      </div>
    </ScrollArea>
  );
}
