"""
Testes de app/main.py: as rotas de documento (GET /documentos, GET
/documentos/{id}, DELETE /documentos/{id}) e o isolamento por dono
(Etapa 1: "cada usuário acessa apenas os próprios documentos").

test_pipeline.py já prova que eh_dono() está correta isoladamente;
este arquivo prova que main.py de fato liga essa checagem a cada
rota — inclusive POST /perguntas, onde um vazamento seria mais grave.

Mesma condição de pgvector dos outros testes de integração.
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

# a fixture `conexao` vem de tests/conftest.py


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


def _registrar(client: TestClient, email: str, senha: str, sessao_anonima_id: str | None = None) -> str:
    headers = {"X-Sessao-Anonima": sessao_anonima_id} if sessao_anonima_id else {}
    resposta = client.post(
        "/auth/registrar", json={"email": email, "senha": senha}, headers=headers
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["token"]


# --- GET /documentos lista só os do usuário que pergunta ---


def test_listar_documentos_devolve_so_os_do_usuario(conexao):
    with TestClient(app) as client:
        sessao1 = _sessao_anonima()
        doc1 = _subir_documento(client, sessao1)
        token1 = _registrar(client, "usuario1.lista@exemplo.com", "senha12345", sessao1)

        sessao2 = _sessao_anonima()
        doc2 = _subir_documento(client, sessao2)
        token2 = _registrar(client, "usuario2.lista@exemplo.com", "senha12345", sessao2)

        resposta1 = client.get("/documentos", headers={"Authorization": f"Bearer {token1}"})
        resposta2 = client.get("/documentos", headers={"Authorization": f"Bearer {token2}"})

    ids1 = {d["id"] for d in resposta1.json()}
    ids2 = {d["id"] for d in resposta2.json()}

    assert doc1["id"] in ids1 and doc1["id"] not in ids2
    assert doc2["id"] in ids2 and doc2["id"] not in ids1


# --- GET /documentos/{id} de outro usuário: 404, não vaza nem existência ---


def test_documento_de_outro_usuario_devolve_404(conexao):
    with TestClient(app) as client:
        sessao_dono = _sessao_anonima()
        documento = _subir_documento(client, sessao_dono)
        _registrar(client, "dono.isolamento@exemplo.com", "senha12345", sessao_dono)

        # usuário novo, sem nenhuma relação com o documento acima
        token_estranho = _registrar(client, "estranho.isolamento@exemplo.com", "senha12345")

        resposta = client.get(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token_estranho}"},
        )

    assert resposta.status_code == 404


# --- POST /perguntas sobre documento de outro usuário: 404 ---


def test_perguntar_sobre_documento_de_outro_usuario_devolve_404(conexao):
    """
    A checagem de posse vale para POST /perguntas também, não só para
    as rotas de metadado — é aqui que vazar conteúdo de verdade
    aconteceria, não apenas o nome do arquivo.
    """
    with TestClient(app) as client:
        sessao_dono = _sessao_anonima()
        documento = _subir_documento(client, sessao_dono)
        _registrar(client, "dono.pergunta@exemplo.com", "senha12345", sessao_dono)

        token_estranho = _registrar(client, "estranho.pergunta@exemplo.com", "senha12345")

        resposta = client.post(
            "/perguntas",
            json={"documento_id": documento["id"], "pergunta": "qualquer coisa"},
            headers={"Authorization": f"Bearer {token_estranho}"},
        )

    assert resposta.status_code == 404


# --- DELETE /documentos/{id} de outro usuário: 404, e nada é removido ---


def test_deletar_documento_de_outro_usuario_devolve_404_e_nao_remove(conexao):
    with TestClient(app) as client:
        sessao_dono = _sessao_anonima()
        documento = _subir_documento(client, sessao_dono)
        token_dono = _registrar(client, "dono.delete@exemplo.com", "senha12345", sessao_dono)

        token_estranho = _registrar(client, "estranho.delete@exemplo.com", "senha12345")

        resposta_estranho = client.delete(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token_estranho}"},
        )
        assert resposta_estranho.status_code == 404

        # o dono ainda enxerga o documento — nada foi apagado
        resposta_dono = client.get(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token_dono}"},
        )
        assert resposta_dono.status_code == 200


# --- o dono consegue deletar o próprio documento ---


def test_dono_consegue_deletar_o_proprio_documento(conexao):
    with TestClient(app) as client:
        sessao = _sessao_anonima()
        documento = _subir_documento(client, sessao)
        token = _registrar(client, "dono.deleta.mesmo@exemplo.com", "senha12345", sessao)

        resposta_delete = client.delete(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resposta_delete.status_code == 204

        resposta_get = client.get(
            f"/documentos/{documento['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resposta_get.status_code == 404
