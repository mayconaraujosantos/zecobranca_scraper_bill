from dataclasses import dataclass, field
from datetime import datetime, timezone
import jwt # Necessário instalar: pip install PyJWT

@dataclass
class Token:
    """Representa um token de acesso."""
    secret: str
    # Atributos adicionais que podem ser extraídos do token JWT
    # Exemplo: {'alg': 'RS256', 'typ': 'JWT'} e payload {'exp': ..., 'nbf': ..., ...}
    payload: dict = field(default_factory=dict) # Para armazenar o payload do JWT decodificado

    @property
    def is_expired(self) -> bool:
        """Verifica se o token expirou."""
        if 'exp' not in self.payload:
            return False # Não é possível verificar a expiração sem o claim 'exp'

        # O timestamp em 'exp' é geralmente em UTC
        expiration_time = datetime.fromtimestamp(self.payload['exp'], tz=timezone.utc)
        return datetime.now(timezone.utc) > expiration_time

    @staticmethod
    def from_jwt(token_string: str, secret_key: str = None) -> 'Token':
        """
        Cria uma instância de Token a partir de uma string JWT.
        Se secret_key for fornecido, tenta decodificar e verificar a assinatura.
        Caso contrário, apenas decodifica o payload sem verificação.
        """
        try:
            if secret_key:
                # Tenta decodificar com verificação (para tokens assinados)
                # Nota: Para tokens assinados por algoritmos assimétricos (como RS256),
                # você precisará da chave pública. Se for um segredo compartilhado (HS256),
                # o secret_key pode ser usado. Neste caso, o segredo usado para obter o token
                # pode não ser diretamente o secret_key para verificação.
                # Se o token for apenas `secret` sem assinatura JWT válida, esta parte pode falhar.
                # O mais provável é que o `secret` no localStorage seja o token em si (JWT).
                # Se a chave privada não estiver disponível, podemos apenas decodificar.
                # Vamos supor que `secret` é o JWT, e que não temos a chave para verificar assinatura aqui.
                # Em cenários reais, a API de autenticação forneceria a chave pública ou o método de validação.

                # Simplificação: Assume que se o valor no localStorage é JSON e tem 'secret',
                # e `secret` é o JWT. Decodificamos para obter expiração.
                # Se `secret` não é um JWT válido, `jwt.decode` falhará.
                payload = jwt.decode(token_string, options={"verify_signature": False})
            else:
                payload = jwt.decode(token_string, options={"verify_signature": False})

            # Extrai o token JWT para o campo 'secret' e o payload decodificado
            return Token(secret=token_string, payload=payload)

        except jwt.ExpiredSignatureError:
            print("Erro: O token JWT expirou.")
            raise ValueError("Token JWT expirado")
        except jwt.InvalidTokenError as e:
            print(f"Erro ao decodificar o token JWT: {e}")
            raise ValueError(f"Token JWT inválido: {e}")
        except Exception as e:
            print(f"Erro inesperado ao processar token JWT: {e}")
            raise ValueError(f"Erro ao processar token: {e}")