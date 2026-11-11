"""
Testes das rotas de conversa em app/main.py: a primeira pergunta abre a
conversa, as seguintes entram no histórico, e tudo é isolado por dono.

Precisam de Postgres real com pgvector — mesma condição dos outros
testes de integração. A LLM é um dublê (devolve uma resposta fixa e as
citações que a busca real recuperou): estes testes são sobre as
conversas, não sobre o que o modelo escreve, e assim rodam rápido e
sem depender de Ollama ou de chave de API.
"""

import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

import app.pipeline as modulo_pipeline
from app.config import DATABASE_URL
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"
PERGUNTA = "com quantos dias de antecedencia o distrato deve ser comunicado?"


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


@pytest.fixture(autouse=True)
def llm_de_mentira(monkeypatch):
    monkeypatch.setattr(
        modulo_pipeline,
        "gerar_resposta",
        lambda pergunta, chunks: {"resposta": "resposta de mentira", "chunks": chunks},
    )


def _subir(client: TestClient, sessao: str, nome: str = "contrato.pdf") -> dict:
    with open(FIXTURES / "texto_simples.pdf", "rb") as arquivo:
        resposta = client.post(
            "/documentos",
            files={"arquivo": (nome, arquivo, "application/pdf")},
            headers={"X-Sessao-Anonima": sessao},
        )
    assert resposta.status_code == 201
    return resposta.json()


def _usuario_com_documentos(client: TestClient, email: str, nomes: list[str]):
    """Sobe os documentos deslogado e cadastra: eles passam para a conta (adoção)."""
    sessao = str(uuid.uuid4())
    documentos = [_subir(client, sessao, nome) for nome in nomes]
    resposta = client.post(
        "/auth/registrar",
        json={"email": email, "senha": "senha12345"},
        headers={"X-Sessao-Anonima": sessao},
    )
    assert resposta.status_code == 201, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['token']}"}, documentos


def _perguntar(client, headers, documento_ids, conversa_id=None, pergunta=PERGUNTA):
    corpo = {"documento_ids": documento_ids, "pergunta": pergunta}
    if conversa_id is not None:
        corpo["conversa_id"] = conversa_id
    return client.post("/perguntas", json=corpo, headers=headers)


# --- a primeira pergunta abre a conversa ---


def test_primeira_pergunta_abre_uma_conversa_e_devolve_o_id(conexao):
    with TestClient(app) as client:
        headers, (doc,) = _usuario_com_documentos(client, "abre@exemplo.com", ["contrato.pdf"])

        resposta = _perguntar(client, headers, [doc["id"]])
        conversas = client.get("/conversas", headers=headers).json()

    assert resposta.status_code == 200
    conversa_id = resposta.json()["conversa_id"]
    assert [c["id"] for c in conversas] == [conversa_id]
    assert [d["nome_original"] for d in conversas[0]["documentos"]] == ["contrato.pdf"]


# --- as perguntas seguintes entram no histórico, com as citações ---


def test_pergunta_com_conversa_id_acrescenta_ao_historico(conexao):
    with TestClient(app) as client:
        headers, (doc,) = _usuario_com_documentos(client, "historico@exemplo.com", ["contrato.pdf"])
        conversa_id = _perguntar(client, headers, [doc["id"]]).json()["conversa_id"]

        segunda = _perguntar(client, headers, [doc["id"]], conversa_id, "outra pergunta?")
        detalhe = client.get(f"/conversas/{conversa_id}", headers=headers).json()

    assert segunda.json()["conversa_id"] == conversa_id
    assert [m["pergunta"] for m in detalhe["mensagens"]] == [PERGUNTA, "outra pergunta?"]
    assert detalhe["mensagens"][0]["resposta"] == "resposta de mentira"
    # a citação foi gravada com o nome do arquivo e a página
    assert detalhe["mensagens"][0]["citacoes"][0]["documento"] == "contrato.pdf"


# --- POST /conversas: a lombada leva TODOS os documentos, mesmo se um não for usado ---


def test_criar_conversa_liga_todos_os_documentos_pedidos(conexao):
    with TestClient(app) as client:
        headers, docs = _usuario_com_documentos(
            client, "dois@exemplo.com", ["contrato.pdf", "aditivo.pdf"]
        )

        criada = client.post(
            "/conversas", json={"documento_ids": [d["id"] for d in docs]}, headers=headers
        )
        # pergunta só sobre um dos dois: o outro continua na conversa
        _perguntar(client, headers, [docs[0]["id"]], criada.json()["id"])
        conversas = client.get("/conversas", headers=headers).json()

    assert criada.status_code == 201
    assert [d["nome_original"] for d in conversas[0]["documentos"]] == ["contrato.pdf", "aditivo.pdf"]


def test_pergunta_sobre_documento_que_nao_e_da_conversa_devolve_400(conexao):
    with TestClient(app) as client:
        headers, (primeiro, segundo) = _usuario_com_documentos(
            client, "fora@exemplo.com", ["contrato.pdf", "aditivo.pdf"]
        )
        conversa_id = _perguntar(client, headers, [primeiro["id"]]).json()["conversa_id"]

        resposta = _perguntar(client, headers, [segundo["id"]], conversa_id)

    assert resposta.status_code == 400


# --- isolamento: a conversa de um usuário não existe para o outro ---


def test_conversa_de_outro_usuario_devolve_404_em_todas_as_rotas(conexao):
    with TestClient(app) as client:
        headers_dono, (doc_dono,) = _usuario_com_documentos(client, "dono@exemplo.com", ["a.pdf"])
        conversa_id = _perguntar(client, headers_dono, [doc_dono["id"]]).json()["conversa_id"]

        headers_estranho, (doc_estranho,) = _usuario_com_documentos(
            client, "estranho@exemplo.com", ["b.pdf"]
        )

        ler = client.get(f"/conversas/{conversa_id}", headers=headers_estranho)
        apagar = client.delete(f"/conversas/{conversa_id}", headers=headers_estranho)
        perguntar = _perguntar(client, headers_estranho, [doc_estranho["id"]], conversa_id)
        lista_estranho = client.get("/conversas", headers=headers_estranho).json()
        # e o dono continua com a conversa intacta
        lista_dono = client.get("/conversas", headers=headers_dono).json()

    assert (ler.status_code, apagar.status_code, perguntar.status_code) == (404, 404, 404)
    assert lista_estranho == []
    assert [c["id"] for c in lista_dono] == [conversa_id]


def test_pergunta_recusada_nao_deixa_conversa_para_tras(conexao):
    """O pedido é recusado antes da LLM: nada pode ter sido gravado."""
    with TestClient(app) as client:
        _, (doc_alheio,) = _usuario_com_documentos(client, "alheio@exemplo.com", ["a.pdf"])
        headers, _ = _usuario_com_documentos(client, "curioso@exemplo.com", ["b.pdf"])

        resposta = _perguntar(client, headers, [doc_alheio["id"]])
        conversas = client.get("/conversas", headers=headers).json()

    assert resposta.status_code == 404
    assert conversas == []


def test_rotas_de_conversa_exigem_login(conexao):
    with TestClient(app) as client:
        assert client.get("/conversas").status_code == 401
        assert client.post("/conversas", json={"documento_ids": [1]}).status_code == 401
        assert client.get("/conversas/1").status_code == 401
        assert client.delete("/conversas/1").status_code == 401


# --- apagar: a conversa leva as mensagens e os documentos que só ela usava ---


def test_apagar_conversa_remove_mensagens_e_documentos(conexao):
    with TestClient(app) as client:
        headers, (doc,) = _usuario_com_documentos(client, "apaga@exemplo.com", ["contrato.pdf"])
        conversa_id = _perguntar(client, headers, [doc["id"]]).json()["conversa_id"]

        apagar = client.delete(f"/conversas/{conversa_id}", headers=headers)
        conversas = client.get("/conversas", headers=headers).json()
        documento = client.get(f"/documentos/{doc['id']}", headers=headers)

    assert apagar.status_code == 204
    assert conversas == []
    assert documento.status_code == 404


def test_remover_o_ultimo_documento_apaga_a_conversa(conexao):
    with TestClient(app) as client:
        headers, (doc,) = _usuario_com_documentos(client, "ultimo@exemplo.com", ["contrato.pdf"])
        _perguntar(client, headers, [doc["id"]])

        remover = client.delete(f"/documentos/{doc['id']}", headers=headers)
        conversas = client.get("/conversas", headers=headers).json()

    assert remover.status_code == 204
    assert conversas == []


def test_remover_um_dos_dois_documentos_mantem_a_conversa_e_o_historico(conexao):
    with TestClient(app) as client:
        headers, (primeiro, segundo) = _usuario_com_documentos(
            client, "um-de-dois@exemplo.com", ["contrato.pdf", "aditivo.pdf"]
        )
        conversa_id = _perguntar(client, headers, [primeiro["id"], segundo["id"]]).json()["conversa_id"]

        client.delete(f"/documentos/{primeiro['id']}", headers=headers)
        detalhe = client.get(f"/conversas/{conversa_id}", headers=headers).json()

    assert [d["nome_original"] for d in detalhe["documentos"]] == ["aditivo.pdf"]
    assert len(detalhe["mensagens"]) == 1


# --- ampliar o conhecimento: acrescentar um documento a uma conversa que já existe ---


def test_acrescentar_documento_a_conversa_existente(conexao):
    with TestClient(app) as client:
        headers, (primeiro, segundo) = _usuario_com_documentos(
            client, "amplia@exemplo.com", ["contrato.pdf", "aditivo.pdf"]
        )
        conversa_id = _perguntar(client, headers, [primeiro["id"]]).json()["conversa_id"]

        acrescentou = client.post(
            f"/conversas/{conversa_id}/documentos",
            json={"documento_id": segundo["id"]},
            headers=headers,
        )
        # agora uma pergunta pode valer para os dois
        pergunta = _perguntar(client, headers, [primeiro["id"], segundo["id"]], conversa_id)

    assert acrescentou.status_code == 200
    assert [d["nome_original"] for d in acrescentou.json()["documentos"]] == [
        "contrato.pdf",
        "aditivo.pdf",
    ]
    assert pergunta.status_code == 200


def test_acrescentar_um_terceiro_documento_devolve_400(conexao):
    with TestClient(app) as client:
        headers, (a, b, c) = _usuario_com_documentos(
            client, "terceiro@exemplo.com", ["a.pdf", "b.pdf", "c.pdf"]
        )
        conversa = client.post(
            "/conversas", json={"documento_ids": [a["id"], b["id"]]}, headers=headers
        ).json()

        resposta = client.post(
            f"/conversas/{conversa['id']}/documentos", json={"documento_id": c["id"]}, headers=headers
        )

    assert resposta.status_code == 400


def test_acrescentar_documento_de_outro_usuario_devolve_404(conexao):
    with TestClient(app) as client:
        _, (doc_alheio,) = _usuario_com_documentos(client, "dono.doc@exemplo.com", ["a.pdf"])
        headers, (meu,) = _usuario_com_documentos(client, "intruso@exemplo.com", ["b.pdf"])
        conversa_id = _perguntar(client, headers, [meu["id"]]).json()["conversa_id"]

        resposta = client.post(
            f"/conversas/{conversa_id}/documentos",
            json={"documento_id": doc_alheio["id"]},
            headers=headers,
        )

    assert resposta.status_code == 404


def test_acrescentar_o_mesmo_documento_de_novo_nao_duplica(conexao):
    with TestClient(app) as client:
        headers, (doc,) = _usuario_com_documentos(client, "repete@exemplo.com", ["a.pdf"])
        conversa_id = _perguntar(client, headers, [doc["id"]]).json()["conversa_id"]

        resposta = client.post(
            f"/conversas/{conversa_id}/documentos", json={"documento_id": doc["id"]}, headers=headers
        )

    assert resposta.status_code == 200
    assert len(resposta.json()["documentos"]) == 1
