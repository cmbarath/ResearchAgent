import ast
import ipaddress
import operator
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs.http_client import HttpClient

from config import settings

# ---------------------------------------------------------
# Safe AST Calculator Implementation
# ---------------------------------------------------------

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_ast_node(node: ast.AST) -> float | int:
    """Recursively evaluates safe mathematical AST nodes."""
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Constant of type {type(node.value).__name__} is not allowed")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            operand = _eval_ast_node(node.operand)
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = _eval_ast_node(node.left)
            right = _eval_ast_node(node.right)

            # Prevent exponential Denial of Service
            if op_type is ast.Pow:
                if isinstance(right, (int, float)) and abs(right) > 500:
                    raise ValueError("Exponent too large (max allowed: 500)")
                if isinstance(left, (int, float)) and abs(left) > 10000 and right > 10:
                    raise ValueError("Calculation exceeds safe magnitude")

            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero")

            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

    raise ValueError(f"Disallowed expression node: {type(node).__name__}")


def safe_calculate(expression: str) -> Dict[str, Any]:
    """Safely calculates the result of an arithmetic expression without eval()."""
    clean_expr = expression.strip()
    if not clean_expr:
        return {"success": False, "error": "Expression is empty"}

    try:
        parsed = ast.parse(clean_expr, mode="eval")
        result = _eval_ast_node(parsed)
        # Format clean int if whole number
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return {
            "success": True,
            "expression": clean_expr,
            "result": result,
            "display": str(result),
        }
    except ZeroDivisionError:
        return {"success": False, "error": "Division by zero"}
    except (SyntaxError, ValueError, TypeError) as e:
        return {"success": False, "error": f"Invalid arithmetic expression: {str(e)}"}
    except OverflowError:
        return {"success": False, "error": "Arithmetic overflow: number too large"}
    except Exception as e:
        return {"success": False, "error": f"Calculator error: {str(e)}"}


# ---------------------------------------------------------
# URL Normalization & SSRF Prevention
# ---------------------------------------------------------

PRIVATE_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def normalize_url(url: str) -> str:
    """Normalizes and extracts clean http/https URL string from LLM inputs.
    
    Handles artifacts such as '[https://...]', 'url: https://...', 's: [https://...]'.
    """
    if not url or not isinstance(url, str):
        return ""
    u = url.strip().strip("\"'`<>[]()")
    if u.lower().startswith("url:"):
        u = u[4:].strip()
    if u.lower().startswith("s:"):
        u = u[2:].strip()
    u = u.strip("\"'`<>[]()")
    m = re.search(r"https?://[^\s)\]\"'>]+", u)
    if m:
        return m.group(0).rstrip(".,;:)")
    return u


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """Validates that a URL is well-formed http/https and prevents SSRF."""
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    url = normalize_url(url)
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Failed to parse URL"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are permitted"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing valid hostname"

    # Check for localhost variations
    if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return False, "Access to localhost/internal addresses is forbidden"

    # Check if hostname is an IP address in private ranges
    try:
        ip = ipaddress.ip_address(hostname)
        for net in PRIVATE_IP_RANGES:
            if ip in net:
                return False, f"Access to private/local network ({ip}) is forbidden"
    except ValueError:
        # Hostname is a domain name, which is normal
        pass

    return True, None


# ---------------------------------------------------------
# Query Reformulation Helper (DuckDuckGo only)
# ---------------------------------------------------------

def generate_ddg_reformulations(query: str) -> List[str]:
    """Generates up to 3 bounded search queries for zero/weak search results."""
    candidates = [query.strip()]

    # Attempt 2: Strip conversational filler and punctuation
    cleaned = re.sub(
        r"^(what\s+are\s+the|what\s+is\s+the|tell\s+me\s+about|find\s+|search\s+for|can\s+you\s+explain|give\s+me)\s+",
        "",
        query,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[?!.,;:]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned and cleaned.lower() != query.strip().lower() and cleaned not in candidates:
        candidates.append(cleaned)

    # Attempt 3: Specific research-oriented expansion
    if "llm" in cleaned.lower():
        expanded = re.sub(r"\bllm\b", "large language models", cleaned, flags=re.IGNORECASE)
        if expanded not in candidates:
            candidates.append(expanded)
    else:
        research_variant = f"{cleaned} research overview".strip()
        if research_variant not in candidates:
            candidates.append(research_variant)

    return candidates[:3]


# ---------------------------------------------------------
# Tool Registry & Execution Context
# ---------------------------------------------------------

class ToolContext:
    """Manages the state of URL discovery, fetches, and tools for a single agent session."""

    def __init__(self):
        self.discovered_urls: Set[str] = set()
        self.fetched_urls: Set[str] = set()
        self.url_metadata: Dict[str, Dict[str, Any]] = {}

    def _execute_duckduckgo_query(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Executes search strictly against DuckDuckGo HTML & Lite endpoints."""
        hc = HttpClient(timeout=10)
        # Attempt DuckDuckGo HTML endpoint
        resp = hc.get("https://html.duckduckgo.com/html/", params={"q": query})
        if resp.status_code != 200:
            # Fallback to DuckDuckGo Lite endpoint
            resp = hc.get("https://lite.duckduckgo.com/lite/", params={"q": query})

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen_urls = set()

        # Parse standard DuckDuckGo HTML items
        items = soup.find_all("div", class_="result")
        if items:
            for result in items:
                title_tag = result.find("a", class_="result__a")
                snippet_tag = result.find("a", class_="result__snippet")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                raw_href = title_tag.get("href", "")
                if "uddg=" in raw_href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                    if "uddg" in parsed:
                        raw_href = parsed["uddg"][0]
                url = normalize_url(raw_href)
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                # Result validation
                if not url or not url.startswith(("http://", "https://")):
                    continue
                if "duckduckgo.com" in url or url in seen_urls:
                    continue
                if not title:
                    continue

                seen_urls.add(url)
                results.append({"title": title, "url": url, "snippet": snippet})
                if len(results) >= max_results:
                    break

        # Fallback to DuckDuckGo Lite table format if HTML items empty
        if not results:
            links = soup.find_all("a", class_="result-link")
            for link in links:
                title = link.get_text(strip=True)
                raw_href = link.get("href", "")
                if "uddg=" in raw_href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                    if "uddg" in parsed:
                        raw_href = parsed["uddg"][0]
                url = normalize_url(raw_href)

                if not url or not url.startswith(("http://", "https://")):
                    continue
                if "duckduckgo.com" in url or url in seen_urls:
                    continue
                if not title:
                    continue

                seen_urls.add(url)
                snippet = ""
                tr = link.find_parent("tr")
                if tr:
                    next_tr = tr.find_next_sibling("tr")
                    if next_tr:
                        snippet = next_tr.get_text(strip=True)
                results.append({"title": title, "url": url, "snippet": snippet})
                if len(results) >= max_results:
                    break

        return results

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web for relevant information using DuckDuckGo only.
        
        If initial search yields 0 results, performs bounded query reformulation (max 3 attempts).
        
        Args:
            query: The search keywords or research question.
            max_results: Maximum number of search results to return (default: 5).
        """
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Search query cannot be empty",
                "results": [],
            }

        max_results = min(max(1, int(max_results)), 10)
        query = query.strip()
        reformulations = generate_ddg_reformulations(query)

        structured_results: List[Dict[str, str]] = []
        effective_query = query
        attempts_used = 0

        try:
            for attempt, q_variant in enumerate(reformulations, 1):
                attempts_used = attempt
                effective_query = q_variant
                raw_results = self._execute_duckduckgo_query(q_variant, max_results=max_results)

                if raw_results:
                    structured_results = raw_results
                    break

            for item in structured_results:
                url = item["url"]
                self.discovered_urls.add(url)
                self.url_metadata[url] = {
                    "title": item["title"],
                    "snippet": item["snippet"],
                }

            if structured_results:
                if attempts_used > 1:
                    summary = f"DuckDuckGo found {len(structured_results)} results after reformulating to '{effective_query}' (attempt {attempts_used}/3)."
                else:
                    summary = f"DuckDuckGo found {len(structured_results)} relevant search results for '{query}'."
            else:
                summary = f"DuckDuckGo search returned 0 useful results after {attempts_used} attempts for '{query}'."

            return {
                "success": True,
                "query": query,
                "effective_query": effective_query,
                "attempts_used": attempts_used,
                "count": len(structured_results),
                "summary": summary,
                "results": structured_results,
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": f"DuckDuckGo search execution failed: {str(e)}",
                "results": [],
            }

    def fetch_page(self, url: str) -> Dict[str, Any]:
        """Fetch and clean the contents of a webpage.
        
        Args:
            url: The HTTP or HTTPS URL to fetch.
        """
        if not url:
            return {"success": False, "error": "URL cannot be empty"}

        # Normalize URL to strip LLM artifacts like '[https://...]' or 's: [https://...]'
        url = normalize_url(url)
        is_valid, err = validate_url(url)
        if not is_valid:
            return {
                "success": False,
                "url": url,
                "error": f"URL validation failed: {err}",
            }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 ResearchAgent/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(
                timeout=settings.PAGE_FETCH_TIMEOUT,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(url)

            if response.status_code >= 400:
                return {
                    "success": False,
                    "url": url,
                    "error": f"HTTP {response.status_code}: {response.reason_phrase}",
                }

            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {
                    "success": False,
                    "url": url,
                    "error": f"Unsupported content type: {content_type}",
                }

            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract title before decomposing
            page_title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
            if not page_title and url in self.url_metadata:
                page_title = self.url_metadata[url].get("title", "")

            # Strip unnecessary noise elements
            for tag in soup([
                "script", "style", "nav", "footer", "header",
                "noscript", "aside", "form", "svg", "iframe", "button"
            ]):
                tag.decompose()

            # Clean and normalize readable text
            text_chunks = [s.strip() for s in soup.stripped_strings if len(s.strip()) > 0]
            clean_text = " ".join(text_chunks)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            if not clean_text:
                return {
                    "success": False,
                    "url": url,
                    "error": "Extracted page content was empty or unreadable",
                }

            # Enforce max page characters budget
            truncated = False
            if len(clean_text) > settings.MAX_PAGE_CHARS:
                clean_text = clean_text[:settings.MAX_PAGE_CHARS] + "... [truncated for length]"
                truncated = True

            # Register as successfully fetched URL
            self.fetched_urls.add(url)
            self.url_metadata[url] = {
                "title": page_title or url,
                "content_preview": clean_text[:200],
            }

            return {
                "success": True,
                "url": url,
                "title": page_title,
                "content": clean_text,
                "length": len(clean_text),
                "truncated": truncated,
                "summary": f"Page fetched successfully ({len(clean_text)} chars): {page_title or url}",
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "url": url,
                "error": f"Page request timed out after {settings.PAGE_FETCH_TIMEOUT}s",
            }
        except httpx.ConnectError:
            return {
                "success": False,
                "url": url,
                "error": "Failed to connect to host (connection refused or DNS error)",
            }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "url": url,
                "error": f"HTTP network error: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": f"Error processing page: {str(e)}",
            }

    def calculator(self, expression: str) -> Dict[str, Any]:
        """Perform arithmetic calculation safely.
        
        Args:
            expression: The arithmetic expression to evaluate, e.g. '25 * 4' or '(100 - 30) / 2'.
        """
        return safe_calculate(expression)


# ---------------------------------------------------------
# Tool Definitions for Ollama API
# ---------------------------------------------------------

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo to discover relevant URLs, titles, and snippets. Use this to find sources when answering external or current questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query keywords",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (default: 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch and clean text content from a web URL discovered during web_search. Only pages fetched with this tool are eligible to be cited in the final answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full HTTP/HTTPS URL of the page to fetch and read",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Safely evaluate an arithmetic math expression (e.g. '25 * 4', '(100 + 50) / 2', '2 ** 8'). Supports +, -, *, /, //, %, **.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]
