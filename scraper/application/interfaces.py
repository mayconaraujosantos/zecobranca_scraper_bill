# Service interfaces
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from scraper.domain.models import (
    Credenciais,
    FaturaDTO,
    InformacoesUsuario,
    LocalizacaoUsuario,
    TokenAcesso,
)


class IRecaptchaSolver(ABC):
    @abstractmethod
    def resolver(self) -> bool:
        pass


class ILoginService(ABC):
    @abstractmethod
    def autenticar(
        self, credenciais: Credenciais
    ) -> Tuple[Optional[TokenAcesso], Optional[InformacoesUsuario]]:
        pass


class IFaturaService(ABC):
    @abstractmethod
    def obter_faturas_abertas(
        self,
        token: TokenAcesso,
        unidade_consumidora: str,
        client_id: str,
        localizacao: LocalizacaoUsuario,
    ) -> Optional[List[FaturaDTO]]:
        pass


class IWebDriverManager(ABC):
    @abstractmethod
    def inicializar(self) -> bool:
        pass

    @abstractmethod
    def finalizar(self) -> bool:
        pass

    @abstractmethod
    def executar_script(self, script: str) -> Any:
        pass

    @abstractmethod
    def navegar_para(self, url: str) -> bool:
        pass

    @abstractmethod
    def preencher_campo(self, seletor: str, valor: str) -> bool:
        pass

    @abstractmethod
    def clicar_elemento(self, seletor: str) -> bool:
        pass

    @abstractmethod
    def aguardar_elemento(self, seletor: str, timeout: int = 10) -> bool:
        pass
