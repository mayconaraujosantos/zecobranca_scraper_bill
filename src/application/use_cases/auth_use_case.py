
import logging

from src.application.interfaces.auth_service import IAuthService, ITokenStorageService
from src.domain.token import Token

logger = logging.getLogger(__name__)

class AuthUseCase:
    """Casos de uso relacionados à autenticação e gerenciamento de token."""

    def __init__(self, auth_service: IAuthService, token_storage_service: ITokenStorageService):
        self.auth_service = auth_service
        self.token_storage_service = token_storage_service

    def get_valid_token(self, cpf_cnpj_email: str, senha: str) -> Token | None:
        """
        Tenta carregar um token válido do armazenamento.
        Se não encontrar ou for inválido, tenta realizar o login para obter um novo.
        """
        # 1. Tentar carregar token do armazenamento
        stored_token = self.token_storage_service.load_token()

        if stored_token:
            logger.info("Token válido carregado do armazenamento.")
            return stored_token
        else:
            logger.warning("Nenhum token válido encontrado ou token expirado. Tentando login...")
            # 2. Se não houver token válido, realizar login
            new_token = self.auth_service.login_and_get_token(cpf_cnpj_email, senha)
            if new_token:
                logger.info("Novo token obtido com sucesso via login.")
                # O serviço de autenticação já salva o token no armazenamento
                return new_token
            else:
                logger.error("Falha ao obter token, mesmo após tentar o login.")
                return None