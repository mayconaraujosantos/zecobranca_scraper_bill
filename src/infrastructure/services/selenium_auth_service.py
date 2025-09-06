from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

from src.config.settings import settings
from src.domain.token import Token
from src.infrastructure.services.token_storage_service import TokenStorageService


class SeleniumAuthService:
    """Serviço para autenticação via Selenium e extração de token."""

    def __init__(self, token_storage: TokenStorageService, headless: bool = settings.HEADLESS_BROWSER):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.token_storage = token_storage

    def _setup_driver(self):
        """Configurar o WebDriver."""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox') # Necessário em alguns ambientes headless
            chrome_options.add_argument('--disable-dev-shm-usage') # Necessário em alguns ambientes headless
        else:
            chrome_options.add_argument('--start-maximized')

        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        self.wait = WebDriverWait(self.driver, 20)

    def _extract_access_token_from_local_storage(self) -> Token | None:
        """Extrai o access token do localStorage baseado no padrão encontrado."""
        print("🔎 Extraindo token do localStorage...")
        try:
            # Script para encontrar a chave específica do access token
            access_token_data = self.driver.execute_script("""
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    if (key.includes('accesstoken')) { // Busca por chaves que contenham 'accesstoken'
                        let value = localStorage.getItem(key);
                        // Retorna a chave e o valor bruto para processamento posterior
                        return {key: key, value: value};
                    }
                }
                return null; // Retorna null se nenhuma chave for encontrada
            """)

            if access_token_data:
                print(f"✅ Chave de token encontrada: '{access_token_data['key']}'")
                raw_token_value = access_token_data['value']

                # Tenta decodificar o valor bruto
                try:
                    # O valor em localStorage pode ser um JSON string contendo o token JWT
                    token_info = json.loads(raw_token_value)
                    if 'secret' in token_info:
                        jwt_token_string = token_info['secret']
                        # Tenta criar um objeto Token a partir do JWT
                        token = Token.from_jwt(jwt_token_string)
                        print(f"🎯 Access Token JWT extraído (primeiros 50 chars): {token.secret[:50]}...")
                        return token
                    else:
                        print("❌ Campo 'secret' não encontrado no JSON do token.")
                        print(f"Conteúdo do JSON: {token_info}")
                        return None
                except json.JSONDecodeError:
                    print("❌ Não foi possível decodificar o JSON do valor do token.")
                    print(f"Valor bruto recebido (primeiros 200 chars): {raw_token_value[:200]}...")
                    # Tenta tratar o valor bruto como o próprio token JWT, caso não seja JSON
                    try:
                        token = Token.from_jwt(raw_token_value)
                        print(f"🎯 Access Token JWT extraído (primeiros 50 chars): {token.secret[:50]}...")
                        return token
                    except ValueError:
                        print("❌ O valor bruto também não parece ser um token JWT válido.")
                        return None
                except ValueError as e: # Captura erros específicos de Token.from_jwt
                    print(f"❌ Erro ao processar token JWT: {e}")
                    return None

            else:
                print("❌ Nenhuma chave de token encontrada no localStorage.")
                return None

        except Exception as e:
            print(f"💥 Erro inesperado ao extrair token do localStorage: {e}")
            return None

    def login_and_get_token(self, cpf_cnpj_email: str, senha: str) -> Token | None:
        """Realiza o login e retorna um objeto Token."""
        self._setup_driver()

        try:
            print(f"🚀 Acessando página de login: {settings.AUTH_LOGIN_URL}")
            self.driver.get(settings.AUTH_LOGIN_URL)

            print("📋 Aguardando formulário de login...")
            # Espera o formulário principal estar presente
            self.wait.until(EC.presence_of_element_located((By.ID, "localAccountForm")))

            # Preencher credenciais
            campo_usuario = self.wait.until(EC.element_to_be_clickable((By.ID, "signInName")))
            campo_senha = self.driver.find_element(By.ID, "password")
            botao_entrar = self.driver.find_element(By.ID, "next")

            campo_usuario.clear()
            campo_usuario.send_keys(cpf_cnpj_email)
            campo_senha.clear()
            campo_senha.send_keys(senha)

            print("🖱️ Clicando no botão 'Entrar'...")
            botao_entrar.click()

            print("⏳ Aguardando redirecionamento após login...")
            # Usar WebDriverWait para esperar a URL mudar ou um elemento específico da página logada aparecer
            # Uma heurística é esperar a URL do portal do cliente ou um elemento que só aparece após o login.
            # Para este exemplo, usamos um tempo fixo mais curto e depois verificamos a URL.
            time.sleep(5) # Pequena pausa para dar tempo ao JavaScript de agir

            current_url = self.driver.current_url
            print(f"URL atual após login: {current_url}")

            if settings.CLIENT_PORTAL_URL in current_url:
                print("✅ Login realizado com sucesso!")

                # Aguardar um pouco mais para garantir que o token seja preenchido no localStorage
                time.sleep(3)

                # Extrair o access token do localStorage
                token = self._extract_access_token_from_local_storage()
                if token:
                    self.token_storage.save_token(token.secret, token.payload)
                    return token
                else:
                    print("❌ Não foi possível extrair o access token do localStorage.")
                    return None
            else:
                print(f"⚠️ Possível falha no login. URL atual não contém {settings.CLIENT_PORTAL_URL}.")
                # Tentar buscar por mensagens de erro na página
                try:
                    error_message_element = self.driver.find_element(By.CLASS_NAME, "error")
                    print(f"Mensagem de erro na página: {error_message_element.text}")
                except:
                    print("Nenhuma mensagem de erro explícita encontrada na página.")
                return None

        except Exception as e:
            print(f"💥 Erro durante o login com Selenium: {e}")
            return None
        finally:
            self.close() # Garante que o driver seja fechado após o login

    def close(self):
        """Fecha o driver do Selenium."""
        if self.driver:
            self.driver.quit()
            print("🔚 Navegador Selenium fechado.")