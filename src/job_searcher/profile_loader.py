"""Load profile text from a directory of TXT, Markdown, and PDF files."""

from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def load_profile(path: str) -> str:
    """Read supported files in *path* and return their labeled contents.

    Files are searched recursively and concatenated in sorted relative-path
    order. Text files are decoded as UTF-8, replacing malformed byte sequences.
    """
    directory = Path(path)
    if not directory.is_dir():
        raise NotADirectoryError(f"Profile path is not a directory: {directory}")

    profile_sections: list[str] = []
    files = sorted(
        (
            file_path
            for file_path in directory.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda file_path: str(file_path.relative_to(directory)).casefold(),
    )

    for file_path in files:
        if file_path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)
            file_content = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            file_content = file_path.read_text(encoding="utf-8", errors="replace")

        profile_sections.append(
            f"------ {file_path.name} ------\n\n{file_content}\n\n"
        )

    return "".join(profile_sections)
