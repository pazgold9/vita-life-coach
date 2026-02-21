"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StepViewer } from "@/components/step-viewer";
import { ProfileForm } from "@/components/profile-form";
import { WelcomeDialog } from "@/components/welcome-dialog";
import {
  executeAgentStream,
  fetchProfile,
  resetProfile,
  type ExecuteResponse,
  type StepRecord,
  type ConversationTurn,
  type StreamEvent,
  type UserProfile,
} from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  steps?: StepRecord[];
  isError?: boolean;
}

interface ActivityItem {
  id: string;
  type: "orchestrator" | "specialist" | "info";
  agent: string;
  message: string;
  detail?: string;
  status: "active" | "done";
  timestamp: number;
}

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [profileData, setProfileData] = useState<UserProfile>({});
  const [isProfileComplete, setIsProfileComplete] = useState(false);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [showWelcomeDialog, setShowWelcomeDialog] = useState(false);
  const [showProfileForm, setShowProfileForm] = useState(false);
  const [showMobileProfileForm, setShowMobileProfileForm] = useState(false);
  const [skipAttempts, setSkipAttempts] = useState(0);
  const [forcedSkip, setForcedSkip] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const activityIdRef = useRef(0);

  useEffect(() => {
    // Reset profile on every visit so each visitor starts fresh
    resetProfile().then(() => {
      setProfileData({});
      setIsProfileComplete(false);
      setMissingFields(["name", "age", "sex", "weight_kg", "height_cm", "activity_level", "dietary_restrictions", "medical_conditions", "goals"]);
      setShowWelcomeDialog(true);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, activity]);

  function refreshProfile() {
    fetchProfile().then((res) => {
      setProfileData(res.profile);
      setIsProfileComplete(res.is_complete);
      setMissingFields(res.missing_fields);
      if (res.is_complete) {
        setForcedSkip(false);
        setShowProfileForm(false);
        setShowMobileProfileForm(false);
      }
    });
  }

  function buildHistory(): ConversationTurn[] {
    const recent = messages.slice(-10);
    return recent.map((m) => ({ role: m.role, content: m.content }));
  }

  function addActivity(
    type: ActivityItem["type"],
    agent: string,
    message: string,
    detail?: string,
    status: ActivityItem["status"] = "active",
  ) {
    const id = `act-${++activityIdRef.current}`;
    setActivity((prev) => [...prev, { id, type, agent, message, detail, status, timestamp: Date.now() }]);
    return id;
  }

  function markAgentDone(agent: string, message?: string) {
    setActivity((prev) =>
      prev.map((a) =>
        a.agent === agent && a.status === "active"
          ? { ...a, status: "done" as const, message: message || a.message }
          : a,
      ),
    );
  }

  const handleStreamEvent = useCallback((event: StreamEvent) => {
    const msg = event.message || "";
    switch (event.event) {
      case "orchestrator_start":
        addActivity("orchestrator", "Head Coach", msg || "Analyzing your question...");
        break;
      case "orchestrator_thinking":
        markAgentDone("Head Coach");
        addActivity("orchestrator", "Head Coach", msg || "Thinking...");
        break;
      case "orchestrator_thought":
        markAgentDone("Head Coach");
        addActivity("orchestrator", "Head Coach", msg, undefined, "done");
        break;
      case "specialists_dispatched":
        addActivity("info", "System", msg || "Dispatching specialists...", undefined, "done");
        break;
      case "specialist_start":
        addActivity("specialist", event.specialist || "Specialist", msg || `${event.specialist} working...`, event.task);
        break;
      case "specialist_done": {
        const name = event.specialist || "Specialist";
        markAgentDone(name, `${name} completed`);
        if (event.summary) {
          addActivity("specialist", name, event.summary, undefined, "done");
        }
        break;
      }
      case "composing":
        addActivity("orchestrator", "Head Coach", msg || "Composing your answer...");
        break;
      case "done":
        markAgentDone("Head Coach", "Composing your answer...");
        break;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const chatEnabled = isProfileComplete || forcedSkip;

  async function handleRun() {
    const text = prompt.trim();
    if (!text || loading || !chatEnabled) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setPrompt("");
    setLoading(true);
    setActivity([]);
    activityIdRef.current = 0;

    const profileMode = (!isProfileComplete && forcedSkip) ? "anonymous" : undefined;

    try {
      const history = buildHistory();
      const data: ExecuteResponse = await executeAgentStream(
        text,
        history,
        handleStreamEvent,
        profileMode,
      );
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content:
          data.status === "error"
            ? data.error || "Unknown error"
            : data.response || "",
        steps: data.steps,
        isError: data.status === "error",
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (!profileMode) {
        refreshProfile();
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "Request failed",
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      setActivity([]);
    }
  }

  function handleNewConversation() {
    setMessages([]);
    setPrompt("");
    textareaRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleRun();
    }
  }

  function handleSkipAttempt() {
    if (skipAttempts >= 1) {
      setForcedSkip(true);
    }
    setSkipAttempts((prev) => prev + 1);
  }

  const agentColor: Record<string, string> = {
    "Head Coach": "text-blue-400",
    "Nutrition Expert": "text-green-400",
    "Science Researcher": "text-purple-400",
    "Wellness Coach": "text-amber-400",
    System: "text-muted-foreground",
  };

  const agentIcon: Record<string, string> = {
    "Head Coach": "\u{1F9E0}",
    "Nutrition Expert": "\u{1F96C}",
    "Science Researcher": "\u{1F52C}",
    "Wellness Coach": "\u{1F9D8}",
    System: "\u{2699}\u{FE0F}",
  };

  const profileItems = [
    { label: "Name", value: profileData.name },
    { label: "Age", value: profileData.age },
    { label: "Sex", value: profileData.sex },
    { label: "Weight", value: profileData.weight_kg ? `${profileData.weight_kg} kg` : undefined },
    { label: "Height", value: profileData.height_cm ? `${profileData.height_cm} cm` : undefined },
    { label: "Activity", value: profileData.activity_level },
    { label: "Diet", value: profileData.dietary_restrictions },
    { label: "Conditions", value: profileData.medical_conditions },
    { label: "Goals", value: profileData.goals },
  ].filter((p) => p.value);

  return (
    <div className="flex h-screen">
      {/* Welcome Dialog */}
      <WelcomeDialog
        open={showWelcomeDialog}
        onFillProfile={() => {
          setShowWelcomeDialog(false);
          setShowProfileForm(true);
        }}
        onDismiss={() => setShowWelcomeDialog(false)}
      />

      {/* Mobile Profile Form Overlay */}
      {showMobileProfileForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 md:hidden animate-in fade-in duration-200">
          <Card className="w-[90vw] max-h-[90vh] overflow-y-auto shadow-xl">
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold mb-3">Your Profile</h3>
              <ProfileForm
                initialData={profileData}
                missingFields={missingFields}
                onSave={() => {
                  refreshProfile();
                  setShowMobileProfileForm(false);
                }}
                onCancel={() => setShowMobileProfileForm(false)}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Sidebar */}
      <aside className="w-72 border-r bg-muted/30 p-4 hidden md:flex flex-col overflow-y-auto">
        <div className="mb-4">
          <h1 className="text-xl font-bold tracking-tight">Vita</h1>
          <p className="text-xs text-muted-foreground">
            AI Wellness &amp; Nutrition Coach
          </p>
        </div>
        <Separator className="mb-4" />
        <Button
          variant="outline"
          size="sm"
          className="mb-4 w-full"
          onClick={handleNewConversation}
        >
          + New Conversation
        </Button>

        {/* Profile Section */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Your Profile
            </p>
            <Button
              variant="ghost"
              size="xs"
              className="text-xs h-6 px-2"
              onClick={() => setShowProfileForm(!showProfileForm)}
            >
              {showProfileForm ? "Close" : isProfileComplete ? "Edit" : "Fill In"}
            </Button>
          </div>

          {showProfileForm ? (
            <ProfileForm
              initialData={profileData}
              missingFields={missingFields}
              onSave={refreshProfile}
              onCancel={() => setShowProfileForm(false)}
            />
          ) : profileItems.length > 0 ? (
            <div className="space-y-0.5">
              {profileItems.map((item) => (
                <div key={item.label} className="flex justify-between text-xs">
                  <span className="text-muted-foreground">{item.label}</span>
                  <span className="text-foreground font-medium truncate ml-2 max-w-[140px]">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No profile data yet. Fill in your details for personalized advice.
            </p>
          )}
        </div>
        <Separator className="mb-4" />

        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
          Try asking
        </p>
        <div className="space-y-2">
          {[
            "I'm [age], [sex], [weight]kg, [height]cm, [activity level]. Build me a meal plan",
            "What does research say about [topic]?",
            "I have [condition/symptom]. What should I eat?",
            "Give me a [meal type] with high [nutrient]",
            "Help me improve my [sleep / stress / energy]",
            "Is [supplement/food] safe? What does science say?",
          ].map((t) => (
            <button
              key={t}
              onClick={() => { if (chatEnabled) { setPrompt(t); textareaRef.current?.focus(); } }}
              className={`w-full text-left text-xs px-3 py-2 rounded-lg border border-input hover:bg-muted/50 transition-colors leading-snug ${!chatEnabled ? "opacity-50 cursor-not-allowed" : ""}`}
              disabled={!chatEnabled}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="mt-auto pt-4">
          <Separator className="mb-3" />
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Agents
            </p>
            <div className="flex items-center gap-2 text-xs">
              <span>{agentIcon["Head Coach"]}</span>
              <span className={agentColor["Head Coach"]}>Head Coach</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span>{agentIcon["Nutrition Expert"]}</span>
              <span className={agentColor["Nutrition Expert"]}>Nutrition Expert</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span>{agentIcon["Science Researcher"]}</span>
              <span className={agentColor["Science Researcher"]}>Science Researcher</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span>{agentIcon["Wellness Coach"]}</span>
              <span className={agentColor["Wellness Coach"]}>Wellness Coach</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <header className="border-b px-6 py-3 flex items-center gap-3">
          <div className="md:hidden">
            <h1 className="text-lg font-bold">Vita</h1>
          </div>
          <div className="hidden md:block">
            <h2 className="text-sm font-semibold">
              Conversation ({messages.filter((m) => m.role === "user").length}{" "}
              turns)
            </h2>
          </div>
          <div className="ml-auto flex gap-2">
            {/* Mobile profile button */}
            <Button
              variant="outline"
              size="sm"
              className="md:hidden"
              onClick={() => setShowMobileProfileForm(true)}
            >
              Profile
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={handleNewConversation}
            >
              New
            </Button>
          </div>
        </header>

        {/* Chat Thread */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {/* Anonymous warning banner */}
            {forcedSkip && !isProfileComplete && (
              <div className="bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm px-4 py-2.5 rounded-lg text-center">
                Profile incomplete — results may not be personalized or accurate.{" "}
                <button
                  className="underline hover:text-amber-100"
                  onClick={() => {
                    setShowProfileForm(true);
                    setShowMobileProfileForm(true);
                  }}
                >
                  Fill Profile
                </button>
              </div>
            )}

            {messages.length === 0 && !loading && (
              <div className="text-center py-20 text-muted-foreground">
                <p className="text-lg font-medium mb-1">Welcome to Vita</p>
                <p className="text-sm">
                  Ask a wellness, nutrition, or health question to start a
                  conversation.
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i}>
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-br-md bg-primary text-primary-foreground px-4 py-2.5 text-sm whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <Card
                      className={`max-w-[85%] ${
                        msg.isError
                          ? "border-destructive/50 bg-destructive/5"
                          : ""
                      }`}
                    >
                      <CardContent className="p-4">
                        <div className="text-sm whitespace-pre-wrap break-words leading-relaxed">
                          {msg.content}
                        </div>
                        {msg.steps && msg.steps.length > 0 && (
                          <div className="mt-3">
                            <StepViewer steps={msg.steps} />
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                )}
              </div>
            ))}

            {/* Live Activity Timeline */}
            {loading && activity.length > 0 && (
              <div className="flex justify-start">
                <Card className="max-w-[85%] w-full">
                  <CardContent className="p-4">
                    <div className="space-y-2.5">
                      {activity.map((item) => (
                        <div key={item.id} className="flex items-start gap-2.5 animate-in fade-in slide-in-from-bottom-1 duration-300">
                          <span className="text-base mt-0.5 shrink-0">
                            {item.status === "active" ? (
                              <span className="inline-block h-4 w-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
                            ) : (
                              agentIcon[item.agent] || "\u{2705}"
                            )}
                          </span>
                          <div className="min-w-0">
                            <span className={`text-xs font-semibold ${agentColor[item.agent] || "text-foreground"}`}>
                              {item.agent}
                            </span>
                            <p className="text-sm text-foreground/90 leading-snug">
                              {item.message}
                            </p>
                            {item.detail && (
                              <p className="text-xs text-muted-foreground mt-0.5 italic">
                                Task: {item.detail}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {loading && activity.length === 0 && (
              <div className="flex justify-start">
                <Card>
                  <CardContent className="p-4">
                    <span className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span className="h-4 w-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                      Connecting...
                    </span>
                  </CardContent>
                </Card>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input Bar */}
        <div className="border-t bg-background px-6 py-4">
          <div className="max-w-3xl mx-auto">
            {/* Profile gate message */}
            {!chatEnabled && (
              <div className="mb-3 text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  {skipAttempts === 0 && "Complete your profile to start chatting."}
                  {skipAttempts === 1 && "Last chance — Your results will be much less accurate without a complete profile. Are you sure you want to skip?"}
                </p>
                <div className="flex items-center justify-center gap-2">
                  <Button
                    size="sm"
                    onClick={() => {
                      setShowProfileForm(true);
                      setShowMobileProfileForm(true);
                    }}
                  >
                    Fill Profile
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground"
                    onClick={handleSkipAttempt}
                  >
                    {skipAttempts === 0 ? "Skip for now" : "Skip anyway"}
                  </Button>
                </div>
              </div>
            )}

            <div className="flex gap-3 items-end">
              <textarea
                ref={textareaRef}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder={chatEnabled ? "Ask a question..." : "Complete your profile to start chatting..."}
                className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={loading || !chatEnabled}
              />
              <Button
                onClick={handleRun}
                disabled={loading || !prompt.trim() || !chatEnabled}
                size="default"
              >
                {loading ? (
                  <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  "Send"
                )}
              </Button>
            </div>
            {chatEnabled && (
              <p className="text-center text-xs text-muted-foreground mt-2">
                Cmd + Enter to send
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
