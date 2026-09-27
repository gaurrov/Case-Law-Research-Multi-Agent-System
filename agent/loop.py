"""Day 1 hand-rolled agent loop: model call -> tool selection -> execution -> observation -> repeat."""
import json
import logging
from google import genai
from google.genai import types
import yaml
from pathlib import Path

from agent.tools import _get_gemini_tools, TOOL_DISPATCH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_model_name = _config["llm"]["model"]

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

_client = genai.Client()


def run_agent(query: str, on_event=None) -> str:
    """Run the agent loop for a research query. Returns the final memo text."""

    def emit(event):
        if on_event:
            on_event(event)
        logger.info(json.dumps(event, default=str)[:500])

    emit({"type": "agent_start", "query": query})

    chat = _client.chats.create(
        model=_model_name,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[_get_gemini_tools()],
        ),
    )

    response = chat.send_message(query)

    for iteration in range(MAX_ITERATIONS):
        emit({"type": "llm_call", "iteration": iteration + 1})

        function_calls = []
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call and part.function_call.name:
                    function_calls.append(part)

        if not function_calls:
            final_text = response.text or ""
            emit({"type": "agent_done", "iterations": iteration + 1})
            return final_text

        function_responses = []
        for part in function_calls:
            fc = part.function_call
            tool_name = fc.name
            tool_input = dict(fc.args) if fc.args else {}
            for key, val in tool_input.items():
                if isinstance(val, float) and val == int(val):
                    tool_input[key] = int(val)

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

            is_error = "error" in result if isinstance(result, dict) else False
            emit({
                "type": "tool_result",
                "tool": tool_name,
                "result_preview": json.dumps(result, default=str)[:300],
                "is_error": is_error,
            })

            function_responses.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": json.dumps(result, default=str)},
                )
            )

        response = chat.send_message(function_responses)

    emit({"type": "agent_done", "iterations": MAX_ITERATIONS, "reason": "max_iterations"})
    return "Research incomplete — maximum iterations reached."
