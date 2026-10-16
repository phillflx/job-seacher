"""
Creates a SessionManager object
Initialize using SessionManager()
Methods:
    - authenticate((user, password)) -> None: logs to linkedin

"""

import os
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class SessionManager:
    driver: webdriver = None

    def __init__(self):
        self.driver = self.get_chrome_webdriver(detach=True)
        pass

    def get_chrome_webdriver(self, detach: bool = False, headless: bool = False) -> webdriver:
        options = webdriver.ChromeOptions()
        if headless: options.add_argument("--headless=new")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1440,1000")
        options.add_experimental_option("detach", detach)
        return webdriver.Chrome(options=options)

    def authenticate(self, user:str = None, password:str = None) -> None:
        """
        Logs in to Linkedin
        """
        if user is None:
                user = input("Linkedin username: ")
        if password is None:
            password = input("Linkedin password: ")

        self.driver.get("https://www.linkedin.com/login")

        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[type="email"]')))

        email_input = self.driver.find_elements(By.CSS_SELECTOR, '[type="email"]')[1]
        pwd_input = self.driver.find_elements(By.CSS_SELECTOR, '[type="password"]')[1]
        send_button = self.driver.find_elements(By.CSS_SELECTOR, '[type="button"]')[-1]

        print(f"Login in with user name {user}")

        email_input.send_keys(user)
        pwd_input.send_keys(password)
        send_button.click()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # read LINKEDIN_EMAIL and LINKEDIN_PWD from .env
    user = os.environ.get("LINKEDIN_EMAIL")
    password = os.environ.get("LINKEDIN_PWD")

    session_manager = SessionManager()
    session_manager.authenticate()