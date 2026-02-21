"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface WelcomeDialogProps {
  open: boolean;
  onFillProfile: () => void;
  onDismiss: () => void;
}

export function WelcomeDialog({ open, onFillProfile, onDismiss }: WelcomeDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-in fade-in duration-200">
      <Card className="w-[420px] max-w-[90vw] shadow-xl">
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-xl">Welcome to Vita</CardTitle>
          <CardDescription>Your AI Wellness &amp; Nutrition Coach</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            To give you the most accurate and personalized advice, Vita needs some basic information about you — like your age, weight, height, activity level, and goals.
          </p>
          <div className="rounded-lg bg-muted/50 border p-3 text-sm space-y-1.5">
            <p className="font-medium">How to get the best results:</p>
            <p className="text-muted-foreground">
              Open the <strong>Your Profile</strong> section in the sidebar (left side) and fill in all the required fields. This takes about 30 seconds and ensures every answer is tailored to you.
            </p>
          </div>
          <div className="flex gap-2 pt-1">
            <Button className="flex-1" onClick={onFillProfile}>
              Fill Profile Now
            </Button>
            <Button variant="ghost" onClick={onDismiss}>
              Maybe Later
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
