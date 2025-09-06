import json

import os

from src.config.settings import settings
from src.domain.token import Token


class TokenStorageService:
    """Serviço para salvar e carregar o token do acesso."""

    def __init__(self, token_file: str = settings.TOKEN_FILE):
        self.token_file = token_file

    def save_token(self, token_secret: str, token_payload: dict) -> None:
        """Salva o token (secret e payload) em um arquivo."""
        try:
            token_data = {
                "secret": token_secret,
                "payload": token_payload
            }
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            print(f"✅ Token salvo em: {self.token_file}")
        except IOError as e:
            print(f"❌ Erro ao salvar token em {self.token_file}: {e}")
            # Decidir como lidar com o erro: levantar exceção, logar, etc.
            raise

    def load_token(self) -> Token | None:
        """Carrega o token do arquivo, se existir e for válido."""
        if not os.path.exists(self.token_file):
            print("ℹ️ Arquivo de token não encontrado.")
            return None

        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)

            if not token_data or 'secret' not in token_data or 'payload' not in token_data:
                print("❌ Dados do token inválidos no arquivo.")
                return None

            token = Token(secret=token_data['secret'], payload=token_data['payload'])

            if token.is_expired:
                print("⚠️ Token carregado expirou. Será necessário gerar um novo.")
                # Opcional: remover o arquivo de token expirado
                # os.remove(self.token_file)
                return None
            else:
                print(f"✅ Token carregado de: {self.token_file}")
                return token

        except (IOError, json.JSONDecodeError, ValueError) as e:
            print(f"❌ Erro ao carregar ou validar token de {self.token_file}: {e}")
            # Se houver erro ao carregar/validar, consideramos o token inválido
            # Opcional: remover arquivo corrompido
            # if os.path.exists(self.token_file):
            #     os.remove(self.token_file)
            return None
        except Exception as e:
            print(f"💥 Erro inesperado ao carregar token: {e}")
            return None