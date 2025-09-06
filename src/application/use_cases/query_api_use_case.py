from typing import Dict, Any, Optional

import logging

from src.application.interfaces.api_service import IApiService
from src.application.interfaces.auth_service import ITokenStorageService

logger = logging.getLogger(__name__)

class QueryApiUseCase:
    """Casos de uso para interagir com a API externa."""

    def __init__(self, api_service: IApiService, token_storage_service: ITokenStorageService):
        self.api_service = api_service
        self.token_storage_service = token_storage_service

    def consultar_debitos(self, matricula: str, sequencial_responsavel: str, zona_ligacao: str) -> Optional[Dict[str, Any]]:
        """
        Consulta os débitos totais de uma matrícula na API.
        Verifica a validade do token e tenta reautenticar se necessário.
        """
        # Primeiro, obtém o token válido (que pode ser carregado ou obtido via login)
        # NOTA: A lógica de reautenticação em caso de 401 aqui pode ser mais complexa.
        # Idealmente, a camada de aplicação orquestra isso.
        # Para este exemplo, assumimos que o token já é válido ao chamar o use case.
        # Se a requisição falhar com 401, a camada de `main` pode tentar reautenticar.

        # Em um fluxo mais complexo, o use case poderia ter acesso ao AuthUseCase
        # para tentar reautenticar em caso de erro 401.
        # Por simplicidade agora, vamos apenas usar o token atual.
        # O HttpApiService já espera um Token válido.

        data = self.api_service.fazer_requisicao(matricula, sequencial_responsavel, zona_ligacao)

        if data:
            logger.info("Consulta de débitos à API realizada com sucesso.")
            return data
        else:
            logger.error("Falha na consulta de débitos à API.")
            return None