"""Day 1 hand-rolled agent loop: model call -> tool selection -> execution -> observation -> repeat."""
import json
import logging
import anthropic
import yaml
from pathlib import Path

from agent.tools import TOOL_SCHEMAS, TOOL_DISPATCH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_client = anthropic.Anthropic()
_model = _config["llm"]["model"]
_max_tokens = _config["llm"]["max_tokens"]

SYSTEM_PROMPT = """You are a legal research assistant. Your job is to research case law relevant to a user's query.

You have access to tools that let you search a case law corpus, retrieve full case texts, analyze their relevance, and validate citations.

Follow this workflow:
1. Use search_cases to find potentially relevant cases.
2. For the top results, use get_case_text to retrieve details.
3. Use analyze_relevance to determine each case's relevance to the query.
4. Use validate_citation to confirm case IDs are valid before citing them.
5. After analyzing cases, provide a research memo summarizing your findings with proper citations.

If a tool returns an error (e.g., case not found), handle it gracefully — skip that case and continue with others. Do not stop the entire research process because of one failed tool call.

Always cite cases you reference and note if any cases could not be fully analyzed."""

MAX_ITERATIONS = 15


def run_agent(query: str, on_event=None) -> str:
    """Run the agent loop for a research query. Returns the final memo text.

    Args:
        query: The research query to investigate.
        on_event: Optional callback(event_dict) for streaming agent events.
    """
    messages = [{"role": "user", "content": query}]

    def emit(event):
        if on_event:
            on_event(event)
        logger.info(json.dumps(event, default=str)[:500])

    emit({"type": "agent_start", "query": query})

    for iteration in range(MAX_ITERATIONS):
        emit({"type": "llm_call", "iteration": iteration + 1})

        response = _client.messages.create(
            model=_model,
            max_tokens=_max_tokens,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text
            emit({"type": "agent_done", "iterations": iteration + 1})
            return final_text

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text
            emit({"type": "agent_done", "iterations": iteration + 1})
            return final_text

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input
            tool_id = tool_block.id

            emit({
                "type": "tool_call",
                "tool": tool_name,
                "input": tool_input,
                "iteration": iteration + 1,
            })

            func = TOOL_DISPATCH.get(tool_name)
            if not func:
                result = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    result = func(**tool_input)
                except Exception as e:
                    result = {"error": f"Tool execution failed: {str(e)}"}

            emit({
                "type": "tool_result",
                "tool": tool_name,
                "result_preview": json.dumps(result, default=str)[:300],
                "is_error": "error" in result if isinstance(result, dict) else False,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(result, default=str),
            })

        messages.append({"role": "user", "content": tool_results})

    emit({"type": "agent_done", "iterations": MAX_ITERATIONS, "reason": "max_iterations"})
    return "Research incomplete — maximum iterations reached."
