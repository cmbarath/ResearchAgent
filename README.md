# AI Research Agent — Custom ReAct Loop

A demo-ready, full-stack AI research application featuring a **handcrafted ReAct (Reasoning + Acting) agent loop** powered entirely by local **Ollama (`llama3.2:latest`)**.

Built without any high-level agent frameworks (no LangChain `AgentExecutor`, no LangGraph, no AutoGen, no CrewAI). Every tool selection, backend execution, observation return, and termination step is implemented explicitly in clean, interview-ready Python and TypeScript.

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│             Frontend: React + Vite + TS                │
│    (Tailwind CSS, Event Stream Reader, Live Feed)     │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/research (SSE)
                            ▼
┌────────────────────────────────────────────────────────┐
│              Backend: FastAPI + Uvicorn                │
│             Server-Sent Events (SSE) Stream            │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│              Custom Python ReAct Loop                  │
│       Explicit iteration control (MAX_STEPS = 8)       │
│        Token budget tracking (MAX_TOTAL_TOKENS = 6000) │
└───────────────────────────┬────────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
┌──────────────────────────────┐  ┌────────────────────────────────┐
│   Ollama Local LLM Service   │  │       Native Tool Calling      │
│     (llama3.2:latest)        │  │  1. web_search (DuckDuckGo)    │
│  Native Function Calling     │  │  2. fetch_page (httpx + bs4)   │
│                              │  │  3. calculator (safe AST)      │
└──────────────────────────────┘  └────────────────────────────────┘
```

---

## 2. Why the Custom Loop Exists

Many production and interview implementations rely on abstractions like LangChain's `AgentExecutor` or LangGraph. While convenient, those frameworks:
- Obscure the underlying prompt engineering, state transitions, and tool-call mechanics.
- Make it difficult to enforce bespoke safety policies, like strict citation gating.
- Add massive dependency trees and unpredictable exception flows.

In this project, the **ReAct loop is written manually** from scratch in [`backend/agent.py`](backend/agent.py):
1. **Explicit Step Budget**: Exactly bounded by `MAX_STEPS = 8`.
2. **Deterministic State Machine**: Messages and tool observations append explicitly to a transparent message buffer.
3. **Resilient Error Recovery**: Tool exceptions never crash the loop; structured error observations feed back to the LLM so it can recover or pick alternate tools.
4. **Strict Citation Filtering**: Citations are cryptographically and deterministically restricted to URLs actually retrieved with `fetch_page`.

---

## 3. The ReAct Flow

```text
User Question
      ↓
LLM receives Question + System Prompt + Tool Definitions
      ↓
LLM decides action: Call Tool vs Final Answer
      │
      ├───────────────────[ Tool Call ]───────────────────┐
      │                                                   │
      ▼                                                   ▼
Backend executes Tool safely               Stream 'tool_call' event via SSE
      │
      ▼
Tool Observation returned to LLM           Stream 'tool_result' event via SSE
      │
      ▼
LLM receives Observation & decides next action (Repeat, max 8 steps)
      │
      └──────────────────[ Final Answer ]─────────────────┐
                                                          │
                                                          ▼
Backend verifies citations against fetched URLs
                                                          ↓
Stream 'final' and 'done' events to Frontend
```

---

## 4. Built-In Security & Safety

- **Safe AST Calculator**:
  Arithmetic expressions are parsed into Python Abstract Syntax Trees (`ast.parse`) and evaluated against an explicit whitelist of mathematical operations (`+`, `-`, `*`, `/`, `//`, `%`, `**`).
  - **Zero use of `eval()` or `exec()`**.
  - Arbitrary code execution, imports, and variables are blocked.
  - Exponent overflow protection limits powers to prevent Denial of Service.
- **SSRF & URL Protection**:
  All URLs passed to `fetch_page` are validated before network requests:
  - Only `http://` and `https://` protocols permitted.
  - Loopback (`localhost`, `127.0.0.1`, `::1`), zero addresses, and RFC 1918 private IP subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) are blocked.
- **Page Sanitization & Content Truncation**:
  Extracted HTML is cleaned with BeautifulSoup by stripping scripts, styles, navigation, headers, footers, and forms, and truncated to `MAX_PAGE_CHARS = 4000` to prevent LLM context flooding.
- **Hard Step Limit (`MAX_STEPS = 8`)**:
  Prevents infinite tool invocation loops. If 8 steps elapse, the agent immediately synthesizes the best answer from gathered observations.
- **Token Budget (`MAX_TOTAL_TOKENS = 6000`)**:
  Cumulative token usage is tracked via Ollama evaluation metadata.
- **Strict Citation Policy**:
  The final answer may cite **ONLY** URLs that were successfully fetched and read via `fetch_page`. URLs merely returned in search snippets are never allowed as citations.

---

## 5. Server-Sent Events (SSE) Streaming

The frontend uses standard `fetch()` with `response.body.getReader()` to consume progressive events streamed from `POST /api/research`:

| Event Type | Description |
|------------|-------------|
| `step` | Indicates current iteration number (e.g. `Step 1/8: Analyzing question...`) |
| `tool_call` | Broadcasts tool selected by LLM (`tool`, `arguments`) |
| `tool_result` | Broadcasts tool execution summary and structured output |
| `error` | Broadcasts recoverable errors or warnings |
| `final` | Delivers the synthesized research report and verified citations list |
| `done` | Signals completion with token usage and duration metrics |

---

## 6. Prerequisites

- **Windows 10/11**
- **Python 3.12+**
- **Node.js v20+** and **npm**
- **Ollama** installed and running locally
- Ollama model: `llama3.2:latest` (or `ollama pull llama3.2`)

---

## 7. Setup & Run Instructions

### 1. Start Ollama (if not already running)
```powershell
ollama serve
ollama list
```
Verify `llama3.2:latest` is present.

### 2. Backend Setup & Launch
Open a PowerShell terminal:
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```
Backend will be live at `http://127.0.0.1:8000`.
Health check: `http://127.0.0.1:8000/api/health`.

### 3. Frontend Setup & Launch
Open a second PowerShell terminal:
```powershell
cd frontend
npm install
npm run dev
```
Frontend will be live at `http://localhost:5173`.

---

## 8. Running Backend Tests

Run the automated pytest test suite covering safe AST math, URL validation, citation filtering, and API endpoints:
```powershell
python -m pytest backend/test_tools.py backend/test_agent.py -o pythonpath=backend
```

---

## 9. Recommended Demo Scenarios

### Demo 1: Direct Arithmetic (Tool: `calculator`)
- **Query:** `What is 25 multiplied by 4?`
- **Expected:** Agent detects arithmetic, invokes `calculator` with `25 * 4`, receives `100`, and answers `100` within 2 steps.

### Demo 2: Real-World Web Research (Tools: `web_search` + `fetch_page`)
- **Query:** `What are the latest developments in AI coding agents?`
- **Expected:** Agent performs DuckDuckGo search, selects candidate URLs, fetches and reads full article contents with `fetch_page`, synthesizes a comprehensive report, and cites verified URLs.

### Demo 3: Error Recovery & Resilience
- **Query:** Enter a query referencing an unavailable site or invalid calculation.
- **Expected:** Backend catches the exception, converts it to structured error observation, and the agent adapts without crashing.
