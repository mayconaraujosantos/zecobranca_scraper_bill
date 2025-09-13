import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class IRecaptchaSolver(ABC):
    @abstractmethod
    def resolver(self) -> bool:
        pass


class RecaptchaAPISolver(IRecaptchaSolver):
    def __init__(
        self, web_driver, api_key: str, service_url: str = "http://2captcha.com"
    ):
        self._web_driver = web_driver
        self.api_key = api_key
        self.service_url = service_url

    def resolver(self) -> bool:
        logger.info("Starting automatic reCAPTCHA solving via API")

        # Obter site key do reCAPTCHA
        site_key = self._get_recaptcha_site_key()
        if not site_key:
            logger.error("Could not find reCAPTCHA site key")
            return False

        # Resolver via API
        captcha_id = self._send_captcha_to_service(site_key)
        if not captcha_id:
            return False

        # Aguardar solução
        solution = self._wait_for_solution(captcha_id)
        if not solution:
            return False

        # Inserir solução
        return self._submit_solution(solution)

    def _get_recaptcha_site_key(self) -> str:
        return self._web_driver.executar_script(
            """
            return document.querySelector('.g-recaptcha')?.dataset?.sitekey ||
                   document.querySelector('[data-sitekey]')?.dataset?.sitekey ||
                   document.querySelector('iframe[src*=\"recaptcha\"]')?.src?.match(/k=([^&]+)/)?.[1];
        """
        )

    def _send_captcha_to_service(self, site_key: str) -> Optional[str]:
        try:
            page_url = self._web_driver.executar_script("return window.location.href;")
            data = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1,
            }

            response = requests.post(f"{self.service_url}/in.php", data=data)
            result = response.json()

            if result.get("status") == 1:
                return result.get("request")
            else:
                logger.error(f"API error: {result.get('error_text')}")
                return None

        except Exception as e:
            logger.error(f"Error sending captcha to service: {e}")
            return None

    def _wait_for_solution(self, captcha_id: str, timeout: int = 120) -> str:
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.service_url}/res.php",
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1,
                    },
                )

                result = response.json()

                if result.get("status") == 1:
                    return result.get("request")
                elif result.get("request") == "CAPCHA_NOT_READY":
                    time.sleep(5)
                else:
                    logger.error(f"Captcha solving failed: {result.get('request')}")
                    return None

            except Exception as e:
                logger.error(f"Error checking captcha solution: {e}")
                time.sleep(5)

        logger.warning("Timeout waiting for captcha solution")
        return None

    def _submit_solution(self, solution: str) -> bool:
        try:
            # Inserir token no textarea oculto
            self._web_driver.executar_script(
                f"""
                document.querySelector('textarea#g-recaptcha-response').value = '{solution}';
                document.querySelector('input[name=\"g-recaptcha-response\"]').value = '{solution}';
            """
            )

            # Disparar evento change
            self._web_driver.executar_script(
                """
                var event = new Event('change', {{ bubbles: true }});
                document.querySelector('textarea#g-recaptcha-response').dispatchEvent(event);
                document.querySelector('input[name=\"g-recaptcha-response\"]').dispatchEvent(event);
            """
            )

            return True

        except Exception as e:
            logger.error(f"Error submitting solution: {e}")
            return False
