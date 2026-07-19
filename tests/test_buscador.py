"""
Testes da Etapa 5 (recuperação): pergunta → chunks mais relevantes.

Precisam de um Postgres real com pgvector — mesma condição de
test_armazenador.py. Pulam (skip) sem essa infraestrutura de pé.

Os 6 cenários seguem a seção 5.10 de docs/documentacao.md, com um
documento pequeno e controlado: um contrato fictício com um assunto
por página, indexado uma vez por teste.
"""

import psycopg
import pytest

from app.config import DATABASE_URL
from app.indexacao import armazenador
from app.recuperacao.buscador import buscar


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

# a fixture `conexao` vem de tests/conftest.py — compartilhada com
# test_armazenador.py (Etapa 4)

DOCUMENTO_ID = 1

CHUNKS_CONTRATO = [
    {
        "indice": 0,
        "pagina": 1,
        "texto": "As partes deste contrato sao a CONTRATANTE e a CONTRATADA, doravante designadas em conjunto as Partes.",
    },
    {
        "indice": 1,
        "pagina": 2,
        "texto": "O aluguel mensal e de tres mil reais, reajustado anualmente pelo indice IGPM.",
    },
    {
        "indice": 2,
        "pagina": 3,
        "texto": "O distrato devera ser comunicado com noventa dias de antecedencia, por escrito, sob pena de multa.",
    },
    {
        "indice": 3,
        "pagina": 4,
        "texto": "A multa por atraso no pagamento sera de dois por cento sobre o valor devido, mais juros de um por cento ao mes.",
    },
    {
        "indice": 4,
        "pagina": 5,
        "texto": "O produto XPT-4472 possui garantia de doze meses a partir da data de compra.",
    },
]


@pytest.fixture
def documento_indexado(conexao):
    armazenador.indexar(conexao, documento_id=DOCUMENTO_ID, chunks=CHUNKS_CONTRATO)
    return conexao


# --- a resposta que está claramente na página X vem no top-k ---


def test_pergunta_direta_recupera_o_chunk_da_pagina_certa(documento_indexado):
    resultado = buscar(documento_indexado, DOCUMENTO_ID, "qual o valor do aluguel mensal?")

    assert any(r["pagina"] == 2 for r in resultado)


# --- assunto ausente do documento -> limiar zera o resultado ---


def test_assunto_ausente_devolve_lista_vazia(documento_indexado):
    resultado = buscar(documento_indexado, DOCUMENTO_ID, "qual a receita de lasanha?")

    assert resultado == []


# --- k limita o número de chunks devolvidos ---


def test_k_limita_a_quantidade_de_chunks(documento_indexado):
    resultado = buscar(
        documento_indexado,
        DOCUMENTO_ID,
        "fale sobre o contrato",
        k=3,
        limiar=2.0,  # limiar solto de propósito: este teste é sobre o k, não sobre relevância
    )

    assert len(resultado) <= 3


# --- resultados vêm ordenados por distância crescente ---


def test_resultados_vem_ordenados_por_distancia_crescente(documento_indexado):
    resultado = buscar(
        documento_indexado, DOCUMENTO_ID, "fale sobre o contrato", limiar=2.0
    )

    distancias = [r["distancia"] for r in resultado]
    assert distancias == sorted(distancias)


# --- sinônimo recupera o trecho certo (prova a busca semântica) ---


def test_sinonimo_recupera_o_trecho_certo(documento_indexado):
    resultado = buscar(
        documento_indexado, DOCUMENTO_ID, "qual o prazo de rescisao do contrato?"
    )

    assert any(r["pagina"] == 3 for r in resultado)


# --- código exato: limitação conhecida da busca semântica (seção 5.6) ---


def test_pergunta_por_codigo_exato_nao_distingue_codigo_parecido(documento_indexado):
    """
    Não há chunk sobre XPT-4471 no documento — só XPT-4472. A busca
    semântica não diferencia os dois (o embedding capta "é um código
    de produto", não qual): o teste prova que o chunk errado (4472)
    ainda assim é devolvido como se fosse relevante para uma pergunta
    sobre 4471. Isso documenta a limitação, não é um bug: é exatamente
    o que a seção 5.6 descreve, e a correção (busca híbrida) está no
    roadmap, não no v1.
    """
    resultado = buscar(
        documento_indexado, DOCUMENTO_ID, "o produto XPT-4471 tem garantia de quanto tempo?"
    )

    assert any(r["pagina"] == 5 for r in resultado)
