"""
Etapa 4 — Indexação: armazenamento no PostgreSQL.

Recebe os chunks da Etapa 3, gera o embedding de cada um (embedder.py)
e grava tudo na tabela `chunks` — o último passo da fase de indexação
(seção 4.1 de docs/documentacao.md). Texto e vetor ficam lado a lado
de propósito: o vetor serve para achar; o texto, para usar na
citação e no prompt (seção 4.9).

Sem framework de migração no v1: duas tabelas, um DDL, direto — o
mesmo espírito de "sem LangChain" aplicado ao lado do banco. Preço
real desse trade-off, visto na prática: `CREATE TABLE IF NOT EXISTS`
não altera uma tabela que já existe com um schema mais antigo — se
uma coluna nova (como `usuario_id`, da Etapa 7) for adicionada aqui,
um banco que já rodou uma versão anterior do código não a ganha
sozinho. Em desenvolvimento, o remédio é recriar o volume do Postgres;
um projeto com dado real em produção precisaria de uma migração de
verdade — e é exatamente esse o motivo de "sem migração" ser uma
decisão do v1, não um esquecimento.

Etapa 7: a tabela `documentos` nasce aqui, não antes — `chunks.documento_id`
sempre existiu no contrato (seção 4.9), mas só a API precisa de um
lugar para guardar o nome original do arquivo, o status
(indexando/pronto/falhou) e o dono de cada upload (seção 7.2).

O dono é `usuario_id` OU `sessao_anonima_id`, nunca os dois ao mesmo
tempo até o cadastro adiado (seção 1.5) resolver a ambiguidade: todo
documento nasce com `sessao_anonima_id` e `usuario_id` nulo; no
cadastro ou login, `usuario_id` é preenchido (seção 7.3, em
app/auth/armazenador.py) e o documento passa a pertencer à conta.
"""

import psycopg
from pgvector import Vector
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


def criar_tabelas(conexao: psycopg.Connection) -> None:
    """
    Cria as tabelas `documentos` e `chunks` (seção 4.9) se ainda não
    existirem. A dimensão do vetor vem de embedder.DIMENSAO — nunca um
    número solto repetido aqui, para que coluna e modelo nunca possam
    divergir silenciosamente (seção 4.6: dimensão errada estoura na
    primeira inserção).
    """
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS documentos (
            id                BIGSERIAL PRIMARY KEY,
            nome_original     TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'indexando',
            usuario_id        BIGINT,
            sessao_anonima_id TEXT,
            criado_em         TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
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


def criar_documento(
    conexao: psycopg.Connection,
    nome_original: str,
    usuario_id: int | None = None,
    sessao_anonima_id: str | None = None,
) -> int:
    """
    Registra um novo documento com status "indexando" e devolve o id
    gerado — usado por POST /documentos antes de rodar a extração e o
    chunking, para já existir um id a que os chunks se associam.

    O documento nasce com o dono que a requisição trouxer: um usuário
    autenticado (`usuario_id`) ou uma sessão anônima
    (`sessao_anonima_id`) — nunca os dois, nunca nenhum (seção 1.5).
    """
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documentos (nome_original, usuario_id, sessao_anonima_id)
            VALUES (%s, %s, %s) RETURNING id
            """,
            (nome_original, usuario_id, sessao_anonima_id),
        )
        (documento_id,) = cursor.fetchone()
    conexao.commit()
    return documento_id


def atualizar_status_documento(
    conexao: psycopg.Connection, documento_id: int, status: str
) -> None:
    """status: "indexando" | "pronto" | "falhou" (seção 7.2)."""
    conexao.execute(
        "UPDATE documentos SET status = %s WHERE id = %s", (status, documento_id)
    )
    conexao.commit()


def buscar_documento(conexao: psycopg.Connection, documento_id: int) -> dict | None:
    """
    Usado por GET /documentos/{id}, POST /perguntas e DELETE
    /documentos/{id} — todos precisam do dono (`usuario_id` /
    `sessao_anonima_id`) para checar acesso antes de agir. None se o
    id não existir.
    """
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nome_original, status, usuario_id, sessao_anonima_id
            FROM documentos WHERE id = %s
            """,
            (documento_id,),
        )
        linha = cursor.fetchone()

    if linha is None:
        return None

    documento_id, nome_original, status, usuario_id, sessao_anonima_id = linha
    return {
        "id": documento_id,
        "nome_original": nome_original,
        "status": status,
        "usuario_id": usuario_id,
        "sessao_anonima_id": sessao_anonima_id,
    }


def listar_documentos(
    conexao: psycopg.Connection,
    usuario_id: int | None = None,
    sessao_anonima_id: str | None = None,
) -> list[dict]:
    """
    Usado por GET /documentos. Lista os documentos do usuário
    autenticado, ou os da sessão anônima quando não há usuário —
    nunca os dois conjuntos misturados.
    """
    with conexao.cursor() as cursor:
        if usuario_id is not None:
            cursor.execute(
                "SELECT id, nome_original, status FROM documentos WHERE usuario_id = %s ORDER BY criado_em DESC",
                (usuario_id,),
            )
        else:
            cursor.execute(
                "SELECT id, nome_original, status FROM documentos WHERE sessao_anonima_id = %s AND usuario_id IS NULL ORDER BY criado_em DESC",
                (sessao_anonima_id,),
            )
        linhas = cursor.fetchall()

    return [
        {"id": id_, "nome_original": nome_original, "status": status}
        for id_, nome_original, status in linhas
    ]


def remover_documento(conexao: psycopg.Connection, documento_id: int) -> None:
    """Usado por DELETE /documentos/{id} — remove o documento e os chunks dele."""
    conexao.execute("DELETE FROM chunks WHERE documento_id = %s", (documento_id,))
    conexao.execute("DELETE FROM documentos WHERE id = %s", (documento_id,))
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
                (
                    documento_id,
                    chunk["indice"],
                    chunk["pagina"],
                    chunk["texto"],
                    # Vector(...), não a list[float] crua: o adaptador do
                    # pgvector só reconhece Vector/ndarray como parâmetro
                    # (ver register_vector_info) — uma lista pura cai no
                    # dumper padrão do psycopg e vira array double
                    # precision, não vector. Buscador.py tem a mesma regra.
                    Vector(vetor),
                )
                for chunk, vetor in zip(chunks, vetores)
            ],
        )
    conexao.commit()
