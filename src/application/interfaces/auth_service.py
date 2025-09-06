from abc import ABC, abstractmethod

from src.domain.token import Token


class IAuthService(ABC):
    """Interface abstrata para serviços de autenticação."""

    @abstractmethod
    def login_and_get_token(self, cpf_cnpj_email: str, senha: str) -> Token | None:
        """
        Realiza o login e retorna um objeto Token válido.
        Retorna None em caso de falha.
        """
        pass

class ITokenStorageService(ABC):
    """Interface abstrata para serviços de armazenamento de token."""

    @abstractmethod
    def save_token(self, token_secret: str, token_payload: dict) -> None:
        pass

    @abstractmethod
    def load_token(self) -> Token | None:
        pass