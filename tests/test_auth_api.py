"""
Testes de app/main.py: as rotas POST /auth/registrar e POST
/auth/login em si — e-mail duplicado, senha errada, e a corrida entre
dois cadastros simultâneos com o mesmo e-mail.

Mesma condição de pgvector dos outros testes de integração (a rota
abre conexão via armazenador.conectar(), que sempre tenta habilitar
a extensão).
"""

import psycopg
import pytest
from fastapi.testclient import TestClient

import app.main as modulo_main
from app.config import DATABASE_URL
from app.main import app


def _pgvector_disponivel() -> bool:
    if not DATABASE_URL:
        return False
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conexao:
            resultado = conexao.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
            ).fetchone()
            return resultado is not None
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _pgvector_disponivel(),
    reason="DATABASE_URL não configurada, Postgres inalcançável, ou extensão vector não instalada",
)

# a fixture `conexao` vem de tests/conftest.py


# --- e-mail duplicado: 409, não 500 ---


def test_registrar_com_email_ja_cadastrado_devolve_409(conexao):
    with TestClient(app) as client:
        client.post(
            "/auth/registrar",
            json={"email": "duplicado@exemplo.com", "senha": "senha12345"},
        )
        resposta = client.post(
            "/auth/registrar",
            json={"email": "duplicado@exemplo.com", "senha": "outrasenha123"},
        )

    assert resposta.status_code == 409


# --- a mesma corrida, mas pela restrição do banco, não pela checagem prévia ---


def test_corrida_de_dois_cadastros_com_o_mesmo_email_tambem_devolve_409(conexao, monkeypatch):
    """
    Simula a janela de corrida: os dois cadastros passam pela checagem
    de "e-mail já existe" (aqui, forçada a sempre dizer "não existe")
    antes de qualquer um commitar. O segundo INSERT esbarra na
    restrição UNIQUE do Postgres — e main.py precisa converter isso
    em 409, não deixar vazar como 500.
    """
    monkeypatch.setattr(
        modulo_main.auth_armazenador, "buscar_usuario_por_email", lambda *_: None
    )

    with TestClient(app) as client:
        primeira = client.post(
            "/auth/registrar",
            json={"email": "corrida@exemplo.com", "senha": "senha12345"},
        )
        segunda = client.post(
            "/auth/registrar",
            json={"email": "corrida@exemplo.com", "senha": "outrasenha123"},
        )

    assert primeira.status_code == 201
    assert segunda.status_code == 409


# --- login com senha errada: 401 ---


def test_login_com_senha_errada_devolve_401(conexao):
    with TestClient(app) as client:
        client.post(
            "/auth/registrar",
            json={"email": "senha.errada@exemplo.com", "senha": "senha-certa-123"},
        )
        resposta = client.post(
            "/auth/login",
            json={"email": "senha.errada@exemplo.com", "senha": "senha-errada-123"},
        )

    assert resposta.status_code == 401


# --- login com e-mail que não existe: 401 (não 404 — não revela se o e-mail existe) ---


def test_login_com_email_inexistente_devolve_401(conexao):
    with TestClient(app) as client:
        resposta = client.post(
            "/auth/login",
            json={"email": "ninguem.aqui@exemplo.com", "senha": "qualquer-coisa"},
        )

    assert resposta.status_code == 401
