import pytest
from tools import safe_calculate, validate_url, normalize_url, generate_ddg_reformulations, ToolContext

def test_safe_calculate_basic_operations():
    # Addition, multiplication, parenthesis
    res = safe_calculate("25 * 4")
    assert res["success"] is True
    assert res["result"] == 100

    res = safe_calculate("(100 - 25) / 5")
    assert res["success"] is True
    assert res["result"] == 15

    res = safe_calculate("2 ** 8")
    assert res["success"] is True
    assert res["result"] == 256

    res = safe_calculate("-10 + 5")
    assert res["success"] is True
    assert res["result"] == -5

def test_safe_calculate_division_by_zero():
    res = safe_calculate("10 / 0")
    assert res["success"] is False
    assert "Division by zero" in res["error"]

def test_safe_calculate_blocks_unsafe_code():
    # Prevent arbitrary code execution, import, functions, variables
    res = safe_calculate("__import__('os').system('dir')")
    assert res["success"] is False
    assert "Invalid arithmetic expression" in res["error"]

    res = safe_calculate("eval('2+2')")
    assert res["success"] is False

    res = safe_calculate("open('secret.txt')")
    assert res["success"] is False

    res = safe_calculate("x + 5")
    assert res["success"] is False

def test_safe_calculate_power_limit():
    # Exponential bomb protection
    res = safe_calculate("2 ** 999999999")
    assert res["success"] is False
    assert "Exponent too large" in res["error"] or "overflow" in res["error"].lower()

def test_normalize_url():
    # Correct handling of raw, bracketed, or prefixed URLs from LLMs
    assert normalize_url("https://example.com") == "https://example.com"
    assert normalize_url("[https://example.com]") == "https://example.com"
    assert normalize_url("s: [https://example.com]") == "https://example.com"
    assert normalize_url("url: https://example.com/page?a=1") == "https://example.com/page?a=1"
    assert normalize_url("Source: <https://example.com/test>") == "https://example.com/test"
    assert normalize_url("   ") == ""

def test_validate_url_valid_and_invalid():
    # Valid URLs
    ok, err = validate_url("https://www.google.com")
    assert ok is True
    assert err is None

    ok, err = validate_url("http://example.org/article?id=123")
    assert ok is True
    assert err is None

    # Invalid schemes
    ok, err = validate_url("file:///etc/passwd")
    assert ok is False
    assert "Only HTTP and HTTPS" in err

    ok, err = validate_url("javascript:alert(1)")
    assert ok is False

    # SSRF: localhost and private IPs
    ok, err = validate_url("http://localhost:8000")
    assert ok is False
    assert "forbidden" in err

    ok, err = validate_url("http://127.0.0.1:11434/api/generate")
    assert ok is False
    assert "forbidden" in err

    ok, err = validate_url("http://192.168.1.1/admin")
    assert ok is False
    assert "forbidden" in err

    ok, err = validate_url("http://10.0.0.1")
    assert ok is False
    assert "forbidden" in err

def test_generate_ddg_reformulations():
    refs = generate_ddg_reformulations("What are the recent developments in LLM?")
    assert len(refs) <= 3
    assert refs[0] == "What are the recent developments in LLM?"
    # Should include conversational-stripped and expanded variants
    assert any("large language models" in r.lower() or "llm" in r.lower() for r in refs)

def test_tool_context_calculator():
    ctx = ToolContext()
    res = ctx.calculator("50 + 50")
    assert res["success"] is True
    assert res["result"] == 100

def test_tool_context_fetch_page_validation():
    ctx = ToolContext()
    res = ctx.fetch_page("http://localhost:9999")
    assert res["success"] is False
    assert "forbidden" in res["error"]

def test_tool_context_discovered_and_fetched_tracking():
    ctx = ToolContext()
    ctx.discovered_urls.add("https://example.com/test")
    assert "https://example.com/test" in ctx.discovered_urls
    assert "https://example.com/test" not in ctx.fetched_urls

def test_duckduckgo_web_search_live():
    ctx = ToolContext()
    res = ctx.web_search("What are the recent developments in LLM?", max_results=3)
    assert res["success"] is True
    assert res["count"] > 0
    assert len(res["results"]) > 0
    first = res["results"][0]
    assert "title" in first and first["title"]
    assert "url" in first and first["url"].startswith("http")
    assert "duckduckgo.com" not in first["url"]
