from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IApiService(ABC):
    """Interface abstrata para serviços de API externa."""

    @abstractmethod
    def fazer_requisicao(self, matricula: str, sequencial_responsavel: str, zona_ligacao: str) -> Optional[Dict[str, Any]]:
        """
        Executa a requisição específica para a API.
        Retorna os dados da resposta ou None em caso de erro.
        """
        pass