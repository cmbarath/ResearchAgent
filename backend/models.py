from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The research or query question")

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str

class CitationItem(BaseModel):
    index: int
    url: str
    title: Optional[str] = None

class AgentEvent(BaseModel):
    type: Literal["step", "tool_call", "tool_result", "error", "final", "done"]
    step: int = 0
    message: Optional[str] = None
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result_summary: Optional[str] = None
    raw_result: Optional[Any] = None
    error: Optional[str] = None
    final_answer: Optional[str] = None
    citations: Optional[List[str]] = None
    fetched_urls: Optional[List[str]] = None
    discovered_urls: Optional[List[str]] = None
    token_usage: Optional[Dict[str, int]] = None
