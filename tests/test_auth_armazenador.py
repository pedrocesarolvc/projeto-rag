"""
Testes de app/auth/armazenador.py: usuários e adoção de documentos da
sessão anônima (Etapa 7, seção 7.3). Mesma condição dos outros testes
de integração: pulam sem Postgres com pgvector — armazenador.conectar()
sempre tenta habilitar a extensão, mesmo para as tabelas de conta.
"""

import psycopg
import pytest

from app.auth import armazenador as auth_armazenador
from app.config import DATABASE_URL
from app.indexacao import armazenador


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


# --- criar e buscar usuário ---


def test_criar_usuario_e_buscar_por_email(conexao):
    usuario_id = auth_armazenador.criar_usuario(conexao, "achado@exemplo.com", "hash-qualquer")
    conexao.commit()

    usuario = auth_armazenador.buscar_usuario_por_email(conexao, "achado@exemplo.com")

    assert usuario is not None
    assert usuario["id"] == usuario_id
    assert usuario["email"] == "achado@exemplo.com"


def test_buscar_usuario_inexistente_devolve_none(conexao):
    assert auth_armazenador.buscar_usuario_por_email(conexao, "ninguem@exemplo.com") is None


# --- adoção da sessão anônima (seção 7.3) ---


def test_adotar_documentos_move_so_os_daquela_sessao(conexao):
    usuario_id = auth_armazenador.criar_usuario(conexao, "dono@exemplo.com", "hash")
    conexao.commit()

    doc_da_sessao = armazenador.criar_documento(
        conexao, "meu.pdf", sessao_anonima_id="sessao-a"
    )
    doc_de_outra_sessao = armazenador.criar_documento(
        conexao, "outro.pdf", sessao_anonima_id="sessao-b"
    )

    auth_armazenador.adotar_documentos_da_sessao(conexao, "sessao-a", usuario_id)
    conexao.commit()

    adotado = armazenador.buscar_documento(conexao, doc_da_sessao)
    nao_adotado = armazenador.buscar_documento(conexao, doc_de_outra_sessao)

    assert adotado["usuario_id"] == usuario_id
    assert nao_adotado["usuario_id"] is None


def test_adotar_nao_rouba_documento_que_ja_tem_dono(conexao):
    """
    Seção 7.3: "a sessão anônima só entrega o que é dela". Um
    documento já adotado por um usuário não pode ser adotado de novo
    por outro, mesmo reaproveitando (ou forjando) o mesmo token de
    sessão anônima.
    """
    usuario1 = auth_armazenador.criar_usuario(conexao, "primeiro@exemplo.com", "hash")
    usuario2 = auth_armazenador.criar_usuario(conexao, "segundo@exemplo.com", "hash")
    conexao.commit()

    documento_id = armazenador.criar_documento(
        conexao, "doc.pdf", sessao_anonima_id="sessao-x"
    )
    auth_armazenador.adotar_documentos_da_sessao(conexao, "sessao-x", usuario1)
    conexao.commit()

    auth_armazenador.adotar_documentos_da_sessao(conexao, "sessao-x", usuario2)
    conexao.commit()

    documento = armazenador.buscar_documento(conexao, documento_id)
    assert documento["usuario_id"] == usuario1
