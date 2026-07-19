"""
Testes da Etapa 4 (indexação): armazenamento no PostgreSQL.

Precisam de um Postgres real com a extensão pgvector disponível — ver
.env.example. Pulam (skip) se DATABASE_URL não estiver configurada,
o banco não estiver alcançável, ou a extensão vector não estiver
instalada no servidor, em vez de falhar: a suíte continua
reproduzível para quem clonar o projeto sem ter essa infraestrutura
de pé (pgvector, em particular, não é trivial de instalar no Windows
sem Docker — ver docs/documentacao.md, Etapa 4).
"""

import psycopg
import pytest

from app.config import DATABASE_URL
from app.indexacao import armazenador
from app.indexacao.embedder import gerar_embeddings


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
# test_buscador.py (Etapa 5)


# --- inserir e recuperar um vetor do Postgres devolve o mesmo vetor ---


def test_inserir_e_recuperar_devolve_o_mesmo_vetor(conexao):
    chunks = [{"indice": 0, "pagina": 1, "texto": "um texto qualquer para indexar"}]
    vetor_esperado = gerar_embeddings([chunks[0]["texto"]])[0]

    armazenador.indexar(conexao, documento_id=1, chunks=chunks)

    with conexao.cursor() as cursor:
        cursor.execute("SELECT vetor FROM chunks WHERE documento_id = 1")
        (vetor_salvo,) = cursor.fetchone()

    assert list(vetor_salvo) == pytest.approx(vetor_esperado, abs=1e-5)


# --- a query de distância devolve os chunks na ordem esperada ---


def test_query_de_distancia_devolve_chunks_na_ordem_esperada(conexao):
    chunks = [
        {"indice": 0, "pagina": 1, "texto": "O prazo de rescisao e de 90 dias."},
        {"indice": 1, "pagina": 1, "texto": "Segue a receita de bolo de fuba."},
        {
            "indice": 2,
            "pagina": 1,
            "texto": "O distrato deve ser comunicado com antecedencia.",
        },
    ]
    armazenador.indexar(conexao, documento_id=1, chunks=chunks)

    vetor_pergunta = gerar_embeddings(["qual o prazo de rescisao do contrato?"])[0]

    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT texto FROM chunks ORDER BY vetor <=> %s LIMIT 3",
            (vetor_pergunta,),
        )
        resultados = [linha[0] for linha in cursor.fetchall()]

    # os dois chunks sobre rescisão/distrato vêm antes da receita de bolo,
    # que não tem nada a ver com a pergunta
    assert set(resultados[:2]) == {chunks[0]["texto"], chunks[2]["texto"]}
    assert resultados[2] == chunks[1]["texto"]
