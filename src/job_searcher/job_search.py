"""Search LinkedIn job listings using an authenticated Selenium session."""

from dataclasses import dataclass
import re
from time import sleep
from urllib.parse import urlencode
import traceback

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .fields_searcher import FieldsSearcher
from .session_manager import SessionManager

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search-results/"
LINKEDIN_JOB_VIEW_URL = "https://www.linkedin.com/jobs/view/"
JOBS_CONTAINER_SELECTOR = '[componentkey="SearchResultsMainContent"]'
JOB_LINK_SELECTOR = '[componentkey^="job-card-component-ref-"]'
JOB_DETAILS_CONTAINER_SELECTOR = '[data-sdui-screen="com.linkedin.sdui.flagshipnav.jobs.SemanticJobDetails"]'
APPLY_BUTTON_SELECTORS = (
    'button.jobs-apply-button',
    'a.jobs-apply-button',
    '[data-job-id] button[aria-label*="Apply"]',
    'button[aria-label*="Apply"]',
    'a[aria-label*="Apply"]',
)


@dataclass
class Job:
    job_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    linkedin_url: str = ""
    listed: str = ""
    date_posted: str = ""
    description: str = ""
    easy_apply: bool = False
    apply_url: str = ""
    applied: bool = False


class JobSearch:
    """Scrape job cards and their detail panes from LinkedIn."""

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.driver = session_manager.driver
        self.fields_searcher: FieldsSearcher = FieldsSearcher()

    def search(self, job_title: str, limit: int) -> list[Job]:
        """Search LinkedIn for *job_title* and return up to *limit* jobs."""
        if limit <= 0:
            return []

        self.driver.get(f"{LINKEDIN_SEARCH_URL}?{urlencode({'keywords': job_title})}")
        wait = WebDriverWait(self.driver, 15)
        container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, JOBS_CONTAINER_SELECTOR))
        )
        self._scroll_to_end(container)
        links = self.driver.find_elements(By.CSS_SELECTOR, JOB_LINK_SELECTOR)

        jobs: list[Job] = []
        last_job_id = None
        for index in range(len(links)):
            # Re-query on every iteration because selecting a card replaces its DOM node.
            cards = self.driver.find_elements(By.CSS_SELECTOR, JOB_LINK_SELECTOR)
            if index >= len(cards) or len(jobs) >= limit:
                break

            card = cards[index]
            card_url = card.get_attribute("href") or ""
            job_id = self._get_job_id(card, card_url)
            if job_id == last_job_id:
                continue

            try:
                card.click()
                job = self._read_selected_job(wait, card_url, job_id)
                jobs.append(job)
            except Exception:
                traceback.print_exc()
                continue

            last_job_id = job_id
        return jobs

    def _scroll_to_end(self, container) -> None:
        """Scroll the results pane until its content stops growing."""
        previous_height = -1
        stable_rounds = 0
        while stable_rounds < 3:
            try:
                height = self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight; "
                    "return arguments[0].scrollHeight;",
                    container,
                )
            except StaleElementReferenceException:
                container = self.driver.find_element(By.CSS_SELECTOR, JOBS_CONTAINER_SELECTOR)
                continue
            sleep(0.6)
            if height == previous_height:
                stable_rounds += 1
            else:
                stable_rounds = 0
                previous_height = height

    def _read_selected_job(self, wait: WebDriverWait, card_url: str, job_id: str = "") -> Job:
        apply_button = self._wait_for_apply_button(wait)
        apply_url = (apply_button.get_attribute("href") or "").strip()
        button_text = " ".join(
            filter(None, (apply_button.text, apply_button.get_attribute("aria-label")))
        ).lower()

        extracted = self.fields_searcher.get_fields_from_text(
            self._selected_job_text(card_url, job_id),
            ["title", "company", "location", "date_posted", "description"],
        )
        linkedin_url = f"{LINKEDIN_JOB_VIEW_URL}{job_id}/"
        date_posted = extracted.get("date_posted") or ""

        return Job(
            job_id=job_id,
            title=str(extracted.get("title") or ""),
            company=str(extracted.get("company") or ""),
            location=str(extracted.get("location") or ""),
            linkedin_url=linkedin_url,
            listed=str(date_posted),
            date_posted=str(date_posted),
            description=str(extracted.get("description") or ""),
            easy_apply="easy" in button_text,
            apply_url=apply_url,
        )

    def _selected_job_text(self, card_url: str, job_id: str) -> str:
        return self.driver.find_elements(By.CSS_SELECTOR, JOB_DETAILS_CONTAINER_SELECTOR)[0].text

    @staticmethod
    def _get_job_id(card, card_url: str) -> str:
        for attribute in ("data-job-id", "componentkey"):
            value = card.get_attribute(attribute) or ""
            match = re.search(r"(\d{6,})", value)
            if match:
                return match.group(1)
        match = re.search(r"/jobs/view/(\d+)", card_url)
        return match.group(1) if match else ""

    def _wait_for_apply_button(self, wait: WebDriverWait):
        def find_button(driver):
            for selector in APPLY_BUTTON_SELECTORS:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    return buttons[0]
            return False

        try:
            return wait.until(find_button)
        except TimeoutException:
            # Keep the selected listing in the result if LinkedIn omits its apply control.
            return _EmptyElement()

    def _text_first(self, selectors: tuple[str, ...]) -> str:
        for selector in selectors:
            for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                try:
                    text = element.text.strip()
                    if text:
                        return text
                except StaleElementReferenceException:
                    continue
        return ""


class _EmptyElement:
    """Fallback for listings without an apply button."""

    text = ""

    @staticmethod
    def get_attribute(_name: str) -> str:
        return ""


def main() -> None:
    print("JobSearch is a library component; create it with a SessionManager instance.")
