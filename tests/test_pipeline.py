"""
Testes de app/pipeline.py: eh_dono() — a regra de acesso do v1
("cada usuário acessa apenas os próprios documentos", Etapa 1) — e a
costura de responder_pergunta() entre a busca e a geração. Sem banco:
a busca e a LLM são dublês.
"""

from unittest.mock import MagicMock

import app.pipeline as modulo_pipeline
from app.pipeline import eh_dono, responder_pergunta


def test_dono_por_usuario_bate():
    documento = {"usuario_id": 5, "sessao_anonima_id": None}

    assert eh_dono(documento, usuario_id=5, sessao_anonima_id=None) is True


def test_usuario_diferente_nao_e_dono():
    documento = {"usuario_id": 5, "sessao_anonima_id": None}

    assert eh_dono(documento, usuario_id=6, sessao_anonima_id=None) is False


def test_dono_por_sessao_anonima_bate():
    documento = {"usuario_id": None, "sessao_anonima_id": "abc"}

    assert eh_dono(documento, usuario_id=None, sessao_anonima_id="abc") is True


def test_sessao_anonima_diferente_nao_e_dona():
    documento = {"usuario_id": None, "sessao_anonima_id": "abc"}

    assert eh_dono(documento, usuario_id=None, sessao_anonima_id="xyz") is False


def test_documento_adotado_nao_responde_mais_a_sessao_anonima_antiga():
    """
    Depois da adoção (seção 7.3), o dono é o usuário — a sessão
    anônima que fez o upload original perde o acesso.
    """
    documento = {"usuario_id": 5, "sessao_anonima_id": "abc"}

    assert eh_dono(documento, usuario_id=None, sessao_anonima_id="abc") is False


# --- responder_pergunta: id do documento vira nome do arquivo antes da geração ---


def test_responder_pergunta_acrescenta_o_nome_do_documento_aos_chunks(monkeypatch):
    """
    A Etapa 5 só devolve `documento_id` por chunk; o prompt e a citação
    precisam do NOME. É responder_pergunta() quem faz essa tradução —
    sem ela, a geração receberia chunks sem o campo `documento`.
    """
    buscar_fake = MagicMock(
        return_value=[
            {"documento_id": 20, "pagina": 1, "texto": "do aditivo", "distancia": 0.1},
            {"documento_id": 10, "pagina": 3, "texto": "do contrato", "distancia": 0.2},
        ]
    )
    gerar_fake = MagicMock(return_value={"resposta": "ok", "chunks": []})
    monkeypatch.setattr(modulo_pipeline, "buscar", buscar_fake)
    monkeypatch.setattr(modulo_pipeline, "gerar_resposta", gerar_fake)

    documentos = [
        {"id": 10, "nome_original": "contrato.pdf"},
        {"id": 20, "nome_original": "aditivo.pdf"},
    ]
    responder_pergunta(MagicMock(), documentos, "pergunta qualquer")

    _, chunks_enviados = gerar_fake.call_args[0]
    assert [c["documento"] for c in chunks_enviados] == ["aditivo.pdf", "contrato.pdf"]


def test_responder_pergunta_busca_em_todos_os_documentos_pedidos(monkeypatch):
    buscar_fake = MagicMock(return_value=[])
    monkeypatch.setattr(modulo_pipeline, "buscar", buscar_fake)
    monkeypatch.setattr(
        modulo_pipeline, "gerar_resposta", MagicMock(return_value={"resposta": "", "chunks": []})
    )

    documentos = [
        {"id": 10, "nome_original": "contrato.pdf"},
        {"id": 20, "nome_original": "aditivo.pdf"},
    ]
    responder_pergunta(MagicMock(), documentos, "pergunta qualquer")

    _, ids_buscados, _ = buscar_fake.call_args[0]
    assert ids_buscados == [10, 20]
