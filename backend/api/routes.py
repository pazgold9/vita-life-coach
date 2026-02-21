"""API route handlers for Vita."""
import json
import logging
import queue
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from backend import config
from backend import db


def _json_safe(obj):
    """Convert to JSON-serializable form (raw API responses can have datetime etc)."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return str(obj)


from backend.api.schemas import (
    AgentInfoResponse,
    ExecuteRequest,
    ExecuteResponse,
    ProfileUpdateRequest,
    PromptExample,
    PromptTemplate,
    StepRecord,
    TeamInfoResponse,
)

router = APIRouter(prefix="/api", tags=["api"])
logger = logging.getLogger(__name__)


@router.get("/env_check")
def get_env_check():
    """Check if required env vars are set (no values exposed)."""
    return {
        "llmod_api_key_set": bool(config.LLMOD_API_KEY),
        "llmod_base_url": config.LLMOD_BASE_URL[:30] + "..." if config.LLMOD_BASE_URL and len(config.LLMOD_BASE_URL) > 30 else (config.LLMOD_BASE_URL or "(not set)"),
        "pinecone_api_key_set": bool(config.PINECONE_API_KEY),
        "pinecone_index_name": config.PINECONE_INDEX_NAME or "(not set)",
        "supabase_connected": bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY),
    }


@router.get("/team_info", response_model=TeamInfoResponse)
def get_team_info() -> TeamInfoResponse:
    """Return student details (names and emails)."""
    return TeamInfoResponse(
        group_batch_order_number=config.GROUP_BATCH_ORDER_NUMBER,
        team_name=config.TEAM_NAME,
        students=[{"name": s["name"], "email": s["email"]} for s in config.STUDENTS],
    )


@router.get("/agent_info", response_model=AgentInfoResponse)
def get_agent_info() -> AgentInfoResponse:
    """Return agent meta: description, purpose, prompt template, and examples."""
    return AgentInfoResponse(
        description=(
            "Vita is an AI-powered wellness and nutrition coach built on a Supervisor Agent architecture. "
            "An Orchestrator Agent (Head Coach) autonomously plans user goals using a ReAct reasoning loop, "
            "then delegates sub-tasks to three autonomous specialist agents: "
            "Nutrition Expert (RAG over Open Food Facts + USDA), "
            "Science Researcher (RAG over PubMed), and "
            "Wellness Coach (autonomous reasoning for stress, exercise, mindfulness). "
            "Each specialist runs its own ReAct loop with domain-specific tools, and the Orchestrator "
            "synthesizes all specialist outputs into a single coherent response. "
            "Conversation history is persisted via Supabase."
        ),
        purpose="To reduce nutrition confusion and adherence friction by providing precise dietary recommendations (RAG), evidence-based answers from research (RAG), and non-diet wellness protocols — all coordinated by an autonomous multi-agent system.",
        prompt_template=PromptTemplate(
            template="Describe your goal or question in one or two sentences. Examples: 'What's a healthy breakfast for weight loss?', 'Is intermittent fasting supported by research?', 'I need stress relief tips.' The Orchestrator will decompose your request into sub-tasks and route each to the right specialist, then return one coherent response."
        ),
        prompt_examples=[
            PromptExample(
                prompt="What's a healthy breakfast for weight loss?",
                full_response="A healthy breakfast for weight loss could include: (1) Protein—e.g. eggs or Greek yogurt—to keep you full; (2) Fiber—oats or whole-grain toast; (3) Minimal added sugar. Pair with fruit or nuts. Portion control and timing matter more than a single 'best' food; the Nutrition Expert can tailor this to your preferences and the Science Researcher can back it with evidence.",
                steps=[
                    {
                        "module": "Orchestrator Agent",
                        "prompt": {"messages": [{"role": "user", "content": "Plan and route: What's a healthy breakfast for weight loss?"}]},
                        "response": {"choices": [{"message": {"content": "Thought: The user wants a healthy breakfast for weight loss. I should ask the Nutrition Expert for food options.\nAction: call_specialist\nAction Input: Nutrition Expert | Suggest healthy breakfast options for weight loss with calorie counts"}}]},
                    },
                    {
                        "module": "Nutrition Expert",
                        "prompt": {"messages": [{"role": "system", "content": "You are a Nutrition Expert..."}, {"role": "user", "content": "Task: Suggest healthy breakfast options for weight loss with calorie counts"}]},
                        "response": {"choices": [{"message": {"content": "Thought: I can answer this from my expertise.\nAction: finish\nAction Input: Protein (eggs, yogurt), fiber (oats), minimal sugar..."}}]},
                    },
                    {
                        "module": "Orchestrator Agent",
                        "prompt": {"messages": [{"role": "user", "content": "Synthesize final response from specialist answers."}]},
                        "response": {"choices": [{"message": {"content": "A healthy breakfast for weight loss could include..."}}]},
                    },
                ],
            )
        ],
    )


@router.get("/model_architecture")
def get_model_architecture():
    """Return the architecture diagram as PNG."""
    path = config.ARCHITECTURE_PNG_PATH
    if not path.exists():
        raise HTTPException(status_code=404, detail="Architecture image not found")
    return FileResponse(path, media_type="image/png")


@router.get("/history")
def get_conversation_history(
    session_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Return recent conversation history from Supabase."""
    return db.get_history(session_id=session_id, limit=limit)


@router.get("/profile")
def get_user_profile():
    """Return the current user profile with completeness status."""
    profile = db.get_profile()
    is_complete, missing = db.get_profile_completeness()
    filtered = {k: v for k, v in profile.items() if k not in ("id", "updated_at") and v is not None} if profile else {}
    return {"profile": filtered, "is_complete": is_complete, "missing_fields": missing}


@router.post("/profile/reset")
def reset_user_profile():
    """Clear all profile fields — each visit starts fresh."""
    db.reset_profile()
    return {"profile": {}, "is_complete": False, "missing_fields": list(db.PROFILE_FIELDS)}


@router.put("/profile")
def update_user_profile(body: ProfileUpdateRequest):
    """Update user profile fields from the UI form."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")
    success = db.update_profile(updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    profile = db.get_profile()
    is_complete, missing = db.get_profile_completeness()
    filtered = {k: v for k, v in profile.items() if k not in ("id", "updated_at") and v is not None} if profile else {}
    return {"profile": filtered, "is_complete": is_complete, "missing_fields": missing}


@router.post("/execute", response_model=ExecuteResponse)
def post_execute(body: ExecuteRequest) -> ExecuteResponse:
    """Main entry: run the agent and return response + full step trace."""
    if not (config.LLMOD_API_KEY and config.LLMOD_API_KEY.strip()):
        return ExecuteResponse(
            status="error",
            error="LLMOD_API_KEY is not set. Add it to your .env file in the project root (see .env.example).",
            response=None,
            steps=[],
        )
    try:
        from backend.agents.runner import run_agent

        response_text, steps = run_agent(
            body.prompt,
            conversation_history=[t.model_dump() for t in body.conversation_history],
            profile_mode=body.profile_mode,
        )
        safe_steps = [
            StepRecord(
                module=s["module"],
                prompt=_json_safe(s["prompt"]),
                response=_json_safe(s["response"]),
            )
            for s in steps
        ]

        session_id = getattr(body, "session_id", None)
        db.save_conversation(
            prompt=body.prompt,
            response=response_text,
            steps=[s.model_dump() for s in safe_steps],
            session_id=session_id,
        )

        return ExecuteResponse(
            status="ok",
            error=None,
            response=response_text,
            steps=safe_steps,
        )
    except Exception as e:
        logger.exception("Execute failed")
        err_msg = str(e)
        if "contentpolicy" in err_msg.lower() or "content_filter" in err_msg.lower() or "responsibleai" in err_msg.lower():
            err_msg = "I'm sorry, I wasn't able to process that request due to content restrictions. You can try rephrasing your question, or start a new conversation to continue."
        elif "api_key" in err_msg.lower() or "auth" in err_msg.lower() or "401" in err_msg:
            err_msg = "LLM API rejected the request (auth error). API said: %s — Check that your LLMOD_API_KEY is the exact key from LLMod.ai (re-copy it, no spaces). LLMOD_BASE_URL is correct (https://api.llmod.ai/v1)." % err_msg
        elif "pinecone" in err_msg.lower() or "index" in err_msg.lower():
            err_msg = "Pinecone error: %s. Ensure PINECONE_INDEX_NAME exists in Pinecone and its dimension matches your embedding model (e.g. 1536)." % err_msg
        elif "connection" in err_msg.lower() or "timeout" in err_msg.lower() or "refused" in err_msg.lower():
            err_msg = "Cannot reach the LLM API. Check LLMOD_BASE_URL in .env (must be the exact URL from LLMod.ai, e.g. https://api.llmod.ai/v1)."
        return ExecuteResponse(
            status="error",
            error=err_msg,
            response=None,
            steps=[],
        )


@router.post("/execute_stream")
def post_execute_stream(body: ExecuteRequest):
    """SSE endpoint: streams progress events then the final response."""
    if not (config.LLMOD_API_KEY and config.LLMOD_API_KEY.strip()):
        def _err():
            yield f"data: {json.dumps({'event': 'error', 'error': 'LLMOD_API_KEY is not set.'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    event_queue: queue.Queue = queue.Queue()

    def on_progress(event_type: str, data: dict):
        event_queue.put(json.dumps({"event": event_type, **data}))

    def run_in_background():
        try:
            from backend.agents.runner import run_agent

            response_text, steps = run_agent(
                body.prompt,
                conversation_history=[t.model_dump() for t in body.conversation_history],
                on_progress=on_progress,
                profile_mode=body.profile_mode,
            )
            safe_steps = [
                {"module": s["module"], "prompt": _json_safe(s["prompt"]), "response": _json_safe(s["response"])}
                for s in steps
            ]
            event_queue.put(json.dumps({
                "event": "result",
                "status": "ok",
                "response": response_text,
                "steps": safe_steps,
            }))
        except Exception as e:
            logger.exception("Stream execute failed")
            err_msg = str(e)
            if "contentpolicy" in err_msg.lower() or "content_filter" in err_msg.lower() or "responsibleai" in err_msg.lower():
                err_msg = "I'm sorry, I wasn't able to process that request due to content restrictions. You can try rephrasing your question, or start a new conversation to continue."
            event_queue.put(json.dumps({"event": "error", "error": err_msg}))
        event_queue.put(None)

    threading.Thread(target=run_in_background, daemon=True).start()

    def event_generator():
        while True:
            item = event_queue.get(timeout=300)
            if item is None:
                break
            yield f"data: {item}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
