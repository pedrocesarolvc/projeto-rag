"""
Testes de ponta a ponta (Etapa 7, seções 7.5 e 7.6): sobem o pipeline
inteiro, do upload à resposta, através da API real (TestClient) —
as rotas amarradas, não as funções isoladas.

Precisam de Postgres com pgvector (mesma condição dos outros testes
de integração) e do Ollama rodando com o modelo baixado — são os
testes mais "caros" da suíte, e os únicos que tocam a LLM de
verdade. Por isso verificam propriedades da resposta (menciona o
fato certo, cita a página certa), não a string exata: a saída da LLM
não é determinística (seções 6.10 e 7.5).

POST /perguntas exige conta (seção 7.2) — todo teste que pergunta
precisa autenticar antes. Os dois últimos testes cobrem a adoção da
sessão anônima (seção 7.3): documento enviado antes do cadastro/login
continua acessível depois.
"""

import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import DATABASE_URL
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


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

# a fixture `conexao` vem de tests/conftest.py — usada aqui só para
# garantir tabelas limpas antes/depois; as rotas abrem suas próprias
# conexões, como fazem em produção.


def _sessao_anonima() -> str:
    return str(uuid.uuid4())


def _subir_documento(client: TestClient, sessao_anonima_id: str) -> dict:
    with open(FIXTURES / "texto_simples.pdf", "rb") as arquivo:
        resposta = client.post(
            "/documentos",
            files={"arquivo": ("contrato.pdf", arquivo, "application/pdf")},
            headers={"X-Sessao-Anonima": sessao_anonima_id},
        )
    assert resposta.status_code == 201
    return resposta.json()


def _registrar(
    client: TestClient, email: str, senha: str, sessao_anonima_id: str | None = None
) -> str:
    headers = {"X-Sessao-Anonima": sessao_anonima_id} if sessao_anonima_id else {}
    resposta = client.post(
        "/auth/registrar", json={"email": email, "senha": senha}, headers=headers
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["token"]


def _login(
    client: TestClient, email: str, senha: str, sessao_anonima_id: str | None = None
) -> str:
    headers = {"X-Sessao-Anonima": sessao_anonima_id} if sessao_anonima_id else {}
    resposta = client.post(
        "/auth/login", json={"email": email, "senha": senha}, headers=headers
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["token"]


# --- pergunta com resposta conhecida: a resposta bate e cita a página certa ---


def test_pergunta_com_resposta_conhecida_bate_e_cita_a_pagina_certa(conexao):
    sessao = _sessao_anonima()
    with TestClient(app) as client:
        documento = _subir_documento(client, sessao)
        assert documento["status"] == "pronto"

        token = _registrar(client, "resposta.conhecida@exemplo.com", "senha12345", sessao)

        resposta = client.post(
            "/perguntas",
            json={
                "documento_id": documento["id"],
                "pergunta": "com quantos dias de antecedencia o distrato deve ser comunicado?",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()

    assert "90" in corpo["resposta"]
    assert any(citacao["pagina"] == 1 for citacao in corpo["citacoes"])


# --- pergunta fora do documento: o sistema admite que não sabe ---


def test_pergunta_fora_do_documento_admite_que_nao_sabe(conexao):
    sessao = _sessao_anonima()
    with TestClient(app) as client:
        documento = _subir_documento(client, sessao)
        token = _registrar(client, "fora.do.documento@exemplo.com", "senha12345", sessao)

        resposta = client.post(
            "/perguntas",
            json={
                "documento_id": documento["id"],
                "pergunta": "qual a receita de lasanha?",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()

    # o limiar da Etapa 5 já barra o contexto irrelevante — sem
    # citação nenhuma, o grounding da Etapa 6 não tem de onde inventar
    assert corpo["citacoes"] == []


# --- adoção da sessão anônima: cadastro ---


def test_documento_anonimo_continua_acessivel_apos_cadastro(conexao):
    """
    Seção 7.6, terceiro teste: sobe um documento deslogado, cadastra,
    e confirma que o documento continua acessível na conta nova — a
    adoção da seção 7.3 funcionando de ponta a ponta.
    """
    sessao = _sessao_anonima()
    with TestClient(app) as client:
        documento = _subir_documento(client, sessao)

        token = _registrar(client, "adocao.cadastro@exemplo.com", "senha12345", sessao)

        resposta = client.get(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == documento["id"]


# --- adoção da sessão anônima: login (não só cadastro) ---


def test_documento_anonimo_continua_acessivel_apos_login(conexao):
    """
    O par do teste acima: a conta já existia (o usuário se cadastrou
    antes, sem sessão anônima associada), fez upload deslogado depois,
    e recupera o documento fazendo login — não só no cadastro.
    """
    email, senha = "adocao.login@exemplo.com", "senha12345"

    with TestClient(app) as client:
        client.post("/auth/registrar", json={"email": email, "senha": senha})

        sessao = _sessao_anonima()
        documento = _subir_documento(client, sessao)

        token = _login(client, email, senha, sessao)

        resposta = client.get(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == documento["id"]
