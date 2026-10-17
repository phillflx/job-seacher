"""Apply to LinkedIn jobs through the Easy Apply dialog."""

import re
from typing import Any

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from .fields_searcher import FieldsSearcher
from .job import Job, Jobs
from .session_manager import SessionManager

EASY_APPLY_DIALOG_SELECTOR = (
    '[data-sdui-screen="com.linkedin.sdui.flagshipnav.jobs.easyapply.EasyApply"]'
)
EASY_APPLY_BUTTON_SELECTORS = (
    "button.jobs-apply-button",
    'button[aria-label*="Easy Apply"]',
    'button[aria-label*="Easy apply"]',
)
FORM_CONTROL_SELECTOR = "input, textarea, select"
ACTION_LABELS = (
    "submit application",
    "submit",
    "apply",
    "review",
    "next",
)
SUCCESS_MESSAGE = "your application was sent"


class JobApplier:
    """Fill and submit LinkedIn Easy Apply forms from a text profile."""

    def __init__(
        self,
        session_manager: SessionManager,
        user_profie: str,
        fields_searcher: FieldsSearcher | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.driver = session_manager.driver
        self.user_profie = user_profie
        self.fields_searcher = fields_searcher or FieldsSearcher()
        self.jobs = Jobs()
        self.wait = WebDriverWait(self.driver, 15)

    def apply_to_job(self, job: Job) -> None:
        """Open Easy Apply, fill available fields, and submit the application."""
        if job.linkedin_url:
            self.driver.get(job.linkedin_url)

        easy_apply_button = self.wait.until(self._find_easy_apply_button)
        easy_apply_button.click()
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, EASY_APPLY_DIALOG_SELECTOR))
        )

        for _step in range(20):
            if self._application_was_sent():
                self._mark_job_applied(job)
                return

            dialog = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, EASY_APPLY_DIALOG_SELECTOR))
            )
            self._fill_empty_fields(dialog)

            action_button = self._find_action_button(dialog)
            if action_button is None:
                raise RuntimeError("Easy Apply dialog has no Next, Review, Apply, or Submit button.")

            before_state = self._dialog_state(dialog)
            action_button.click()

            try:
                self.wait.until(
                    lambda _driver: self._application_was_sent()
                    or self._current_dialog_state() != before_state
                )
            except TimeoutException as error:
                raise RuntimeError(
                    "Easy Apply did not advance. Review the visible fields and any validation errors."
                ) from error

            if self._application_was_sent():
                self._mark_job_applied(job)
                return

        raise RuntimeError("Easy Apply did not finish after 20 form steps.")

    def _mark_job_applied(self, job: Job) -> None:
        """Persist the applied flag after LinkedIn confirms the submission."""
        job.applied = True
        try:
            self.jobs.update(job)
        except LookupError:
            # Also persist applications for jobs that were not imported beforehand.
            self.jobs.create(job)

    def _find_easy_apply_button(self, driver):
        for selector in EASY_APPLY_BUTTON_SELECTORS:
            for button in driver.find_elements(By.CSS_SELECTOR, selector):
                if button.is_displayed() and button.is_enabled():
                    label = " ".join(
                        (button.text, button.get_attribute("aria-label") or "")
                    ).lower()
                    if "easy" in label:
                        return button

        for button in driver.find_elements(By.CSS_SELECTOR, "button"):
            label = " ".join((button.text, button.get_attribute("aria-label") or "")).lower()
            if button.is_displayed() and button.is_enabled() and "easy apply" in label:
                return button
        return False

    def _fill_empty_fields(self, dialog) -> None:
        fields = self._get_empty_fields(dialog)
        if not fields:
            return

        requested_fields = [field["request"] for field in fields]
        values = self.fields_searcher.get_fields_from_text(
            self.user_profie,
            requested_fields,
        )

        for field in fields:
            answer = values.get(field["request"])
            if answer is None or str(answer).strip() == "":
                continue
            try:
                self._fill_field(field, answer)
            except (
                ElementClickInterceptedException,
                ElementNotInteractableException,
                StaleElementReferenceException,
            ):
                continue

    def _get_empty_fields(self, dialog) -> list[dict[str, Any]]:
        controls = []
        radio_groups: dict[str, list[Any]] = {}

        for element in dialog.find_elements(By.CSS_SELECTOR, FORM_CONTROL_SELECTOR):
            if not element.is_displayed() or not element.is_enabled():
                continue

            tag = element.tag_name.lower()
            input_type = (element.get_attribute("type") or "text").lower()
            if tag == "input" and input_type in {
                "hidden", "submit", "button", "reset", "file", "image", "password"
            }:
                continue

            if tag == "input" and input_type == "radio":
                name = element.get_attribute("name") or element.get_attribute("id") or ""
                radio_groups.setdefault(name, []).append(element)
                continue

            if not self._is_empty(element, tag, input_type):
                continue

            label = self._field_label(element)
            if label:
                controls.append({"kind": "control", "elements": [element], "label": label})

        for group_name, elements in radio_groups.items():
            if any(element.is_selected() for element in elements):
                continue
            labels = [self._field_label(element) for element in elements]
            group_label = self._radio_group_label(elements, group_name)
            options = [label for label in labels if label and label != group_label]
            if group_label:
                controls.append(
                    {
                        "kind": "radio",
                        "elements": elements,
                        "label": f"{group_label}; options: {', '.join(options)}",
                    }
                )

        fields = []
        for index, control in enumerate(controls):
            request = f"field_{index}: {control['label']}"
            control["request"] = request
            fields.append(control)
        return fields

    @staticmethod
    def _is_empty(element, tag: str, input_type: str) -> bool:
        if tag == "select":
            selected = Select(element).first_selected_option
            value = (selected.get_attribute("value") or "").strip()
            text = selected.text.strip().lower()
            return not value or text in {"select an option", "select one", "choose one"}
        if tag == "input" and input_type in {"checkbox"}:
            return not element.is_selected()
        if tag == "input" and input_type in {"radio"}:
            return not element.is_selected()
        return not (element.get_attribute("value") or "").strip()

    def _field_label(self, element) -> str:
        parts = [
            element.get_attribute("aria-label"),
            element.get_attribute("placeholder"),
        ]
        element_id = element.get_attribute("id")
        if element_id:
            try:
                parts.append(
                    self.driver.find_element(By.CSS_SELECTOR, f'label[for="{element_id}"]').text
                )
            except NoSuchElementException:
                pass
        if not any(part and part.strip() for part in parts):
            parts.extend((element.get_attribute("name"), element.get_attribute("id")))
            try:
                parts.append(element.find_element(By.XPATH, "./ancestor::*[self::div or self::fieldset][1]").text)
            except NoSuchElementException:
                pass
        return " ".join(dict.fromkeys(part.strip() for part in parts if part and part.strip()))

    def _radio_group_label(self, elements: list[Any], group_name: str) -> str:
        for element in elements:
            try:
                container_text = element.find_element(
                    By.XPATH, "./ancestor::*[self::fieldset or self::div][1]"
                ).text.strip()
                if container_text:
                    return container_text
            except NoSuchElementException:
                continue
        return group_name

    def _fill_field(self, field: dict[str, Any], answer: Any) -> None:
        elements = field["elements"]
        kind = field["kind"]
        if kind == "radio":
            normalized_answer = str(answer).strip().lower()
            for element in elements:
                label = self._field_label(element).lower()
                value = (element.get_attribute("value") or "").strip().lower()
                if normalized_answer in {label, value} or label in normalized_answer:
                    element.click()
                    return
            return

        element = elements[0]
        tag = element.tag_name.lower()
        input_type = (element.get_attribute("type") or "text").lower()
        if tag == "select":
            select = Select(element)
            normalized_answer = str(answer).strip().lower()
            for option in select.options:
                option_text = option.text.strip().lower()
                option_value = (option.get_attribute("value") or "").strip().lower()
                if normalized_answer in {option_text, option_value}:
                    option.click()
                    return
            for option in select.options:
                if normalized_answer and normalized_answer in option.text.strip().lower():
                    option.click()
                    return
            return

        if tag == "input" and input_type == "checkbox":
            if str(answer).strip().lower() in {"yes", "true", "1", "checked"}:
                element.click()
            return

        element.clear()
        element.send_keys(str(answer))

    def _find_action_button(self, dialog):
        buttons = [
            button
            for button in dialog.find_elements(By.CSS_SELECTOR, "button")
            if button.is_displayed() and button.is_enabled()
        ]
        for label in ACTION_LABELS:
            for button in buttons:
                button_text = " ".join(
                    (button.text, button.get_attribute("aria-label") or "")
                ).strip().lower()
                if re.search(rf"\b{re.escape(label)}\b", button_text):
                    return button
        return None

    def _application_was_sent(self) -> bool:
        try:
            return SUCCESS_MESSAGE in self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def _current_dialog_state(self) -> str:
        try:
            dialogs = self.driver.find_elements(By.CSS_SELECTOR, EASY_APPLY_DIALOG_SELECTOR)
            return self._dialog_state(dialogs[0]) if dialogs else ""
        except StaleElementReferenceException:
            return ""

    @staticmethod
    def _dialog_state(dialog) -> str:
        text = dialog.text
        buttons = [
            " ".join((button.text, button.get_attribute("aria-label") or ""))
            for button in dialog.find_elements(By.CSS_SELECTOR, "button")
            if button.is_displayed()
        ]
        controls = [
            "|".join(
                (
                    element.tag_name,
                    element.get_attribute("name") or "",
                    element.get_attribute("value") or "",
                    element.get_attribute("aria-label") or "",
                    str(element.is_selected()),
                )
            )
            for element in dialog.find_elements(By.CSS_SELECTOR, FORM_CONTROL_SELECTOR)
            if element.is_displayed()
        ]
        return f"{text}\n{'|'.join(buttons)}\n{'|'.join(controls)}"
