"""
Lastro — Etapa 7: autenticação, sem tocar no banco.

Duas responsabilidades, sem misturar: hash de senha (bcrypt) e
emissão/verificação de token de sessão (JWT). Nenhuma consulta ao
banco mora aqui — isso é auth/armazenador.py, ao lado. A mesma
separação que o projeto já aplica em todo lugar: uma coisa faz uma
coisa.

O cadastro adiado (seção 1.5) é a razão de este módulo existir: sem
autenticação não haveria o que "adiar" na Etapa 7, seção 7.3.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import SECRET_KEY

ALGORITMO = "HS256"
EXPIRACAO_TOKEN = timedelta(days=7)


def _chave_secreta() -> str:
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY não configurada — defina no .env (ver .env.example)."
        )
    return SECRET_KEY


def hash_senha(senha: str) -> str:
    """Nunca se guarda a senha em texto puro — só o hash, com salt embutido."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Compara a senha em texto puro contra o hash guardado no banco."""
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def gerar_token(usuario_id: int) -> str:
    """
    O token carrega só o id do usuário e a expiração — sem estado
    guardado no servidor (sem tabela de sessões). Simples de propósito:
    o v1 não precisa revogar tokens antes da expiração.
    """
    payload = {
        "sub": str(usuario_id),
        "exp": datetime.now(timezone.utc) + EXPIRACAO_TOKEN,
    }
    return jwt.encode(payload, _chave_secreta(), algorithm=ALGORITMO)


def decodificar_token(token: str) -> int | None:
    """
    Devolve o usuario_id se o token for válido e não tiver expirado;
    None em qualquer outro caso — nunca levanta exceção. Quem decide
    se autenticação era obrigatória é a rota (ver main.py), não esta
    função.
    """
    try:
        payload = jwt.decode(token, _chave_secreta(), algorithms=[ALGORITMO])
        return int(payload["sub"])
    except jwt.InvalidTokenError:
        return None
