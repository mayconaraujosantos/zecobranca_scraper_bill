import requests
import json
from typing import Dict, Any, Optional

from src.config.settings import settings
from src.domain.token import Token


class HttpApiService:
    """Serviço para fazer requisições à API externa."""

    def __init__(self, token: Token):
        if not token or not token.secret:
            raise ValueError("Token de acesso é necessário para fazer requisições à API.")
        self.token = token
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'authorization': f'Bearer {self.token.secret}',
            'connection': 'keep-alive',
            'ocp-apim-subscription-key': settings.API_SUBSCRIPTION_KEY,
            'origin': settings.CLIENT_PORTAL_URL.rstrip('/'), # Remove barra final se houver
            'referer': settings.CLIENT_PORTAL_URL.rstrip('/'),
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', # User-agent original do seu código
            'x-tenantid': settings.API_TENANT_ID
        }

    def fazer_requisicao(self, matricula: str, sequencial_responsavel: str, zona_ligacao: str) -> Optional[Dict[str, Any]]:
        """Faz a requisição para obter os débitos totais."""
        url = f"{settings.API_BASE_URL}fatura/debito-totais/matricula"
        params = {
            'matricula': matricula,
            'sequencialResponsavel': sequencial_responsavel,
            'zonaLigacao': zona_ligacao
        }

        try:
            print(f"📡 Fazendo requisição para a API: GET {url} com params={params}")
            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            print(f"📊 Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✅ Requisição bem-sucedida!")
                data = response.json()
                print(f"Dados retornados (primeiros 300 chars): {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
                return data
            elif response.status_code == 401:
                print("❌ Erro 401: Não autorizado. O token pode ter expirado ou é inválido.")
                # Neste ponto, a camada de aplicação pode decidir reautenticar.
                return None
            else:
                print(f"❌ Erro na requisição API: Status {response.status_code}")
                print(f"📄 Response Body: {response.text[:500]}...")
                return None

        except requests.exceptions.Timeout:
            print("💥 Erro: A requisição para a API atingiu o tempo limite (timeout).")
            return None
        except requests.exceptions.RequestException as e:
            print(f"💥 Erro na requisição HTTP: {e}")
            return None
        except Exception as e:
            print(f"💥 Erro inesperado durante a requisição API: {e}")
            return None