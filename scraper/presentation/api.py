import logging
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta

from flasgger import Swagger, swag_from
from flask import Flask, g, jsonify, request

from scraper.application.interfaces import (
    IFaturaService,
    ILoginService,
    IWebDriverManager,
)
from scraper.application.services import SessaoAplicacao
from scraper.domain.models import FaturaDTO
from scraper.infrastructure.recaptcha_solvers.manual_solver import RecaptchaManualSolver
from scraper.infrastructure.services.amazon_energy_fatura_service import (
    AmazonasEnergyFaturaService,
)
from scraper.infrastructure.services.amazon_energy_login_service import (
    AmazonasEnergyLoginService,
)
from scraper.infrastructure.web_drivers.chrome_driver_manager import (
    ChromeWebDriverManager,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)
app.config["LOGIN_TIMEOUT_SECONDS"] = 60
_executor = ThreadPoolExecutor(max_workers=4)

# Initialize Swagger UI
swagger = Swagger(app)

cache = {"token": None, "user_info": None, "expiry": None}


# --- Factory and Request Context Management ---


def create_scraper_session(headless: bool = False) -> SessaoAplicacao:
    """Factory para criar uma nova instância de SessaoAplicacao com suas dependências."""
    try:
        web_driver_manager = ChromeWebDriverManager(headless=headless)
        recaptcha_solver = RecaptchaManualSolver(web_driver_manager)
        login_service = AmazonasEnergyLoginService(web_driver_manager, recaptcha_solver)
        fatura_service = AmazonasEnergyFaturaService()
        session = SessaoAplicacao(web_driver_manager, login_service, fatura_service)

        # Tenta inicializar o driver aqui. Se falhar, a exceção será tratada pelos hooks.
        if not session.inicializar():
            raise Exception("Falha ao inicializar o navegador.")
        return session
    except Exception as e:
        logger.error(f"Erro na criação e inicialização da sessão: {e}")
        # Se a inicialização falhar, tenta fechar o driver caso algo tenha sido iniciado
        if (
            "web_driver_manager" in locals()
            and web_driver_manager
            and web_driver_manager.driver
        ):
            web_driver_manager.finalizar()
        raise  # Re-lança a exceção para ser tratada pelo hook ou pelo Flask


@app.before_request
def before_request_hook():
    """
    Executa ANTES de cada requisição. Cria uma nova sessão e a armazena em `g.session`.
    `g` é um objeto especial do Flask para dados de requisição únicos.
    """
    try:
        # Para rodar em modo headless, mude `headless=False` para `True`
        g.session = create_scraper_session(headless=False)
    except Exception as e:
        # Se a criação da sessão falhar, armazena o erro em g para ser tratado nos endpoints.
        g.session_error = e
        logger.error(f"Erro antes da requisição: {e}")


@app.teardown_request
def teardown_request_hook(exception=None):
    """
    Executa APÓS cada requisição, mesmo que ocorra um erro.
    Garante que a sessão e o driver sejam finalizados.
    """
    session = g.pop("session", None)  # Pega a sessão de g e a remove
    if session:
        try:
            session.finalizar()
            logger.info("Sessão do scraper finalizada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao finalizar a sessão do scraper: {e}")


# --- API Endpoint Definitions with Swagger Docstrings ---


@app.route("/login", methods=["POST"])
@swag_from(
    {
        "tags": ["Authentication"],
        "summary": "Realiza o login na plataforma Amazonas Energia.",
        "description": "Autentica o usuário com suas credenciais (CPF/CNPJ e senha) e retorna informações do usuário.",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "cpf_cnpj": {
                            "type": "string",
                            "description": "CPF ou CNPJ do usuário.",
                        },
                        "senha": {"type": "string", "description": "Senha do usuário."},
                    },
                    "example": {"cpf_cnpj": "12345678901", "senha": "sua_senha_aqui"},
                },
            }
        ],
        "responses": {
            "200": {
                "description": "Login bem-sucedido. Informações do usuário retornadas.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "message": {"type": "string"},
                        "user_info": {
                            "type": "object",
                            "properties": {
                                "id": {"type": ["string", "null"]},
                                "nome": {"type": ["string", "null"]},
                                "unidades_consumidoras": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "400": {
                "description": "Requisição inválida. Faltam parâmetros.",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
            },
            "401": {
                "description": "Falha na autenticação.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "message": {"type": "string"},
                    },
                },
            },
            "500": {
                "description": "Erro interno do servidor (problema na inicialização do scraper).",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
            },
        },
    }
)
def login_endpoint():
    data = request.get_json()
    if not data or "cpf_cnpj" not in data or "senha" not in data:
        return jsonify({"error": "CPF/CNPJ e senha são obrigatórios"}), 400

    # 1. Checar o cache
    if cache["token"] and cache["expiry"] > datetime.now():
        logger.info("🔑 Login realizado via cache, evitando reprocessamento.")
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Login realizado via cache",
                    "token": cache["token"],
                    "user_info": (
                        cache["user_info"].__dict__ if cache["user_info"] else {}
                    ),
                }
            ),
            200,
        )

    # Se o cache não for válido, prossegue com a lógica de login
    try:
        # A sessão é criada e inicializada pelo before_request hook
        if "session_error" in g:
            return (
                jsonify(
                    {
                        "error": f"Falha interna ao preparar o serviço: {str(g.session_error)}"
                    }
                ),
                500,
            )

        session = g.session

        if session.autenticar(data["cpf_cnpj"], data["senha"]):
            # 2. Login bem-sucedido, armazenar no cache
            cache["token"] = session.token.valor
            cache["user_info"] = session.user_info
            cache["expiry"] = datetime.now() + timedelta(hours=1)  # Expira em 1 hora

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Login realizado com sucesso",
                        "token": session.token.valor,
                        "user_info": (
                            session.user_info.__dict__ if session.user_info else {}
                        ),
                    }
                ),
                200,
            )
        else:
            return jsonify({"status": "error", "message": "Falha no login"}), 401

    except Exception as e:
        logger.error(f"Erro no endpoint de login: {e}")
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500


@app.route("/faturas", methods=["GET"])
@swag_from(
    {
        "tags": ["Invoices"],
        "summary": "Obtém as faturas abertas do usuário.",
        "description": "Recupera as faturas abertas para uma unidade consumidora específica. Requer autenticação prévia.",
        "parameters": [
            {
                "name": "X-Consumer-Unit",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Identificador da unidade consumidora.",
            },
            {
                "name": "X-Client-Id",
                "in": "header",
                "type": "string",
                "required": True,
                "description": "Identificador do cliente.",
            },
        ],
        "responses": {
            "200": {
                "description": "Lista de faturas obtida com sucesso.",
                "schema": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/FaturaDTO"  # Reference to definition below
                    },
                },
            },
            "400": {
                "description": "Requisição inválida. Headers ausentes.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "required_headers": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "401": {
                "description": "Não autenticado. Sessão inválida ou expirada.",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
            },
            "500": {
                "description": "Erro interno do servidor.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "message": {"type": "string"},
                    },
                },
            },
        },
        "definitions": {  # Define FaturaDTO structure for Swagger
            "FaturaDTO": {
                "type": "object",
                "properties": {
                    "uc": {"type": "integer"},
                    "mes_ano_referencia": {"type": "string"},
                    "data_vencimento": {"type": "string"},
                    "valor_total": {"type": "number"},
                    "codigo_barras": {"type": ["string", "null"]},
                    "pix": {"type": ["string", "null"]},
                },
            }
        },
    }
)
def faturas_endpoint():
    """Endpoint para obter faturas. Verifica se a sessão está autenticada."""

    # Verifica se a sessão foi inicializada com sucesso e se temos um token
    # Se houver um erro na inicialização da sessão, ele já teria retornado 500 no before_request_hook.
    # Aqui, verificamos se a sessão está autenticada (tem token).
    token = request.headers.get("Authorization")
    if token and token.lower().startswith("bearer "):
        token = token[7:]

    if not token or token != cache["token"]:
        logger.warning("Token ausente ou inválido no endpoint /faturas.")
        return (
            jsonify({"error": "Token ausente ou inválido. Faça login novamente."}),
            401,
        )

    consumer_unit = request.headers.get("X-Consumer-Unit")
    client_id = request.headers.get("X-Client-Id")

    if not all([consumer_unit, client_id]):
        return (
            jsonify(
                {
                    "error": "Headers necessários ausentes.",
                    "required_headers": ["X-Consumer-Unit", "X-Client-Id"],
                }
            ),
            400,
        )

    # Cria uma sessão temporária para buscar as faturas
    session = create_scraper_session(headless=True)
    session._token = cache["token"]
    session._user_info = cache["user_info"]
    faturas = session.obter_faturas(consumer_unit, client_id)

    if faturas is not None:
        try:
            # Use model_dump for Pydantic v2+
            return (
                jsonify([fatura.model_dump(by_alias=True) for fatura in faturas]),
                200,
            )
        except Exception as e:
            logger.error(f"Erro ao serializar faturas: {e}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Erro ao processar faturas: {str(e)}",
                    }
                ),
                500,
            )
    else:
        logger.warning("Nenhuma fatura encontrada ou erro ao buscá-las.")
        return (
            jsonify(
                {"status": "error", "message": "Não foi possível obter as faturas."}
            ),
            500,
        )


@app.route("/logout", methods=["POST"])
@swag_from(
    {
        "tags": ["Authentication"],
        "summary": "Realiza o logout da sessão atual.",
        "description": "Encerra a sessão ativa do usuário e libera os recursos do navegador.",
        "responses": {
            "200": {
                "description": "Logout bem-sucedido.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "message": {"type": "string"},
                    },
                },
            }
        },
    }
)
def logout_endpoint():
    """Endpoint de logout. Limpa o cache e finaliza a sessão."""
    session = g.get("session", None)  # Pega a sessão de g, se existir
    if session:
        session.logout()  # Limpa o cache interno da sessão
        # A finalização do driver será tratada pelo teardown_request_hook

    # Se session não existir em g, significa que antes mesmo de criar a sessão houve um erro,
    # ou a requisição foi feita antes do login. Neste caso, não há o que limpar.

    return jsonify({"status": "success", "message": "Logout realizado"}), 200


@app.route("/status", methods=["GET"])
@swag_from(
    {
        "tags": ["Authentication"],
        "summary": "Verifica o status da autenticação do usuário.",
        "description": "Retorna o status atual da sessão (autenticado ou não) e informações do usuário, se disponíveis.",
        "responses": {
            "200": {
                "description": "Status da sessão retornado.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["authenticated", "not_authenticated"],
                        },
                        "has_token": {"type": "boolean"},
                        "user_info": {
                            "type": "object",
                            "properties": {
                                "id": {"type": ["string", "null"]},
                                "nome": {"type": ["string", "null"]},
                                "unidades_consumidoras": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "500": {
                "description": "Erro interno do servidor (sessão não inicializada).",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
            },
        },
    }
)
def status_endpoint():
    """Endpoint para verificar o status da sessão."""
    session = g.get("session", None)  # Pega a sessão de g, se existir

    if not session:
        logger.warning(
            "Endpoint /status chamado, mas sessão do scraper não foi inicializada."
        )
        return (
            jsonify(
                {
                    "status": "not_authenticated",
                    "has_token": False,
                    "user_info": {},
                    "message": "Sessão do scraper indisponível (falha na inicialização).",
                }
            ),
            500,
        )

    # A sessão está disponível, podemos verificar o status de autenticação
    is_authenticated = session.is_authenticated  # Usa a propriedade is_authenticated
    user_info = (
        session.user_info.__dict__ if is_authenticated and session.user_info else {}
    )

    return (
        jsonify(
            {
                "status": "authenticated" if is_authenticated else "not_authenticated",
                "has_token": is_authenticated,
                "user_info": user_info,
            }
        ),
        200,
    )


@app.route("/faturas_auto", methods=["POST"])
@swag_from(
    {
        "tags": ["Invoices"],
        "summary": "Login + Faturas em uma chamada.",
        "description": "Recebe credenciais e dados de fatura, faz login e retorna as faturas abertas.",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "cpf_cnpj": {"type": "string"},
                        "senha": {"type": "string"},
                        "consumer_unit": {"type": "string"},
                        "client_id": {"type": "string"},
                    },
                    "example": {
                        "cpf_cnpj": "12345678901",
                        "senha": "sua_senha_aqui",
                        "consumer_unit": "991643",
                        "client_id": "18839258",
                    },
                },
            }
        ],
        "responses": {
            "200": {
                "description": "Faturas retornadas com sucesso.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "token": {"type": "string"},
                        "user_info": {"type": "object"},
                        "faturas": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/FaturaDTO"},
                        },
                    },
                },
            },
            "401": {
                "description": "Falha no login.",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
            },
            "500": {
                "description": "Erro interno.",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                },
            },
        },
        "definitions": {
            "FaturaDTO": {
                "type": "object",
                "properties": {
                    "uc": {"type": "integer"},
                    "mes_ano_referencia": {"type": "string"},
                    "data_vencimento": {"type": "string"},
                    "valor_total": {"type": "number"},
                    "codigo_barras": {"type": ["string", "null"]},
                    "pix": {"type": ["string", "null"]},
                },
            }
        },
    }
)
def faturas_auto_endpoint():
    data = request.get_json()
    required = ["cpf_cnpj", "senha", "consumer_unit", "client_id"]
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Parâmetros obrigatórios ausentes."}), 400

    try:
        session = create_scraper_session(headless=True)
        if not session.autenticar(data["cpf_cnpj"], data["senha"]):
            return jsonify({"error": "Falha no login."}), 401

        token = session.token.valor if session.token else None
        user_info = session.user_info.__dict__ if session.user_info else {}
        faturas = session.obter_faturas(data["consumer_unit"], data["client_id"])
        faturas_list = [f.model_dump(by_alias=True) for f in faturas] if faturas else []

        return (
            jsonify(
                {
                    "status": "success",
                    # "token": token,
                    "user_info": user_info,
                    "faturas": faturas_list,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Erro no endpoint /faturas_auto: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


if __name__ == "__main__":
    print("🤖 Serviço Amazonas Energia API (Refatorado com SOLID)")
    print("📋 Endpoints disponíveis:")
    print("   POST /login - Realizar login")
    print("   GET  /faturas - Obter faturas (requer autenticação)")
    print("   POST /logout - Fazer logout")
    print("   GET  /status - Verificar status da sessão")
    print("   /apidocs - Acessar a documentação Swagger UI")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
