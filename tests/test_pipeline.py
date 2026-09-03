"""
Testes de app/pipeline.py: eh_dono() — a regra de acesso do v1
("cada usuário acessa apenas os próprios documentos", Etapa 1).
Função pura, sem banco.
"""

from app.pipeline import eh_dono


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
