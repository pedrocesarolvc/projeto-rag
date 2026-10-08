"""
Etapa 5 — Recuperação: pergunta → chunks mais relevantes.

Primeira metade da fase de consulta (seção 5.1): roda a cada
pergunta, não uma vez por documento como a indexação (Etapas 2–4).
Entra a pergunta em texto; sai o punhado de chunks mais próximos
dela, cada um com sua distância. Ainda sem LLM — recuperação escolhe,
não gera (seção 5.2). Gerar é a Etapa 6.

Os três passos (seção 5.3): a pergunta vira vetor pelo mesmo modelo
que vetorizou os chunks (embedder.py, Etapa 4 — modelo diferente
aqui seria comparar mapas diferentes, seção 5.3); mede-se a distância
de cosseno no Postgres; pega-se o top-k.
"""

from pgvector import Vector

from app.indexacao.embedder import gerar_embeddings

# Chutes educados (seções 5.4 e 5.5), sem evals para medir o ideal —
# mas calibrados, não às cegas: medi a distância de cosseno real deste
# modelo em pares de exemplo. Pergunta↔chunk diretamente relacionados
# ficaram em ~0.27–0.36; o caso de sinônimo da seção 5.6 ("rescisão"
# pergunta / "distrato" no texto) em ~0.52; mesmo documento mas assunto
# diferente em ~0.75; totalmente não relacionado em ~0.96. LIMIAR_PADRAO
# fica entre o sinônimo (tem que passar) e o assunto ausente (tem que
# ser rejeitado), com folga dos dois lados.
K_PADRAO = 5
LIMIAR_PADRAO = 0.65


def buscar(
    conexao,
    documento_ids: list[int],
    pergunta: str,
    k: int = K_PADRAO,
    limiar: float = LIMIAR_PADRAO,
) -> list[dict]:
    """
    Vetoriza `pergunta` uma única vez, pega os `k` chunks mais
    próximos dela dentro de CADA documento de `documento_ids`, junta
    tudo e descarta os que passarem do `limiar` de distância (seção
    5.5) — o corte acontece depois do top-k, não no lugar dele: um
    `LIMIT k` sozinho sempre devolve k chunks, mesmo quando nenhum é
    relevante.

    O top-k é POR documento, não global, de propósito: num top-k único
    sobre dois PDFs, o mais "falante" para aquela pergunta poderia
    ocupar todas as vagas e esconder o outro — justamente o que
    impediria juntar as informações dos dois. Com um documento só, o
    comportamento é idêntico ao de antes. O limiar continua barrando
    o que não tem a ver: se o assunto só existe num dos PDFs, só ele
    contribui com chunks.

    Retorna o contrato da seção 5.9 (agora com o documento de origem),
    ordenado por distância crescente entre todos os documentos:

        [{"documento_id": 7, "pagina": 3, "texto": "...", "distancia": 0.18}, ...]

    O NOME do documento não vem daqui: esta etapa só conhece a tabela
    `chunks`, não `documentos`. Quem chama (pipeline.py) já tem os
    documentos em mãos e acrescenta o nome.

    Lista vazia é uma resposta válida — é o que permite à Etapa 6
    responder "não encontrei isso no documento" em vez de inventar.
    """
    # embedder.py devolve list[float] puro — de propósito, não conhece
    # Postgres nem pgvector (Etapa 4 não depende da Etapa 5 para trás).
    # O wrap em Vector() é local, só onde o driver precisa saber que
    # isto é um vetor: sem ele, o adaptador do pgvector cai no dumper
    # padrão de lista e manda um array double precision — o operador
    # <=> não casa com isso (UndefinedFunction), achado só ao testar
    # contra um Postgres real.
    vetor_pergunta = Vector(gerar_embeddings([pergunta])[0])

    chunks = []
    with conexao.cursor() as cursor:
        for documento_id in documento_ids:
            cursor.execute(
                """
                SELECT pagina, texto, vetor <=> %s AS distancia
                FROM chunks
                WHERE documento_id = %s
                ORDER BY vetor <=> %s
                LIMIT %s
                """,
                (vetor_pergunta, documento_id, vetor_pergunta, k),
            )
            chunks.extend(
                {
                    "documento_id": documento_id,
                    "pagina": pagina,
                    "texto": texto,
                    "distancia": distancia,
                }
                for pagina, texto, distancia in cursor.fetchall()
                if distancia <= limiar
            )

    # Cada consulta já vem ordenada, mas a junção de dois documentos
    # não: reordena para que o mais próximo da pergunta venha primeiro,
    # venha ele de onde vier.
    return sorted(chunks, key=lambda chunk: chunk["distancia"])
