import logging
from typing import List, Optional

from scraper.application.interfaces import (
    IFaturaService,
    ILoginService,
    IWebDriverManager,
)
from scraper.domain.models import (
    Credenciais,
    FaturaDTO,
    InformacoesUsuario,
    LocalizacaoUsuario,
    TokenAcesso,
)
from scraper.infrastructure.services.amazon_energy_fatura_service import (
    AmazonasEnergyFaturaService,
)

logger = logging.getLogger(__name__)


class SessaoAplicacao:
    def __init__(
        self,
        web_driver_manager: IWebDriverManager,
        login_service: ILoginService,
        fatura_service: IFaturaService,
    ):
        self._web_driver_manager = web_driver_manager
        self._login_service = login_service
        self._fatura_service = fatura_service

        # O token e user_info serão populados APENAS após um login bem-sucedido.
        # Inicializamos como None para indicar que não estamos autenticados.
        self._token: Optional[TokenAcesso] = None
        self._user_info: Optional[InformacoesUsuario] = None

    def inicializar(self) -> bool:
        """Inicializa o gerenciador do driver."""
        return self._web_driver_manager.inicializar()

    def finalizar(self) -> bool:
        """Finaliza o driver."""
        if self._web_driver_manager:
            return self._web_driver_manager.finalizar()
        return True

    def autenticar(self, cpf_cnpj: str, senha: str) -> bool:
        """
        Tenta autenticar. Se bem-sucedido, armazena o token e user_info.
        Retorna True se a autenticação foi bem-sucedida e as informações
        foram armazenadas.
        """
        credenciais = Credenciais(cpf_cnpj=cpf_cnpj, senha=senha)
        token_obtido, user_info_obtido = self._login_service.autenticar(credenciais)

        if token_obtido and user_info_obtido:
            self._token = token_obtido
            self._user_info = user_info_obtido
            logger.info(
                "✅ Autenticação bem-sucedida e informações armazenadas em cache."
            )
            return True
        else:
            logger.warning("💥 Falha na autenticação ou informações não obtidas.")
            # Limpa o cache caso a autenticação falhe
            self._token = None
            self._user_info = None
            return False

    def logout(self) -> None:
        """Limpa o cache de autenticação."""
        self._token = None
        self._user_info = None
        logger.info("Cache de autenticação limpo.")
        # Opcionalmente, você pode querer
        # finalizar o driver aqui se ele não for compartilhado.
        # self.finalizar()

    def obter_faturas(
        self, unidade_consumidora: str, client_id: str
    ) -> Optional[List[FaturaDTO]]:
        """
        Obtém faturas. Requer que o usuário esteja autenticado (token em cache).
        """
        if not self._token:
            logger.error(
                "Não é possível obter faturas: Usuário não "
                "autenticado ou token expirado."
            )
            return None

        # Usar localização padrão se não houver informação específica
        localizacao = LocalizacaoUsuario(latitude=-3.0542864, longitude=-59.9934416)

        # Aqui, a instância de FaturaService é criada. Se você quiser um cache para
        # instâncias de serviço também, pode passá-la no __init__ da SessaoAplicacao.
        fatura_service = AmazonasEnergyFaturaService()

        return fatura_service.obter_faturas_abertas(
            self._token, unidade_consumidora, client_id, localizacao
        )

    @property
    def token(self) -> Optional[TokenAcesso]:
        return self._token

    @property
    def user_info(self) -> Optional[InformacoesUsuario]:
        return self._user_info

    # Propriedade para verificar se está autenticado (útil para o status endpoint)
    @property
    def is_authenticated(self) -> bool:
        return self._token is not None
