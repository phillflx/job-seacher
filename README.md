# LinkedIn Jobs Application Assistant

A small Python CLI that searches LinkedIn's public job listings by title,
prints matching jobs and lets you open each listing for your own review.

## Setup

Create a private profile file, or a directory containing profile documents,
outside version control. PDF, TXT, and Markdown (`.md`) files are supported.
For a directory, files in subdirectories are included in sorted path order.
Include only facts you want used in application drafts, for example:

```markdown
## Experience
- Data Engineer at Example Co (2022–2025): built Python and SQL pipelines.

## Skills
- Python, SQL, dbt, Airflow

## Education
- B.S. in Computer Science
```

## Run Search

```powershell
python src/jobs_searcher/search.py "Data Engineer" "Software Engineer" "AI Engineer" --location "São Paulo, Brazil" --profile C:\private\career-profile.md --output jobs.json
```

Pass a directory to combine all supported profile files:

```powershell
python src/jobs_searcher/search.py "Data Engineer" --profile C:\private\career-profile --output jobs.json
```

Install the project dependencies to enable PDF text extraction (`pypdf`).

Keep LinkedIn URL support by passing the URL to `--profile`:

```powershell
python src/jobs_searcher/search.py "Data Engineer" --profile "https://www.linkedin.com/in/example/" --output jobs.json
```
