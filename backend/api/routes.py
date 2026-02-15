"""API route handlers for Vita."""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend import config


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
    PromptExample,
    PromptTemplate,
    StepRecord,
    TeamInfoResponse,
)

router = APIRouter(prefix="/api", tags=["api"])
logger = logging.getLogger(__name__)


@router.get("/env_check")
def get_env_check():
    """Check if required env vars are set (no values exposed). Use to debug .env loading."""
    return {
        "llmod_api_key_set": bool(config.LLMOD_API_KEY),
        "llmod_base_url": config.LLMOD_BASE_URL[:30] + "..." if config.LLMOD_BASE_URL and len(config.LLMOD_BASE_URL) > 30 else (config.LLMOD_BASE_URL or "(not set)"),
        "pinecone_api_key_set": bool(config.PINECONE_API_KEY),
        "pinecone_index_name": config.PINECONE_INDEX_NAME or "(not set)",
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
        description="Vita is an AI-powered wellness and nutrition coach with a single Orchestrator Agent (Head Coach) that plans user goals, routes sub-tasks to three specialists (Nutrition Expert, Science Researcher, Wellness Coach), and synthesizes a final answer. Nutrition and Science use RAG over Open Food Facts, USDA FoodData Central, and PubMed; Wellness Coach is LLM-only for stress, exercise, and mindfulness.",
        purpose="To reduce nutrition confusion and adherence friction by providing precise dietary recommendations (RAG), evidence-based answers from research (RAG), and non-diet wellness protocols.",
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
                        "response": {"choices": [{"message": {"content": "[{\"task\": \"Suggest a healthy breakfast\", \"specialist\": \"Nutrition Expert\"}]"}}]},
                    },
                    {
                        "module": "Nutrition Expert",
                        "prompt": {"task": "Suggest a healthy breakfast", "messages": "..."},
                        "response": {"choices": [{"message": {"content": "Protein (eggs, yogurt), fiber (oats), minimal sugar..."}}]},
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

        response_text, steps = run_agent(body.prompt)
        safe_steps = [
            StepRecord(
                module=s["module"],
                prompt=_json_safe(s["prompt"]),
                response=_json_safe(s["response"]),
            )
            for s in steps
        ]
        return ExecuteResponse(
            status="ok",
            error=None,
            response=response_text,
            steps=safe_steps,
        )
    except Exception as e:
        logger.exception("Execute failed")
        err_msg = str(e)
        if "api_key" in err_msg.lower() or "auth" in err_msg.lower() or "401" in err_msg:
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
