import json
import logging

from src.application.use_cases.auth_use_case import AuthUseCase
from src.application.use_cases.query_api_use_case import QueryApiUseCase
from src.config.settings import settings
from src.infrastructure.services.http_api_service import HttpApiService
from src.infrastructure.services.selenium_auth_service import SeleniumAuthService
from src.infrastructure.services.token_storage_service import TokenStorageService

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_dependencies():
    """Configura e injeta as dependências para os casos de uso."""
    # 1. Serviços de infraestrutura
    token_storage_service = TokenStorageService()
    # O SeleniumAuthService precisa do token_storage para salvar o token obtido
    auth_service = SeleniumAuthService(token_storage=token_storage_service, headless=settings.HEADLESS_BROWSER)

    # O HttpApiService precisa do token de acesso. Vamos obtê-lo através do AuthUseCase.
    # Aqui, instanciamos o HttpApiService temporariamente para a injeção no QueryApiUseCase
    # Uma abordagem mais robusta seria ter um factory ou um mecanismo de injeção de dependência.

    # 2. Casos de uso
    auth_use_case = AuthUseCase(auth_service=auth_service, token_storage_service=token_storage_service)

    # Instancia o HttpApiService após garantir que temos um token
    token = auth_use_case.get_valid_token(settings.LOGIN_USUARIO, settings.LOGIN_SENHA)

    if not token:
        logger.error("Não foi possível obter um token válido. Encerrando.")
        return None, None  # Retorna None para ambos os use cases

    api_service = HttpApiService(token=token)
    query_api_use_case = QueryApiUseCase(api_service=api_service,
                                         token_storage_service=token_storage_service)  # Passamos token_storage para futuros reuso

    return auth_use_case, query_api_use_case


def main():
    """Função principal que orquestra o fluxo."""
    logger.info("=" * 60)
    logger.info("CLIENTE API ÁGUAS DE MANAUS - OTIMIZADO COM CLEAN ARCHITECTURE")
    logger.info("=" * 60)

    # Dados de consulta (idealmente, também viriam de uma configuração ou argumento)
    MATRICULA = "1103385"
    SEQUENCIAL_RESPONSAVEL = "886372"
    ZONA_LIGACAO = "1"

    auth_use_case, query_api_use_case = setup_dependencies()

    if not query_api_use_case:
        logger.error("Configuração de dependências falhou. Verifique os logs.")
        return

    logger.info("\n" + "=" * 60)
    logger.info("FAZENDO CONSULTA NA API")
    logger.info("=" * 60)

    resultado = query_api_use_case.consultar_debitos(
        matricula=MATRICULA,
        sequencial_responsavel=SEQUENCIAL_RESPONSAVEL,
        zona_ligacao=ZONA_LIGACAO
    )

    if resultado:
        logger.info("🎉 Processo concluído com sucesso!")
        logger.info("Dados da consulta:")
        logger.info(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        logger.warning("⚠️ Falha na consulta à API.")

    # O Selenium driver é fechado dentro do SeleniumAuthService após o login.
    # Se houvesse necessidade de manter o driver aberto para outras operações,
    # a lógica de fechamento precisaria ser gerenciada aqui.


if __name__ == "__main__":
    main()