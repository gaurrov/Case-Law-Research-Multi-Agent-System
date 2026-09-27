"""Synthesis chain — takes analyzed findings and produces a research memo."""
import yaml
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a legal research assistant writing a research memo.
Synthesize the analyzed case findings into a clear, well-structured memo.

IMPORTANT RULES:
- Only cite cases from the 'analyzed cases' list below.
- Do NOT cite any case from the 'not analyzed' list.
- If cases could not be analyzed, mention them in a 'Limitations' section.
- Include proper legal citations for all referenced cases.
- Structure as: Summary, Relevant Cases, Analysis, Limitations (if any), Conclusion."""),
    ("human", """Research Query: {query}

Analyzed Cases:
{analyzed_cases}

Cases Not Fully Analyzed:
{not_analyzed_cases}

Write a research memo based on these findings."""),
])


def get_synthesis_chain():
    llm = ChatAnthropic(model=_config["llm"]["model"], max_tokens=2048)
    return _prompt | llm | StrOutputParser()


def synthesize_memo(query: str, analyzed: list[dict], not_analyzed: list[dict]) -> str:
    chain = get_synthesis_chain()

    analyzed_text = "\n".join(
        f"- {a['case_name']} ({a['citation']}): score={a['relevance_score']}, {a['relevance_note']}"
        for a in analyzed
    ) or "No cases were successfully analyzed."

    not_analyzed_text = "\n".join(
        f"- Case ID {a['case_id']}: {a.get('reason', 'analysis failed or timed out')}"
        for a in not_analyzed
    ) or "All cases were successfully analyzed."

    return chain.invoke({
        "query": query,
        "analyzed_cases": analyzed_text,
        "not_analyzed_cases": not_analyzed_text,
    })
