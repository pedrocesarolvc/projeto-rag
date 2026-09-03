"""
Lastro — Etapa 7: autenticação, armazenamento no PostgreSQL.

A tabela `usuarios` e a adoção de documentos da sessão anônima
(seção 7.3): transferir os documentos de um token de sessão para o
usuário recém-autenticado, no cadastro ou no login.

Sem FK entre `documentos.usuario_id` e `usuarios.id`, de propósito —
o mesmo estilo do resto do schema (`chunks.documento_id` também não
tem). Simples, e evita amarrar a ordem em que as tabelas nascem.

As funções de escrita aqui **não commitam** — quem chama decide a
transação. É a regra da seção 7.3: "a transferência e a criação da
conta são uma coisa só". main.py compõe criar_usuario() e
adotar_documentos_da_sessao() numa única transação, com rollback se
qualquer uma falhar.
"""

import psycopg


def criar_tabela_usuarios(conexao: psycopg.Connection) -> None:
    """Cria a tabela `usuarios` se ainda não existir."""
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id         BIGSERIAL PRIMARY KEY,
            email      TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conexao.commit()


def criar_usuario(conexao: psycopg.Connection, email: str, senha_hash: str) -> int:
    """Não commita — ver o porquê no docstring do módulo."""
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO usuarios (email, senha_hash) VALUES (%s, %s) RETURNING id",
            (email, senha_hash),
        )
        (usuario_id,) = cursor.fetchone()
    return usuario_id


def buscar_usuario_por_email(conexao: psycopg.Connection, email: str) -> dict | None:
    """Usado no login (verificar senha) e no cadastro (recusar e-mail duplicado)."""
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT id, email, senha_hash FROM usuarios WHERE email = %s", (email,)
        )
        linha = cursor.fetchone()

    if linha is None:
        return None

    usuario_id, email, senha_hash = linha
    return {"id": usuario_id, "email": email, "senha_hash": senha_hash}


def adotar_documentos_da_sessao(
    conexao: psycopg.Connection, sessao_anonima_id: str, usuario_id: int
) -> None:
    """
    Move para `usuario_id` os documentos daquela sessão anônima que
    ainda não têm dono — e só os daquela sessão (seção 7.3: "a sessão
    anônima só entrega o que é dela"). Não commita.
    """
    conexao.execute(
        """
        UPDATE documentos
        SET usuario_id = %s
        WHERE sessao_anonima_id = %s AND usuario_id IS NULL
        """,
        (usuario_id, sessao_anonima_id),
    )
