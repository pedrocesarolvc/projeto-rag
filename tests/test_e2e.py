"""
Testes de ponta a ponta (Etapa 7, seção 7.5): sobem o pipeline
inteiro, do upload à resposta, através da API real (TestClient) —
as duas rotas amarradas, não as funções isoladas.

Precisam de Postgres com pgvector (mesma condição dos outros testes
de integração) e do Ollama rodando com o modelo baixado — são os
testes mais "caros" da suíte, e os únicos que tocam a LLM de
verdade. Por isso verificam propriedades da resposta (menciona o
fato certo, cita a página certa), não a string exata: a saída da LLM
não é determinística (seções 6.10 e 7.5).
"""

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


def _subir_documento(client: TestClient) -> dict:
    with open(FIXTURES / "texto_simples.pdf", "rb") as arquivo:
        resposta = client.post(
            "/documentos",
            files={"arquivo": ("contrato.pdf", arquivo, "application/pdf")},
        )
    assert resposta.status_code == 201
    return resposta.json()


# --- pergunta com resposta conhecida: a resposta bate e cita a página certa ---


def test_pergunta_com_resposta_conhecida_bate_e_cita_a_pagina_certa(conexao):
    with TestClient(app) as client:
        documento = _subir_documento(client)
        assert documento["status"] == "pronto"

        resposta = client.post(
            "/perguntas",
            json={
                "documento_id": documento["id"],
                "pergunta": "com quantos dias de antecedencia o distrato deve ser comunicado?",
            },
        )

    assert resposta.status_code == 200
    corpo = resposta.json()

    assert "90" in corpo["resposta"]
    assert any(citacao["pagina"] == 1 for citacao in corpo["citacoes"])


# --- pergunta fora do documento: o sistema admite que não sabe ---


def test_pergunta_fora_do_documento_admite_que_nao_sabe(conexao):
    with TestClient(app) as client:
        documento = _subir_documento(client)

        resposta = client.post(
            "/perguntas",
            json={
                "documento_id": documento["id"],
                "pergunta": "qual a receita de lasanha?",
            },
        )

    assert resposta.status_code == 200
    corpo = resposta.json()

    # o limiar da Etapa 5 já barra o contexto irrelevante — sem
    # citação nenhuma, o grounding da Etapa 6 não tem de onde inventar
    assert corpo["citacoes"] == []
