# El Compa — A Weather Chatbot

El Compa is a conversational weather assistant built for Assignment 2. Unlike a
grab-bag of unrelated services, all three required services here are tied together
by a single theme (weather), with a distinct persona layered on top: El Compa is a
warm, slightly dramatic weather enthusiast who treats the user like a close friend
("carnal"). The unifying thread is intentional — it's a stronger portfolio piece
than three unrelated demo services would be, at no added implementation cost.

## Services

### Service 1 — API Calls: `get_current_weather`

File: `tools_weather_check.py`

Calls [wttr.in](https://wttr.in) (`?format=j1`) for live conditions at a given
location and extracts the relevant fields from `current_condition[0]`
(temperature, feels-like, condition, humidity, wind speed, precipitation). The
tool returns a plain structured dict, not a formatted sentence — the required
"don't return the API output verbatim" transformation happens downstream, when
the LLM turns the dict into an in-character natural-language answer.

### Service 2 — Semantic Query: `search_weather_knowledge`

Files: `data/weather_knowledge.jsonl`, `ingest.py`, `tools_weather_knowledge.py`

**Dataset.** Rather than reusing the pre-built Pitchfork/music dataset from
class, this project uses a hand-curated set of 86 short (2–3 sentence) weather
facts, split across four categories: `history`, `phenomena`, `records`, and
`folklore`. Each entry was paraphrased from one of four public sources —
Wikipedia's [Timeline of meteorology](https://en.wikipedia.org/wiki/Timeline_of_meteorology)
and [List of weather records](https://en.wikipedia.org/wiki/List_of_weather_records),
[FactRetriever&#39;s weather facts](https://www.factretriever.com/weather-facts), and
the [Old Farmer&#39;s Almanac&#39;s weather proverbs](https://www.almanac.com/content/weather-proverbs-and-prognostics-rain-and-clouds)
— and stored with `category`, `keywords`, `source`, and `source_url` metadata.
The full dataset is under 50 KB, well within the 40 MB limit.

**Embedding process.** `ingest.py` reads `data/weather_knowledge.jsonl`, builds a
`chromadb.PersistentClient` collection at `chroma_store/` (file-persisted, no
Docker/server required — see "Deviations from the course sample" below), and
calls `collection.add()` with only the `text` field passed as `documents`; the
embedding function attached to the collection embeds each document
automatically at add time (no manual embedding-API calls or precomputed vectors
needed, since the dataset is small). This script only needs to be run once, or
whenever `weather_knowledge.jsonl` changes — the resulting `chroma_store/`
directory is committed to the repo so the collection can be queried directly
without re-running ingestion.

**Retrieval.** `search_weather_knowledge(query, category=None)` is a hybrid
search: `category` is an optional tool parameter the LLM fills in only when the
user's question clearly falls into one bucket (e.g. a "records" question), which
is applied as a metadata `where` filter *before* Chroma ranks the remaining
candidates by embedding similarity. This two-stage filter-then-rank approach is
noticeably more precise than semantic search alone — e.g. a query like "coldest
temperature ever recorded" without category filtering can surface topically
related but polarity-opposite results (a *hottest*-temperature record, because
both are "extreme temperature" facts in embedding space); adding the category
filter first removes that class of false positive.

### Service 3 — MCP: `get_weather_advice`

Files: `advice_mcp_server.py`, wired into `main.py`

A small [FastMCP](https://gofastmcp.com) server exposes `get_weather_advice`,
a rule-based tool (temperature thresholds + simple keyword checks on the
condition string) that turns a temperature/condition pair into clothing and
activity advice. It deliberately does *not* call an external API — it's a
distinct capability built on top of Service 1's data, not a re-exposure of it.
The chatbot's instructions require the model to call this tool whenever the
user asks what to wear or whether to go outside, rather than inventing advice
itself (verified by inspecting the LangGraph message trace and confirming the
final answer matches the tool's literal output).

The server runs over **stdio**, not HTTP: `main.py` uses
`langchain_mcp_adapters.MultiServerMCPClient` to spawn `advice_mcp_server.py` as
a subprocess and load its tools directly, rather than requiring a separately
started HTTP server (as `music_mcp`/`static_weather_mcp` do). This means the
whole app starts with a single command — no manual server startup, no ngrok
tunnel.

## User Interface

Built with `gr.ChatInterface` (`app.py`), `type="messages"`. The chat function
reconstructs the full LangChain message history from Gradio's `history` on every
call, so the assistant has access to the entire conversation each turn —
satisfying the "must maintain memory throughout the conversation" requirement.

**Context window management (optional, not implemented):** for very long
conversations, the natural next step would be trimming `state["messages"]`
before it reaches the model, using LangGraph/LangChain's
[`trim_messages`](https://docs.langchain.com/oss/python/langgraph/add-memory#manage-short-term-memory)
utility (e.g. keep the last N messages or cap by token count). This was left
unimplemented given the assignment's time constraints and its "optional"
status — the core, required memory behavior (full-history recall within a
normal-length conversation) is already in place and tested.

## Guardrails

Defined in `prompts.py`:

- **System prompt protection:** the model is instructed not to reveal or take
  instructions to override its own system prompt, with an in-character deflection
  line if asked directly.
- **Restricted topics:** cats/dogs, horoscopes/Zodiac signs, and Taylor Swift are
  all off-limits. Since none of this project's three services touch those
  topics, the guardrail is a straightforward in-character refusal-and-redirect,
  rather than the word-level euphemism approach used in the course's own sample
  (which needed that complexity because its services *were* about those exact
  topics).

## Deviations from the course sample (`course_chat`)

This project's `main.py`/`app.py` structure is adapted from `course_chat`, with
a few deliberate changes worth calling out since they diverge from the sample:

- **`chromadb.PersistentClient` instead of `HttpClient`.** The assignment
  requires file-persisted Chroma rather than the Docker-based server used in
  class, so no `docker compose up` step is needed to run this project.
- **Chat model routed through the API gateway.** `course_chat/main.py` calls
  `init_chat_model("openai:gpt-4o-mini")` unmodified, which reads a personal
  `OPENAI_API_KEY`. Since `.secrets.template` marks that key as optional
  ("if available") and only `API_GATEWAY_KEY` is guaranteed to be set, this
  project instead configures `init_chat_model` with the same gateway
  `base_url`/`default_headers` already used for embeddings, so it doesn't
  depend on a personal OpenAI key.
- **Async graph invocation.** Because the MCP-loaded tool only supports async
  execution, `main.py`/`app.py` call `graph.ainvoke(...)` (not `graph.invoke(...)`)
  and `app.py`'s chat function is `async def`, which Gradio's `ChatInterface`
  supports natively.

## Running the project

```bash
cd 05_src
python -m assignment_chat.ingest   # one-time: builds chroma_store/ from data/weather_knowledge.jsonl
python -m assignment_chat.app      # launches the Gradio chat interface
```
