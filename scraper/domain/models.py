# Domain models for scraper
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field


@dataclass
class Credenciais:
    cpf_cnpj: str
    senha: str


@dataclass
class TokenAcesso:
    valor: str
    expiracao: Optional[int] = None


@dataclass
class InformacoesUsuario:
    id: Optional[str] = None
    nome: Optional[str] = None
    unidades_consumidoras: Optional[List[str]] = None

    def __post_init__(self):
        if self.unidades_consumidoras is None:
            self.unidades_consumidoras = []


@dataclass
class LocalizacaoUsuario:
    latitude: float
    longitude: float

    def para_string(self) -> str:
        return f"latitude={self.latitude}&longitude={self.longitude}"


class FaturaDTO(BaseModel):
    uc: int = Field(alias="UC")
    mes_ano_referencia: str = Field(alias="MES_ANO_REFERENCIA")
    data_vencimento: str = Field(alias="DATA_VENCIMENTO")
    valor_total: float = Field(alias="VALOR_TOTAL")
    codigo_barras: Optional[str] = Field(alias="CODIGO_BARRAS")
    pix: Optional[str] = Field(alias="PIX")

    class Config:
        populate_by_name = True
