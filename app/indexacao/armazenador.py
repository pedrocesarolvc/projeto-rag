"""
Etapa 4 — Indexação: armazenamento no PostgreSQL.

Recebe os chunks da Etapa 3, gera o embedding de cada um (embedder.py)
e grava tudo na tabela `chunks` — o último passo da fase de indexação
(seção 4.1 de docs/documentacao.md). Texto e vetor ficam lado a lado
de propósito: o vetor serve para achar; o texto, para usar na
citação e no prompt (seção 4.9).

Sem framework de migração no v1: uma tabela, um DDL, direto — o mesmo
espírito de "sem LangChain" aplicado ao lado do banco.
"""

import psycopg
from pgvector.psycopg import register_vector

from app.config import DATABASE_URL
from app.indexacao.embedder import DIMENSAO, gerar_embeddings


def conectar() -> psycopg.Connection:
    """
    Abre a conexão, garante a extensão pgvector (seção 4.7) e registra
    o adaptador que converte `list[float]` <-> `vector` do Postgres.
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL não configurada — defina no .env (ver .env.example)."
        )
    conexao = psycopg.connect(DATABASE_URL, autocommit=False)
    conexao.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conexao.commit()
    register_vector(conexao)
    return conexao


def criar_tabela(conexao: psycopg.Connection) -> None:
    """
    Cria a tabela `chunks` (seção 4.9) se ainda não existir. A
    dimensão do vetor vem de embedder.DIMENSAO — nunca um número
    solto repetido aqui, para que coluna e modelo nunca possam
    divergir silenciosamente (seção 4.6: dimensão errada estoura na
    primeira inserção).
    """
    conexao.execute(
        f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id           BIGSERIAL PRIMARY KEY,
            documento_id BIGINT NOT NULL,
            indice       INT NOT NULL,
            pagina       INT NOT NULL,
            texto        TEXT NOT NULL,
            vetor        VECTOR({DIMENSAO}) NOT NULL
        )
        """
    )
    conexao.commit()


def indexar(conexao: psycopg.Connection, documento_id: int, chunks: list[dict]) -> None:
    """
    Gera o embedding de cada chunk e grava tudo na tabela `chunks`.

    `chunks` é exatamente o contrato da Etapa 3:
    `[{"indice": int, "pagina": int, "texto": str}, ...]`.
    """
    if not chunks:
        return

    vetores = gerar_embeddings([chunk["texto"] for chunk in chunks])

    with conexao.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO chunks (documento_id, indice, pagina, texto, vetor)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (documento_id, chunk["indice"], chunk["pagina"], chunk["texto"], vetor)
                for chunk, vetor in zip(chunks, vetores)
            ],
        )
    conexao.commit()
