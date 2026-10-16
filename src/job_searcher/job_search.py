"""Search LinkedIn job listings using an authenticated Selenium session."""

from dataclasses import dataclass
from time import sleep
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from .session_manager import SessionManager

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search-results/"
JOBS_CONTAINER_SELECTOR = '[componentkey="SearchResultsMainContent"]'
JOB_LINK_SELECTOR = '[componentkey^="job-card-component-ref-"]'
APPLY_BUTTON_SELECTORS = (
    'button.jobs-apply-button',
    'a.jobs-apply-button',
    '[data-job-id] button[aria-label*="Apply"]',
    'button[aria-label*="Apply"]',
    'a[aria-label*="Apply"]',
)


@dataclass
class Job:
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    listed: str = ""
    description: str = ""
    easy_apply: bool = False
    apply_url: str = ""
    applied: bool = False


class JobSearch:
    """Scrape job cards and their detail panes from LinkedIn."""

    def __init__(self, session_manager: "SessionManager") -> None:
        self.session_manager = session_manager
        self.driver = session_manager.driver

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
        links = self.driver.find_elements(By.CSS_SELECTOR, JOB_LINK_SELECTOR)[:limit]

        jobs: list[Job] = []
        for index in range(len(links)):
            # Re-query on every iteration because selecting a card replaces its DOM node.
            cards = self.driver.find_elements(By.CSS_SELECTOR, JOB_LINK_SELECTOR)
            if index >= len(cards):
                break
            card = cards[index]
            card_url = card.get_attribute("href") or ""
            try:
                card.click()
            except StaleElementReferenceException:
                cards = self.driver.find_elements(By.CSS_SELECTOR, JOB_LINK_SELECTOR)
                if index >= len(cards):
                    continue
                card = cards[index]
                card_url = card.get_attribute("href") or card_url
                card.click()

            jobs.append(self._read_selected_job(wait, card_url))
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

    def _read_selected_job(self, wait: WebDriverWait, card_url: str) -> Job:
        apply_button = self._wait_for_apply_button(wait)
        apply_url = (apply_button.get_attribute("href") or "").strip()
        button_text = " ".join(
            filter(None, (apply_button.text, apply_button.get_attribute("aria-label")))
        ).lower()

        return Job(
            title=self._text_first((
                ".jobs-unified-top-card__job-title",
                ".job-details-jobs-unified-top-card__job-title",
                "h1",
            )),
            company=self._text_first((
                ".jobs-unified-top-card__company-name",
                ".job-details-jobs-unified-top-card__company-name",
            )),
            location=self._text_first((
                ".jobs-unified-top-card__primary-description",
                ".job-details-jobs-unified-top-card__tertiary-description-container",
            )),
            url=card_url,
            listed=self._text_first((
                ".jobs-unified-top-card__posted-date",
                "li.jobs-unified-top-card__subtitle-item",
            )),
            description=self._text_first((
                ".jobs-description__content",
                ".jobs-description-content__text",
            )),
            easy_apply="easy" in button_text,
            apply_url=apply_url,
        )

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
