"""Per-case analysis chain using LCEL — prompt template -> LLM -> structured output."""
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)


class CaseAnalysis(BaseModel):
    relevance_score: float = Field(description="Relevance score from 0.0 to 1.0")
    relevance_note: str = Field(description="Brief explanation of relevance to the query")


_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a legal research assistant. Analyze the relevance of a case to a research query. "
               "Provide a relevance score (0.0 = not relevant, 1.0 = highly relevant) and a brief note explaining why."),
    ("human", """Research Query: {query}

Case: {case_name} ({citation})
Court: {court}
Date: {date}
Summary: {summary}

Full Text (excerpt):
{full_text_excerpt}

Analyze the relevance of this case to the research query."""),
])


def get_analysis_chain():
    llm = ChatGoogleGenerativeAI(model=_config["llm"]["model"], max_output_tokens=300)
    return _prompt | llm.with_structured_output(CaseAnalysis)


def analyze_case(case_data: dict, query: str) -> CaseAnalysis:
    chain = get_analysis_chain()
    return chain.invoke({
        "query": query,
        "case_name": case_data["case_name"],
        "citation": case_data["citation"],
        "court": case_data["court"],
        "date": case_data["date"],
        "summary": case_data["summary"],
        "full_text_excerpt": case_data["full_text"][:2000],
    })
