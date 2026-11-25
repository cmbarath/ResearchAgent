import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

import ollama

from config import settings
from models import AgentEvent
from tools import ToolContext

SYSTEM_PROMPT = """You are a senior research analyst and AI assistant.
Your goal is to provide accurate, well-reasoned, and rigorously sourced answers to the user's research questions.

You have access to three native tools:
1. `web_search`: Search DuckDuckGo for external or recent information. Returns relevant URLs, titles, and snippets.
2. `fetch_page`: Fetch and read the full readable text content of a specific web URL.
3. `calculator`: Perform safe arithmetic math calculations (e.g. '25 * 4', '(100 + 50) / 2').

OPERATIONAL RULES:
- When answering a question requiring external information, first use `web_search` to discover candidate URLs.
- If a search query returns 0 results, do NOT give up. Reformulate your search query with different, more specific or broader keywords, and call `web_search` again.
- After receiving search results, select the most promising URL and use `fetch_page` to read the webpage content.
- For arithmetic questions, use the `calculator` tool instead of estimation.
- STRICT CITATION RULE: You may ONLY cite URLs that you have actually fetched and read using `fetch_page`. Do NOT cite URLs that were only returned in search results or never fetched.
- When sufficient evidence has been collected, do not call any more tools. Provide your final comprehensive research report.
- List all fetched sources at the end of your report under a 'Sources & Citations' section as:
  [1] URL
  [2] URL
"""

SYNTHESIS_PROMPT = """The research budget limit has been reached.
Based strictly on the information and fetched webpages collected so far, synthesize your final comprehensive research answer now.
Strictly adhere to the citation policy: list only sources from the fetched URLs."""


# Tool signature definitions for Ollama Python SDK schema generation
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo to discover relevant URLs, titles, and snippets.
    
    Args:
        query: The search query keywords or question.
    """
    return ""


def fetch_page(url: str) -> str:
    """Fetch and read the clean text content from a web URL.
    
    Args:
        url: The web URL to fetch and inspect.
    """
    return ""


def calculator(expression: str) -> str:
    """Safely calculate an arithmetic math expression (e.g. '25 * 4', '(100 - 30) / 2').
    
    Args:
        expression: The mathematical expression to evaluate.
    """
    return ""


TOOL_FUNCTIONS = [web_search, fetch_page, calculator]


class CustomReActAgent:
    """Manually implemented ReAct-style Agent Loop.
    
    Orchestrates the LLM through reasoning, tool selection, backend execution,
    observation feedback, and final answer synthesis without third-party frameworks.
    """

    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_HOST)
        self.model = settings.OLLAMA_MODEL
        self.max_steps = settings.MAX_STEPS
        self.max_tokens = settings.MAX_TOTAL_TOKENS

    def _extract_citations_from_text(self, text: str, valid_urls: Set[str]) -> List[str]:
        """Extracts and verifies cited URLs that strictly match successfully fetched URLs.
        
        Guarantees the invariant: FINAL CITATION URLS ⊆ SUCCESSFULLY FETCHED URLS.
        """
        if not valid_urls:
            return []

        url_pattern = r"https?://[^\s)\]\"'>]+"
        found_urls = re.findall(url_pattern, text or "")
        verified = []
        for url in found_urls:
            clean_url = url.rstrip(".,;:)")
            if clean_url in valid_urls and clean_url not in verified:
                verified.append(clean_url)

        # Fallback only to fetched URLs if LLM used numbered references without repeating full URLs
        if not verified and valid_urls:
            verified = list(valid_urls)

        # Absolute enforcement: only successfully fetched URLs are returned
        return [u for u in verified if u in valid_urls]

    async def run(self, question: str) -> AsyncGenerator[AgentEvent, None]:
        """Executes the manual ReAct agent loop and yields progressive SSE AgentEvent items."""
        tool_ctx = ToolContext()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        total_prompt_tokens = 0
        total_eval_tokens = 0
        step_count = 0
        final_answer: Optional[str] = None

        yield AgentEvent(
            type="step",
            step=1,
            message="Initializing research agent and analyzing research question...",
        )

        for step in range(1, self.max_steps + 1):
            step_count = step

            yield AgentEvent(
                type="step",
                step=step,
                message=f"Step {step}/{self.max_steps}: Reasoning and selecting next action...",
            )

            # Check token budget before LLM call
            current_total_tokens = total_prompt_tokens + total_eval_tokens
            if current_total_tokens >= self.max_tokens:
                yield AgentEvent(
                    type="error",
                    step=step,
                    message=f"Token budget of {self.max_tokens} reached. Forcing final answer synthesis.",
                )
                break

            try:
                # Call Ollama LLM with native tool definitions
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_FUNCTIONS,
                    options={
                        "temperature": 0.1,
                        "num_predict": 1024,
                    },
                )
            except Exception as e:
                yield AgentEvent(
                    type="error",
                    step=step,
                    error=f"LLM inference error: {str(e)}",
                    message="Encountered LLM connection or inference failure.",
                )
                break

            # Update token accounting if returned by Ollama
            p_tokens = getattr(response, "prompt_eval_count", 0) or response.get("prompt_eval_count", 0) or 0
            e_tokens = getattr(response, "eval_count", 0) or response.get("eval_count", 0) or 0
            total_prompt_tokens += p_tokens
            total_eval_tokens += e_tokens

            assistant_msg = response.get("message", {})
            tool_calls = assistant_msg.get("tool_calls")

            # CASE 1: LLM selected one or more tools to call
            if tool_calls:
                # Append assistant message to context
                messages.append(assistant_msg)

                for tc in tool_calls:
                    fn_name = tc.function.name if hasattr(tc, "function") else tc.get("function", {}).get("name", "")
                    fn_args = tc.function.arguments if hasattr(tc, "function") else tc.get("function", {}).get("arguments", {})

                    # Broadcast tool_call event to frontend
                    yield AgentEvent(
                        type="tool_call",
                        step=step,
                        tool=fn_name,
                        arguments=fn_args,
                        message=f"Selected tool '{fn_name}'",
                    )

                    # Execute the selected tool safely
                    tool_result_content = ""
                    summary = ""
                    raw_data: Any = None

                    try:
                        if fn_name == "web_search":
                            query = fn_args.get("query", "")
                            max_results = fn_args.get("max_results", settings.MAX_SEARCH_RESULTS)
                            res = tool_ctx.web_search(query=query, max_results=max_results)
                            raw_data = res

                            if res.get("success", False):
                                results_list = res.get("results", [])
                                if results_list:
                                    summary = res.get("summary") or f"Found {len(results_list)} relevant search results for '{query}'"
                                    formatted_items = []
                                    for idx, item in enumerate(results_list, 1):
                                        formatted_items.append(
                                            f"[{idx}] Title: {item['title']}\n"
                                            f"    URL: {item['url']}\n"
                                            f"    Snippet: {item['snippet']}"
                                        )
                                    tool_result_content = (
                                        f"DuckDuckGo search results for '{query}':\n\n"
                                        + "\n\n".join(formatted_items)
                                        + "\n\nAction: Select the best URL above and call fetch_page to read the webpage content before answering."
                                    )
                                else:
                                    summary = res.get("summary") or f"DuckDuckGo search returned 0 results for '{query}'."
                                    tool_result_content = (
                                        f"DuckDuckGo search returned 0 results for query '{query}'.\n\n"
                                        f"Action: Reformulate your search query with different, more specific or broader keywords, "
                                        f"and call web_search again. Do not give up immediately."
                                    )
                            else:
                                summary = f"Search failed: {res.get('error', 'Unknown error')}"
                                tool_result_content = f"Search error: {res.get('error')}"

                        elif fn_name == "fetch_page":
                            url = fn_args.get("url", "")
                            res = tool_ctx.fetch_page(url=url)
                            raw_data = {"url": res.get("url"), "title": res.get("title"), "length": res.get("length")}

                            if res.get("success", False):
                                summary = f"Page fetched successfully ({res.get('length', 0)} chars): {res.get('title') or url}"
                                tool_result_content = (
                                    f"Successfully fetched content from {url} (Title: {res.get('title')}):\n\n"
                                    f"{res.get('content')}\n\n"
                                    f"Action: Analyze this content. If sufficient, synthesize the final answer and cite {url}. Otherwise call another tool."
                                )
                            else:
                                summary = f"Failed to fetch {url}: {res.get('error', 'unknown error')}"
                                tool_result_content = f"Error fetching {url}: {res.get('error')}"

                        elif fn_name == "calculator":
                            expr = fn_args.get("expression", "")
                            res = tool_ctx.calculator(expression=expr)
                            raw_data = res

                            if res.get("success", False):
                                summary = f"Calculated: {expr} = {res.get('display')}"
                                tool_result_content = f"Calculation result: {expr} = {res.get('display')}"
                            else:
                                summary = f"Calculator error: {res.get('error')}"
                                tool_result_content = f"Calculator error: {res.get('error')}"

                        else:
                            summary = f"Unknown tool requested: {fn_name}"
                            tool_result_content = f"Tool '{fn_name}' does not exist. Available tools: web_search, fetch_page, calculator"

                    except Exception as exc:
                        # Tool errors MUST NOT crash the application
                        summary = f"Tool '{fn_name}' execution error: {str(exc)}"
                        tool_result_content = json.dumps({"success": False, "error": str(exc)})

                    # Broadcast tool_result event to frontend
                    yield AgentEvent(
                        type="tool_result",
                        step=step,
                        tool=fn_name,
                        result_summary=summary,
                        raw_result=raw_data,
                        discovered_urls=list(tool_ctx.discovered_urls),
                        fetched_urls=list(tool_ctx.fetched_urls),
                        message=summary,
                    )

                    # Append tool response message to conversation context
                    messages.append({
                        "role": "tool",
                        "content": tool_result_content,
                    })

                # Proceed to next ReAct loop step
                continue

            # CASE 2: No tool calls generated
            final_content = assistant_msg.get("content", "").strip()

            # If the model produced text right after web_search without fetching any page,
            # and we still have budget, prompt it to fetch the top discovered page.
            if len(tool_ctx.discovered_urls) > 0 and len(tool_ctx.fetched_urls) == 0 and step < self.max_steps:
                top_url = next(iter(tool_ctx.discovered_urls))
                yield AgentEvent(
                    type="step",
                    step=step,
                    message=f"Prompting agent to fetch source page {top_url} to satisfy citation requirement...",
                )
                messages.append(assistant_msg)
                messages.append({
                    "role": "user",
                    "content": f"Please call fetch_page on '{top_url}' to verify the content and satisfy the strict citation policy before giving your final answer.",
                })
                continue

            # If no URLs have been discovered yet (e.g. search returned 0 results) and the agent
            # is about to give up before reaching max steps, prompt it to reformulate and search again.
            if len(tool_ctx.discovered_urls) == 0 and step < self.max_steps and "can't find" in final_content.lower() or (len(tool_ctx.discovered_urls) == 0 and step == 1 and not tool_calls):
                yield AgentEvent(
                    type="step",
                    step=step,
                    message="Search returned no initial results. Prompting agent to reformulate query...",
                )
                messages.append(assistant_msg)
                messages.append({
                    "role": "user",
                    "content": "No relevant webpages were found with that query. Please reformulate your search query using different keywords and call web_search again.",
                })
                continue

            if final_content:
                final_answer = final_content
                break

        # If loop reached max steps without terminating with an answer, synthesize one
        if not final_answer:
            yield AgentEvent(
                type="step",
                step=self.max_steps,
                message="Research step budget reached. Synthesizing final answer from observations...",
            )
            messages.append({"role": "user", "content": SYNTHESIS_PROMPT})
            try:
                synth_response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.2, "num_predict": 1024},
                )
                final_answer = synth_response.get("message", {}).get("content", "").strip()
                p_tokens = getattr(synth_response, "prompt_eval_count", 0) or 0
                e_tokens = getattr(synth_response, "eval_count", 0) or 0
                total_prompt_tokens += p_tokens
                total_eval_tokens += e_tokens
            except Exception as e:
                final_answer = (
                    f"Research budget reached after {self.max_steps} steps. "
                    f"Successfully fetched {len(tool_ctx.fetched_urls)} sources, but synthesis encountered: {str(e)}"
                )

        # Strict Citation Rule Enforcement:
        # Cross-reference cited URLs strictly with tool_ctx.fetched_urls
        valid_citations = self._extract_citations_from_text(final_answer, tool_ctx.fetched_urls)

        # Broadcast final answer event
        yield AgentEvent(
            type="final",
            step=step_count,
            final_answer=final_answer,
            citations=valid_citations,
            fetched_urls=list(tool_ctx.fetched_urls),
            discovered_urls=list(tool_ctx.discovered_urls),
            token_usage={
                "prompt_tokens": total_prompt_tokens,
                "eval_tokens": total_eval_tokens,
                "total_tokens": total_prompt_tokens + total_eval_tokens,
            },
            message="Final research answer produced successfully.",
        )

        # Broadcast completion event
        yield AgentEvent(
            type="done",
            step=step_count,
            message=f"Research completed in {step_count} steps.",
            token_usage={
                "prompt_tokens": total_prompt_tokens,
                "eval_tokens": total_eval_tokens,
                "total_tokens": total_prompt_tokens + total_eval_tokens,
            },
        )
