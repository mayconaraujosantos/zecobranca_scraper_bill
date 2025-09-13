# Chrome WebDriver manager
import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from scraper.application.interfaces import IWebDriverManager

logger = logging.getLogger(__name__)


class ChromeWebDriverManager(IWebDriverManager):
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    def inicializar(self) -> bool:
        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1200,800")
            chrome_options.add_argument("--disable-gpu")
            if self.headless:
                chrome_options.add_argument("--headless=new")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            logger.info("Driver configurado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar driver: {e}")
            return False

    def finalizar(self) -> bool:
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Driver finalizado com sucesso")
                return True
        except Exception as e:
            logger.error(f"Erro ao finalizar driver: {e}")
        return False

    def executar_script(self, script: str) -> any:
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            logger.error(f"Erro ao executar script: {e}")
            return None

    def navegar_para(self, url: str) -> bool:
        try:
            self.driver.get(url)
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Erro ao navegar para URL: {e}")
            return False

    def preencher_campo(self, seletor: str, valor: str) -> bool:
        try:
            elemento = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
            )
            elemento.clear()
            elemento.send_keys(valor)
            return True
        except Exception as e:
            logger.error(f"Erro ao preencher campo {seletor}: {e}")
            return False

    def clicar_elemento(self, seletor: str) -> bool:
        try:
            elemento = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
            )
            elemento.click()
            return True
        except Exception as e:
            logger.error(f"Erro ao clicar elemento {seletor}: {e}")
            return False

    def aguardar_elemento(self, seletor: str, timeout: int = 10) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
            )
            return True
        except Exception as e:
            logger.error(f"Elemento {seletor} não encontrado: {e}")
            return False
