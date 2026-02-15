"""API route handlers for Vita."""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend import config
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
    try:
        # Placeholder: will call runner/orchestrator once implemented
        from backend.agents.runner import run_agent

        response_text, steps = run_agent(body.prompt)
        return ExecuteResponse(
            status="ok",
            error=None,
            response=response_text,
            steps=[StepRecord(module=s["module"], prompt=s["prompt"], response=s["response"]) for s in steps],
        )
    except Exception as e:
        logger.exception("Execute failed")
        return ExecuteResponse(
            status="error",
            error=str(e),
            response=None,
            steps=[],
        )
