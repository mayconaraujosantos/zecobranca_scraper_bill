# Amazon Energy Fatura Service implementation
import logging
from typing import Dict, List, Optional

import requests

from scraper.application.interfaces import IFaturaService
from scraper.domain.models import FaturaDTO, LocalizacaoUsuario, TokenAcesso

logger = logging.getLogger(__name__)


class AmazonasEnergyFaturaService(IFaturaService):
    def obter_faturas_abertas(
        self,
        token: TokenAcesso,
        unidade_consumidora: str,
        client_id: str,
        localizacao: LocalizacaoUsuario,
    ) -> Optional[List[FaturaDTO]]:
        url = "https://api-agencia.amazonasenergia.com/api/faturas/abertas"
        headers = self._construir_headers(
            token, unidade_consumidora, client_id, localizacao
        )
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            if "application/json" in response.headers.get("Content-Type", ""):
                faturas_data = response.json()
                return self._converter_para_faturas_dto(faturas_data)
            else:
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição das faturas: {e}")
            return None

    def _construir_headers(
        self,
        token: TokenAcesso,
        unidade_consumidora: str,
        client_id: str,
        localizacao: LocalizacaoUsuario,
    ) -> Dict:
        # Aceita tanto TokenAcesso quanto str
        token_str = token.valor if hasattr(token, "valor") else str(token)
        return {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {token_str}",
            "X-Client-Id": client_id,
            "X-Consumer-Unit": unidade_consumidora,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36",
            "Referer": "https://agencia.amazonasenergia.com/",
        }

    def _converter_para_faturas_dto(self, faturas_data: List[Dict]) -> List[FaturaDTO]:
        return [FaturaDTO.model_validate(fatura) for fatura in faturas_data]
