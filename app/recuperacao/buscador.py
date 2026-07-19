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
    documento_id: int,
    pergunta: str,
    k: int = K_PADRAO,
    limiar: float = LIMIAR_PADRAO,
) -> list[dict]:
    """
    Vetoriza `pergunta`, pega os `k` chunks mais próximos dela dentro
    de `documento_id`, e descarta os que passarem do `limiar` de
    distância (seção 5.5) — o corte acontece depois do top-k, não no
    lugar dele: um `LIMIT k` sozinho sempre devolve k chunks, mesmo
    quando nenhum é relevante.

    Retorna o contrato da seção 5.9, ordenado por distância crescente:

        [{"pagina": 3, "texto": "...", "distancia": 0.18}, ...]

    Lista vazia é uma resposta válida — é o que permite à Etapa 6
    responder "não encontrei isso no documento" em vez de inventar.
    """
    vetor_pergunta = gerar_embeddings([pergunta])[0]

    with conexao.cursor() as cursor:
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
        resultados = cursor.fetchall()

    return [
        {"pagina": pagina, "texto": texto, "distancia": distancia}
        for pagina, texto, distancia in resultados
        if distancia <= limiar
    ]
