# LinkedIn Jobs Application Assistant

Search LinkedIn job listings, save them in a local SQLite database, browse
saved jobs in a Gradio interface, and optionally apply to Easy Apply jobs.

## Setup

From the repository root, install the project and its dependencies:

```powershell
python -m pip install -e .
```

When you plan to use `--apply`, create a profile directory containing the
information you want used in applications. The loader reads `.txt`, `.md`, and
`.pdf` files recursively, in sorted path order. The default directory is
`career-profile` in the current working directory. You can specify another
directory with `--profile`.

## Run the job searcher

Run the module from the repository root. The command searches every combination
of the supplied job titles and locations, then imports the results into the
local database:

```powershell
python -m job_searcher.main --lu linkedin_username --lpwd linkedin_password --title "Data Engineer" "Software Engineer" --location "São Paulo, Brazil" "Germany" --limit 50
```

To apply to available unapplied Easy Apply jobs after all searches have been
imported, include `--apply`:

```powershell
python -m job_searcher.main --lu linkedin_username --lpwd linkedin_password --title "Data Engineer" --location "São Paulo, Brazil" --limit 50 --apply --profile C:\private\career-profile
```

### Command-line parameters

- `--lu` (**required**): LinkedIn username.
- `--lpwd` (**required**): LinkedIn password.
- `--title` (**required**): one or more job titles. Quote titles containing
  spaces.
- `--location` (**required**): one or more locations. Quote locations containing
  spaces. The search runs for every title/location combination.
- `--limit` (optional, default `50`): maximum jobs to collect for each
  title/location combination. Must be greater than zero.
- `--apply` (optional flag): after importing search results, apply to available
  unapplied Easy Apply jobs in the database.
- `--profile` (optional, default `career-profile`): directory containing the
  profile documents used when `--apply` is enabled. Supported formats are TXT,
  Markdown, and PDF.

To apply to one saved job by its LinkedIn job ID, run:

```powershell
python -m job_searcher.apply --lu linkedin_username --lpwd linkedin_password --job_id 12344345 --profile career-profile-path
```

The command reads the job from `jobs.db` and requires it to be an unapplied Easy
Apply job.

## Run the user interface

From the repository root, start the Gradio interface with:

```powershell
python -m job_searcher.ui
```

The interface reads `jobs.db` from the current working directory and creates
the database and `jobs` table if needed. Filter by job title, location, Easy
Apply, and Applied status. The table shows ten jobs per page; use **Previous**
and **Next** to navigate. LinkedIn and apply URLs are clickable.
