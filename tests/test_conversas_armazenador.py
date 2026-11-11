"""
Testes de app/conversas/armazenador.py: criar, listar, registrar
mensagens e as duas formas de apagar (a conversa inteira, ou um
documento que sai de dentro dela).

Precisam de Postgres real com pgvector — mesma condição dos outros
testes de integração. Pulam sem essa infraestrutura de pé.
"""

import psycopg
import pytest

from app.config import DATABASE_URL
from app.conversas import armazenador as conversas
from app.indexacao import armazenador as documentos_armazenador


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


def _documento(conexao, nome: str, usuario_id: int = 1) -> int:
    return documentos_armazenador.criar_documento(conexao, nome, usuario_id=usuario_id)


# --- criar e ler: os documentos vêm na ordem em que foram dados ---


def test_conversa_guarda_os_documentos_na_ordem_dada(conexao):
    primeiro = _documento(conexao, "contrato.pdf")
    segundo = _documento(conexao, "aditivo.pdf")

    conversa_id = conversas.criar_conversa(conexao, 1, [segundo, primeiro])
    conexao.commit()

    conversa = conversas.buscar_conversa(conexao, conversa_id)
    assert conversa["usuario_id"] == 1
    assert [d["nome_original"] for d in conversa["documentos"]] == ["aditivo.pdf", "contrato.pdf"]


def test_buscar_conversa_inexistente_devolve_none(conexao):
    assert conversas.buscar_conversa(conexao, 999999) is None


# --- listar: só as do usuário, da mais antiga para a mais nova ---


def test_listar_devolve_so_as_do_usuario_em_ordem_de_criacao(conexao):
    doc_a = _documento(conexao, "a.pdf", usuario_id=1)
    doc_b = _documento(conexao, "b.pdf", usuario_id=1)
    doc_c = _documento(conexao, "c.pdf", usuario_id=2)
    primeira = conversas.criar_conversa(conexao, 1, [doc_a])
    conversas.criar_conversa(conexao, 2, [doc_c])
    segunda = conversas.criar_conversa(conexao, 1, [doc_b])
    conexao.commit()

    ids = [c["id"] for c in conversas.listar_conversas(conexao, 1)]

    assert ids == [primeira, segunda]


# --- mensagens: gravadas em ordem, com as citações intactas ---


def test_mensagens_voltam_em_ordem_com_as_citacoes(conexao):
    doc = _documento(conexao, "contrato.pdf")
    conversa_id = conversas.criar_conversa(conexao, 1, [doc])
    citacoes = [{"documento": "contrato.pdf", "pagina": 2, "texto": "trecho", "distancia": 0.31}]

    conversas.registrar_mensagem(conexao, conversa_id, "primeira?", "resposta 1", citacoes)
    conversas.registrar_mensagem(conexao, conversa_id, "segunda?", "resposta 2", [])
    conexao.commit()

    mensagens = conversas.listar_mensagens(conexao, conversa_id)
    assert [m["pergunta"] for m in mensagens] == ["primeira?", "segunda?"]
    assert mensagens[0]["citacoes"] == citacoes
    assert mensagens[1]["citacoes"] == []


# --- apagar a conversa: leva as mensagens e só os documentos exclusivos ---


def test_remover_conversa_apaga_mensagens_e_devolve_so_os_documentos_exclusivos(conexao):
    exclusivo = _documento(conexao, "so-dela.pdf")
    compartilhado = _documento(conexao, "dividido.pdf")
    conversa_id = conversas.criar_conversa(conexao, 1, [exclusivo, compartilhado])
    outra = conversas.criar_conversa(conexao, 1, [compartilhado])
    conversas.registrar_mensagem(conexao, conversa_id, "p", "r", [])
    conexao.commit()

    sem_conversa = conversas.remover_conversa(conexao, conversa_id)
    conexao.commit()

    # o compartilhado continua numa conversa viva, então não é devolvido
    assert sem_conversa == [exclusivo]
    assert conversas.buscar_conversa(conexao, conversa_id) is None
    assert conversas.listar_mensagens(conexao, conversa_id) == []
    assert conversas.buscar_conversa(conexao, outra) is not None


# --- tirar um documento: a conversa fica, a menos que fique vazia ---


def test_desvincular_documento_mantem_a_conversa_que_ainda_tem_outro(conexao):
    a = _documento(conexao, "a.pdf")
    b = _documento(conexao, "b.pdf")
    conversa_id = conversas.criar_conversa(conexao, 1, [a, b])
    conversas.registrar_mensagem(conexao, conversa_id, "p", "r", [])
    conexao.commit()

    conversas.desvincular_documento(conexao, a)
    conexao.commit()

    conversa = conversas.buscar_conversa(conexao, conversa_id)
    assert [d["id"] for d in conversa["documentos"]] == [b]
    assert len(conversas.listar_mensagens(conexao, conversa_id)) == 1


def test_desvincular_o_ultimo_documento_apaga_a_conversa_e_as_mensagens(conexao):
    doc = _documento(conexao, "unico.pdf")
    conversa_id = conversas.criar_conversa(conexao, 1, [doc])
    conversas.registrar_mensagem(conexao, conversa_id, "p", "r", [])
    conexao.commit()

    conversas.desvincular_documento(conexao, doc)
    conexao.commit()

    assert conversas.buscar_conversa(conexao, conversa_id) is None
    assert conversas.listar_mensagens(conexao, conversa_id) == []
