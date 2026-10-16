"""
Creates a JobSearch Object which scrapes linkedin job search and returns a job list
it uses SessionManager to interact with linkedin
"""

from dataclasses import asdict, dataclass

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    listed: str = ""
    description: str = ""
    easy_apply: bool
    apply_url: str
    applied: bool