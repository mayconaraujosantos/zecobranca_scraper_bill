import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class Settings:
    """Carrega configurações do ambiente e do projeto."""
    LOGIN_USUARIO: str = os.getenv("AGUAS_MANAUS_LOGIN_USUARIO")
    LOGIN_SENHA: str = os.getenv("AGUAS_MANAUS_LOGIN_SENHA")

    # URLs
    AUTH_LOGIN_URL = "https://aeclientes.b2clogin.com/aeclientes.onmicrosoft.com/b2c_1a_signup_signin/oauth2/v2.0/authorize?client_id=b673d12b-6c65-45b4-9c3c-299cc574b4f8&scope=https%3A%2F%2Faeclientes.onmicrosoft.com%2F769f3922-02f3-4a34-9145-d73e3ece30e4%2FAguasAPI.ReadWrite%20openid%20profile%20offline_access&redirect_uri=https%3A%2F%2Fcliente.aguasdemanaus.com.br%2Fhome"
    API_BASE_URL = "https://api.aegea.com.br/external/agencia-virtual/app/v1/"
    CLIENT_PORTAL_URL = "https://cliente.aguasdemanaus.com.br/" # Usado no referer/origin

    # Chaves de API
    API_SUBSCRIPTION_KEY: str = os.getenv("API_SUBSCRIPTION_KEY")
    API_TENANT_ID: str = os.getenv("API_TENANT_ID")

    # Arquivo para armazenar o token
    TOKEN_FILE = "access_token.txt"

    # Configurações do Selenium
    HEADLESS_BROWSER = False # Pode ser definido via variável de ambiente se necessário

settings = Settings()