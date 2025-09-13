# Amazon Energy Login Service implementation
import logging
import time
from typing import Optional, Tuple

from scraper.application.interfaces import (
    ILoginService,
    IRecaptchaSolver,
    IWebDriverManager,
)
from scraper.domain.models import Credenciais, InformacoesUsuario, TokenAcesso

logger = logging.getLogger(__name__)


class AmazonasEnergyLoginService(ILoginService):
    def __init__(
        self, web_driver_manager: IWebDriverManager, recaptcha_solver: IRecaptchaSolver
    ):
        self._web_driver_manager = web_driver_manager
        self._recaptcha_solver = recaptcha_solver

    def autenticar(
        self, credenciais: Credenciais
    ) -> Tuple[Optional[TokenAcesso], Optional[InformacoesUsuario]]:
        try:
            if not self._inicializar_navegador():
                return None, None
            if not self._preencher_credenciais(credenciais):
                return None, None
            if not self._recaptcha_solver.resolver():
                return None, None
            if not self._clicar_botao_login():
                return None, None

            time.sleep(5)

            token = self._obter_token_acesso()
            if not token:
                return None, None

            user_info = self._extrair_informacoes_usuario()
            logger.info("✅ Login realizado com sucesso!")
            return token, user_info
        except Exception as e:
            logger.error(f"💥 Erro no processo de login: {e}")
            return None, None

    def _inicializar_navegador(self) -> bool:
        logger.info("🌐 Acessando Amazonas Energia")
        return self._web_driver_manager.navegar_para(
            "https://agencia.amazonasenergia.com/"
        )

    def _preencher_credenciais(self, credenciais: Credenciais) -> bool:
        logger.info("📝 Preenchendo credenciais")
        sucesso_cpf = self._web_driver_manager.preencher_campo(
            "input[name='CPF_CNPJ']", credenciais.cpf_cnpj
        )
        sucesso_senha = self._web_driver_manager.preencher_campo(
            "input[name='SENHA']", credenciais.senha
        )
        return sucesso_cpf and sucesso_senha

    def _clicar_botao_login(self) -> bool:
        logger.info("🚀 Clicando no botão de login")
        return self._web_driver_manager.clicar_elemento("button[type='submit']")

    def _obter_token_acesso(self) -> Optional[TokenAcesso]:
        token_valor = self._web_driver_manager.executar_script(
            """
            return localStorage.getItem('@AGENCIA-VIRTUAL:TOKEN-KEY');
        """
        )
        if token_valor:
            logger.info("🔑 Token recuperado com sucesso")
            return TokenAcesso(valor=token_valor)
        logger.warning("⚠️ Token não encontrado no localStorage")
        return None

    def _extrair_informacoes_usuario(self) -> InformacoesUsuario:
        user_info = InformacoesUsuario()
        try:
            user_data = self._web_driver_manager.executar_script(
                """
                const userData = localStorage.getItem('@AGENCIA-VIRTUAL:USER-DATA');
                return userData ? JSON.parse(userData) : {};
            """
            )
            if user_data:
                user_info.id = user_data.get("ID")
                user_info.nome = user_data.get("NOME")
                user_info.unidades_consumidoras = user_data.get(
                    "UNIDADES_CONSUMIDORAS", []
                )
            logger.info(f"📋 Informações do usuário extraídas: {user_info.__dict__}")
        except Exception as e:
            logger.error(f"Erro ao extrair informações do usuário: {e}")
        return user_info
