# Manual Recaptcha solver
import logging
import time

from scraper.application.interfaces import IRecaptchaSolver, IWebDriverManager

logger = logging.getLogger(__name__)


class RecaptchaManualSolver(IRecaptchaSolver):
    def __init__(self, web_driver: IWebDriverManager):
        self._web_driver = web_driver

    def resolver(self) -> bool:
        logger.info("Starting manual reCAPTCHA solving process.")
        logger.info(
            "Please solve the reCAPTCHA manually in the browser window that appears."
        )
        logger.info("You have 120 seconds to complete the challenge.")

        start_time = time.time()
        timeout = 120

        try:
            while time.time() - start_time < timeout:
                if self._check_if_resolved():
                    logger.info("✅ reCAPTCHA seems to be resolved.")
                    return True

                time.sleep(2)

            logger.warning("⏰ Timeout waiting for manual reCAPTCHA solution.")
            return False
        except Exception as e:
            logger.error(f"An error occurred during manual solving: {e}")
            return False

    def _check_if_resolved(self) -> bool:
        # Check for reCAPTCHA token, or if the URL has changed, indicating
        # successful login
        token = self._web_driver.executar_script(
            """
            return document.querySelector('textarea#g-recaptcha-response')?.value ||
            document.querySelector('input[name=\"g-recaptcha-response\"]')?.value ||
                   document.querySelector('[name*=\"recaptcha\"]')?.value;
        """
        )
        current_url = (
            self._web_driver.executar_script("return window.location.href;") or ""
        )

        is_token_present = token and len(token) > 100
        is_redirected = "login" not in current_url.lower()

        return is_token_present or is_redirected
