# AGENTS.md

## Project overview

This repository is a Python package that searches LinkedIn jobs with Selenium, stores job records in SQLite, displays saved jobs in Gradio, and can assist with Easy Apply forms using an LLM-backed field extractor.

## Tech stack

- Python 3.12 or newer, with a `src/` package layout (`src/job_searcher`).
- `uv` project/build configuration (`pyproject.toml` and `uv.lock`); dependencies are declared in `pyproject.toml`.
- Selenium 4 with Chrome WebDriver for LinkedIn browsing and form interaction.
- SQLite for local persistence in `jobs.db`.
- Gradio 5 or newer for the jobs browser UI.
- OpenAI Python client for structured LLM extraction; the current field-searcher configuration uses the OpenAI-compatible Ollama endpoint at `http://localhost:11434/v1` and defaults to `qwen2.5-coder`.
- `python-dotenv` for loading environment configuration, and `pypdf` for PDF profile text extraction.

## Project conventions

- Keep application code in `src/job_searcher/` and use package-relative imports (for example, `from .job import Job`). Run modules from the repository root with `python -m job_searcher.<module>` after installing the project.
- Follow the existing style: four-space indentation, descriptive names, type hints on public interfaces, concise module/class/function docstrings, and standard-library imports before third-party imports and local imports.
- Keep job data represented by the `Job` dataclass in `job.py`; add persisted fields consistently to the dataclass, `JOB_COLUMNS`, and SQLite schema.
- Keep database access in the job repository/importer layer. Use SQLite parameter placeholders for values, context managers for connections/transactions, and create the `jobs` table when initializing database-backed components.
- Use module-level `logging.getLogger(__name__)` for operational logs. Use parameterized logging calls (`logger.info("... %s", value)`) instead of eagerly formatting strings.
- Keep LinkedIn browser interactions behind `SessionManager` and the search/apply classes. Reuse their existing Selenium wait and selector patterns.
- Keep profile inputs as a directory of `.txt`, `.md`, and `.pdf` files. Do not put credentials or API keys in source code or documentation; supply them through command-line arguments or environment configuration as appropriate.
- There is no formatter, linter, or test runner configured in `pyproject.toml`. Preserve nearby formatting and avoid adding tooling assumptions without updating project configuration.

## Install and run

From the repository root, install the package and dependencies:

```powershell
python -m pip install -e .
```

Search one or more job titles across one or more locations (all title/location combinations are searched):

```powershell
python -m job_searcher.main --lu <linkedin_username> --lpwd <linkedin_password> --title "Data Engineer" "Software Engineer" --location "São Paulo, Brazil" "Germany" --limit 50
```

CLI parameters:

- `--lu`: required LinkedIn username.
- `--lpwd`: required LinkedIn password.
- `--title`: one or more required job titles; quote values containing spaces.
- `--location`: one or more required locations; quote values containing spaces.
- `--limit`: maximum results per title/location search; defaults to `50` and must be positive.
- `--apply`: after importing all search results, apply to stored unapplied Easy Apply jobs.
- `--profile`: profile directory for application form answers; defaults to `career-profile`. The directory is read recursively for TXT, Markdown, and PDF files. It is used when `--apply` is enabled.

To include application submissions, prepare the profile directory and add `--apply`:

```powershell
python -m job_searcher.main --lu <linkedin_username> --lpwd <linkedin_password> --title "Data Engineer" --location "São Paulo, Brazil" --limit 50 --apply --profile career-profile
```

Launch the Gradio interface from the repository root:

```powershell
python -m job_searcher.ui
```

The interface reads `jobs.db` in the current working directory, creates its table if needed, and provides paginated job browsing with title, location, Easy Apply, and Applied filters.
