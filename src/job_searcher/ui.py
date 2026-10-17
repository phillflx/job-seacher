"""Gradio interface for browsing jobs stored in SQLite."""

import html
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import gradio as gr

from .job import create_jobs_table

PAGE_SIZE = 10
TABLE_COLUMNS = [
    "Job ID",
    "Title",
    "Company",
    "Location",
    "Date posted",
    "Easy apply",
    "Applied",
    "LinkedIn URL",
    "Apply URL",
]


def get_jobs_page(
    database_path: str | Path,
    job_title: str = "",
    location: str = "",
    easy_apply: str = "Any",
    applied: str = "Any",
    page: int = 0,
) -> tuple[list[list[Any]], int, int]:
    """Return one filtered page of jobs and pagination totals."""
    clauses: list[str] = []
    parameters: list[Any] = []

    if job_title.strip():
        clauses.append("LOWER(title) LIKE LOWER(?)")
        parameters.append(f"%{job_title.strip()}%")
    if location.strip():
        clauses.append("LOWER(location) LIKE LOWER(?)")
        parameters.append(f"%{location.strip()}%")
    if easy_apply == "Yes":
        clauses.append("easy_apply = 1")
    elif easy_apply == "No":
        clauses.append("easy_apply = 0")
    if applied == "Yes":
        clauses.append("applied = 1")
    elif applied == "No":
        clauses.append("applied = 0")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    columns = (
        "job_id, title, company, location, date_posted, easy_apply, applied, "
        "linkedin_url, apply_url"
    )

    with sqlite3.connect(database_path) as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM jobs {where_sql}", parameters
        ).fetchone()[0]
        page_count = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(page, 0), page_count - 1)
        rows = connection.execute(
            f"SELECT {columns} FROM jobs {where_sql} "
            "ORDER BY rowid DESC LIMIT ? OFFSET ?",
            [*parameters, PAGE_SIZE, page * PAGE_SIZE],
        ).fetchall()

    formatted = [
        [
            job_id, title, company, location, date_posted,
            "Yes" if easy else "No", "Yes" if applied else "No",
            linkedin_url, apply_url,
        ]
        for job_id, title, company, location, date_posted, easy, applied, linkedin_url, apply_url in rows
    ]
    return formatted, total, page


def _render_jobs_table(rows: list[list[Any]]) -> str:
    """Render the current page as an HTML table with safe clickable URLs."""
    headers = "".join(f"<th>{html.escape(column)}</th>" for column in TABLE_COLUMNS)
    body_rows = []
    for job_id, title, company, location, date_posted, easy_apply, applied, linkedin_url, apply_url in rows:
        cells = [job_id, title, company, location, date_posted, easy_apply, applied]
        rendered_cells = [f"<td>{html.escape(str(value or ''))}</td>" for value in cells]
        for url in (linkedin_url, apply_url):
            safe_url = str(url or "").strip()
            scheme = urlsplit(safe_url).scheme.lower()
            if scheme in {"http", "https"}:
                escaped_url = html.escape(safe_url, quote=True)
                rendered_cells.append(
                    f'<td><a href="{escaped_url}" target="_blank" '
                    f'rel="noopener noreferrer">Open link</a></td>'
                )
            else:
                rendered_cells.append("<td></td>")
        body_rows.append(f"<tr>{''.join(rendered_cells)}</tr>")

    table = (
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">'
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
    )
    return table


def create_app(database_path: str | Path = "jobs.db") -> gr.Blocks:
    """Build the paginated job browser for the selected SQLite database."""
    database_path = Path(database_path)
    create_jobs_table(database_path)

    def refresh(job_title: str, location: str, easy_apply: str, applied: str, page: int):
        rows, total, page = get_jobs_page(
            database_path, job_title, location, easy_apply, applied, page
        )
        page_count = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        message = (
            f"Page {page + 1} of {page_count} | {total} job(s)"
            if total
            else "No jobs match these filters."
        )
        return (
            _render_jobs_table(rows),
            page,
            message,
            gr.update(interactive=page > 0),
            gr.update(interactive=page < page_count - 1),
        )

    def change_page(
        delta: int, job_title: str, location: str, easy_apply: str, applied: str, page: int
    ):
        return refresh(job_title, location, easy_apply, applied, page + delta)

    with gr.Blocks(title="Saved jobs") as app:
        gr.Markdown("# Saved jobs\nBrowse and filter jobs stored in the SQLite database.")
        page_state = gr.State(0)

        with gr.Row():
            title_filter = gr.Textbox(label="Job title", placeholder="Filter by title")
            location_filter = gr.Textbox(label="Location", placeholder="Filter by location")
            easy_filter = gr.Dropdown(
                choices=["Any", "Yes", "No"], value="Any", label="Easy apply"
            )
            applied_filter = gr.Dropdown(
                choices=["Any", "Yes", "No"], value="Any", label="Applied"
            )

        jobs_table = gr.HTML(
            value=_render_jobs_table([]),
            label="Jobs",
        )
        with gr.Row():
            previous_button = gr.Button("Previous", interactive=False)
            page_status = gr.Markdown()
            next_button = gr.Button("Next")

        outputs = [jobs_table, page_state, page_status, previous_button, next_button]
        filters = [title_filter, location_filter, easy_filter, applied_filter]
        for component in filters:
            component.change(
                lambda title, location, easy, applied: refresh(
                    title, location, easy, applied, 0
                ),
                inputs=filters,
                outputs=outputs,
            )
        previous_button.click(
            lambda title, location, easy, applied, page: change_page(
                -1, title, location, easy, applied, page
            ),
            inputs=[*filters, page_state],
            outputs=outputs,
        )
        next_button.click(
            lambda title, location, easy, applied, page: change_page(
                1, title, location, easy, applied, page
            ),
            inputs=[*filters, page_state],
            outputs=outputs,
        )
        app.load(
            lambda: refresh("", "", "Any", "Any", 0),
            outputs=outputs,
        )

    return app


def main() -> None:
    create_app().launch()


if __name__ == "__main__":
    main()
