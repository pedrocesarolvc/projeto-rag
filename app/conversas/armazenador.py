"""
Lastro — conversas: armazenamento no PostgreSQL.

Cada assunto vive numa conversa (a "lombada" da estante). Três tabelas:

    conversas            — de quem é, e quando nasceu / foi usada pela última vez
    conversa_documentos  — quais documentos (1 ou 2) a conversa consulta, em ordem
    mensagens            — cada pergunta, a resposta e as citações que a sustentaram

Uma conversa só existe para quem tem conta: ela nasce na primeira
pergunta, e a pergunta exige login (cadastro adiado, seção 1.5). Antes
disso, os documentos enviados vivem só na sessão anônima, como sempre.

Cada pergunta continua independente das anteriores — a conversa guarda o
histórico para o usuário reler, mas nada daqui entra no prompt. É de
propósito: o prompt é onde mora o grounding, e fazer o modelo "lembrar"
da conversa mudaria justamente isso.

As citações são guardadas como JSON dentro da própria mensagem, e não
como referência aos chunks: o histórico precisa continuar legível mesmo
depois que um documento for removido e os chunks dele sumirem.

Sem FKs, no mesmo estilo do resto do schema (ver app/auth/armazenador.py).
As funções de escrita **não commitam**, exceto criar_tabelas — quem
chama decide a transação, para que, por exemplo, criar a conversa e
gravar a primeira mensagem sejam uma coisa só.
"""

import psycopg
from psycopg.types.json import Jsonb


def criar_tabelas(conexao: psycopg.Connection) -> None:
    """Cria as tabelas das conversas se ainda não existirem."""
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS conversas (
            id            BIGSERIAL PRIMARY KEY,
            usuario_id    BIGINT NOT NULL,
            criado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS conversa_documentos (
            conversa_id  BIGINT NOT NULL,
            documento_id BIGINT NOT NULL,
            ordem        INT NOT NULL,
            PRIMARY KEY (conversa_id, documento_id)
        )
        """
    )
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS mensagens (
            id          BIGSERIAL PRIMARY KEY,
            conversa_id BIGINT NOT NULL,
            pergunta    TEXT NOT NULL,
            resposta    TEXT NOT NULL,
            citacoes    JSONB NOT NULL DEFAULT '[]',
            criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    # as três consultas que o dia a dia faz: as conversas de um usuário,
    # as mensagens de uma conversa, e as conversas de um documento
    conexao.execute("CREATE INDEX IF NOT EXISTS conversas_usuario_idx ON conversas (usuario_id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS mensagens_conversa_idx ON mensagens (conversa_id)")
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS conversa_documentos_documento_idx "
        "ON conversa_documentos (documento_id)"
    )
    conexao.commit()


def criar_conversa(
    conexao: psycopg.Connection, usuario_id: int, documento_ids: list[int]
) -> int:
    """Cria a conversa ligada aos `documento_ids`, na ordem dada. Não commita."""
    with conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO conversas (usuario_id) VALUES (%s) RETURNING id", (usuario_id,)
        )
        (conversa_id,) = cursor.fetchone()
        cursor.executemany(
            "INSERT INTO conversa_documentos (conversa_id, documento_id, ordem) VALUES (%s, %s, %s)",
            [(conversa_id, documento_id, ordem) for ordem, documento_id in enumerate(documento_ids)],
        )
    return conversa_id


def vincular_documento(
    conexao: psycopg.Connection, conversa_id: int, documento_id: int, ordem: int
) -> None:
    """Põe um documento numa conversa que já existe, depois dos que ela tem. Não commita."""
    conexao.execute(
        """
        INSERT INTO conversa_documentos (conversa_id, documento_id, ordem)
        VALUES (%s, %s, %s)
        ON CONFLICT (conversa_id, documento_id) DO NOTHING
        """,
        (conversa_id, documento_id, ordem),
    )


def _com_documentos(conexao: psycopg.Connection, filtro: str, parametros: tuple) -> list[dict]:
    """
    Junta as conversas selecionadas por `filtro` com os documentos de
    cada uma, em ordem. `filtro` é um trecho de SQL fixo, escrito aqui
    dentro — nunca montado a partir de entrada do usuário.
    """
    with conexao.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT c.id, c.usuario_id, d.id, d.nome_original, d.status
            FROM conversas c
            LEFT JOIN conversa_documentos cd ON cd.conversa_id = c.id
            LEFT JOIN documentos d ON d.id = cd.documento_id
            WHERE {filtro}
            ORDER BY c.criado_em, c.id, cd.ordem
            """,
            parametros,
        )
        linhas = cursor.fetchall()

    conversas: dict[int, dict] = {}
    for conversa_id, usuario_id, doc_id, nome_original, status in linhas:
        conversa = conversas.setdefault(
            conversa_id, {"id": conversa_id, "usuario_id": usuario_id, "documentos": []}
        )
        if doc_id is not None:
            conversa["documentos"].append(
                {"id": doc_id, "nome_original": nome_original, "status": status}
            )
    return list(conversas.values())


def buscar_conversa(conexao: psycopg.Connection, conversa_id: int) -> dict | None:
    """
    `{"id", "usuario_id", "documentos": [{"id", "nome_original", "status"}]}`,
    ou None. O `usuario_id` vem junto para a rota checar o dono, como
    buscar_documento() faz com os documentos.
    """
    encontradas = _com_documentos(conexao, "c.id = %s", (conversa_id,))
    return encontradas[0] if encontradas else None


def listar_conversas(conexao: psycopg.Connection, usuario_id: int) -> list[dict]:
    """As conversas do usuário, da mais antiga para a mais nova — a ordem da estante."""
    return _com_documentos(conexao, "c.usuario_id = %s", (usuario_id,))


def registrar_mensagem(
    conexao: psycopg.Connection,
    conversa_id: int,
    pergunta: str,
    resposta: str,
    citacoes: list[dict],
) -> int:
    """Grava a pergunta, a resposta e as citações, e marca a conversa como usada. Não commita."""
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO mensagens (conversa_id, pergunta, resposta, citacoes)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (conversa_id, pergunta, resposta, Jsonb(citacoes)),
        )
        (mensagem_id,) = cursor.fetchone()
        cursor.execute(
            "UPDATE conversas SET atualizado_em = now() WHERE id = %s", (conversa_id,)
        )
    return mensagem_id


def listar_mensagens(conexao: psycopg.Connection, conversa_id: int) -> list[dict]:
    """As mensagens da conversa, da mais antiga para a mais nova."""
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, pergunta, resposta, citacoes
            FROM mensagens WHERE conversa_id = %s
            ORDER BY criado_em, id
            """,
            (conversa_id,),
        )
        linhas = cursor.fetchall()
    return [
        {"id": id_, "pergunta": pergunta, "resposta": resposta, "citacoes": citacoes}
        for id_, pergunta, resposta, citacoes in linhas
    ]


def remover_conversa(conexao: psycopg.Connection, conversa_id: int) -> list[int]:
    """
    Apaga a conversa e as mensagens dela, e devolve os ids dos documentos
    que ficaram sem nenhuma conversa — esses a rota apaga em seguida,
    porque sem conversa o usuário não tem mais como vê-los. Documento
    que ainda pertence a outra conversa fica. Não commita.
    """
    with conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT cd.documento_id
            FROM conversa_documentos cd
            WHERE cd.conversa_id = %s
              AND NOT EXISTS (
                  SELECT 1 FROM conversa_documentos outro
                  WHERE outro.documento_id = cd.documento_id AND outro.conversa_id <> %s
              )
            """,
            (conversa_id, conversa_id),
        )
        exclusivos = [documento_id for (documento_id,) in cursor.fetchall()]
        cursor.execute("DELETE FROM mensagens WHERE conversa_id = %s", (conversa_id,))
        cursor.execute("DELETE FROM conversa_documentos WHERE conversa_id = %s", (conversa_id,))
        cursor.execute("DELETE FROM conversas WHERE id = %s", (conversa_id,))
    return exclusivos


def desvincular_documento(conexao: psycopg.Connection, documento_id: int) -> None:
    """
    Tira o documento de todas as conversas dele, antes de ele ser
    removido. Uma conversa que fica sem documento nenhum não tem mais o
    que consultar nem título para a lombada: some junto, com as
    mensagens. As mensagens de uma conversa que continua existindo
    ficam como estão — as citações já estão gravadas nelas. Não commita.
    """
    with conexao.cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT conversa_id FROM conversa_documentos WHERE documento_id = %s",
            (documento_id,),
        )
        afetadas = [conversa_id for (conversa_id,) in cursor.fetchall()]
        cursor.execute("DELETE FROM conversa_documentos WHERE documento_id = %s", (documento_id,))
        for conversa_id in afetadas:
            cursor.execute(
                "SELECT 1 FROM conversa_documentos WHERE conversa_id = %s LIMIT 1",
                (conversa_id,),
            )
            if cursor.fetchone() is None:
                cursor.execute("DELETE FROM mensagens WHERE conversa_id = %s", (conversa_id,))
                cursor.execute("DELETE FROM conversas WHERE id = %s", (conversa_id,))
