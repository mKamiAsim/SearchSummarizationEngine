# Search Summarization Engine

An extensible research pipeline built with LangChain and LCEL. It turns a natural-language question into targeted web searches, source summaries, and a cited Markdown report. The default configuration targets a local LM Studio OpenAI-compatible endpoint, while any compatible OpenAI API can be configured through environment variables.

## Architecture

```text
User question
	|
	v
ResearchOrchestrator
	|-- 1. Assistant selection       -> AssistantPersona
	|-- 2. Query generation           -> SearchQueryGeneration
	|-- 3. Web search                 -> SearchResult[]
	|-- 4. Scrape + summarize         -> ScrapedContent[] -> SummarizedResult[]
	|-- 5. Report compilation         -> ResearchReport
	`-- optional Markdown persistence -> reports/
```

`src/orchestrator.py` owns the workflow and records intermediate values in `PipelineState`. Each LLM stage is implemented as an LCEL chain:

```text
YAML PromptTemplate | ChatOpenAI | RobustPydanticParser
```

Prompt files live in `src/prompts/`; Pydantic models in `src/core/models.py` define the contracts between stages. `src/utils/web_searching.py` and `src/utils/web_scraping.py` isolate external web access, making those boundaries straightforward to mock in tests.

## Installation

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Configuration

Copy the values below into `.env` and adjust them for your provider:

```dotenv
OPENAI_API_KEY=lm-studio
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_MODEL_NAME=qwen/qwen3.5-4b
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=12288
```

Settings are defined and validated in `src/config/settings.py`. Environment variables override defaults. The API base is normalized to end in `/v1`; the default local setup does not require a cloud key.

## LangSmith Observability

Tracing is disabled by default. To enable LangSmith, add the following to `.env`:

```dotenv
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=search-summarization-engine
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

`ResearchOrchestrator` configures these standard LangChain variables before creating chains. This captures the pipeline's LLM and runnable traces in the selected LangSmith project without changing application behavior. Keep the API key in a local, uncommitted `.env` file.

## Usage

CLI:

```powershell
research-engine "What are the latest developments in quantum computing?"
```

Python:

```python
from src.orchestrator import ResearchOrchestrator

report = ResearchOrchestrator().run(
	"What are the latest developments in quantum computing?",
	save_to_file="reports/quantum_computing.md",
)
print(report.report_content)
```

## Testing and Quality Checks

```powershell
python -m pytest -o addopts="" tests
ruff check src tests
mypy src tests
python -c "import src; print(src.__version__)"
```

The test suite currently focuses on structured-output parsing. Web access and LLM calls should be covered with mocked integration tests as the pipeline evolves.

## Project Layout

```text
src/
  orchestrator.py             Pipeline and CLI entry point
  chains/                     Five-stage LLM chain implementations
  config/settings.py          Validated environment-backed configuration
  core/models.py              Pydantic pipeline contracts
  core/llm_factory.py         Shared ChatOpenAI factory
  core/observability.py       LangSmith environment configuration
  prompts/                    YAML prompt templates
  utils/                      Logging, web search, scraping, and parsers
tests/                         Automated tests
reports/                       Example and generated reports
```

## Error Handling and Security

The orchestrator wraps pipeline failures in `RuntimeError` while retaining the original exception as its cause. External content is treated as untrusted input and should not be given additional privileges. Credentials belong in environment variables and are intentionally masked by the settings string representation; do not place them in prompts, logs, or reports.
