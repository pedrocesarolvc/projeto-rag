"""
Etapa 6 — Geração: montagem do prompt.

O prompt é a lógica de negócio do projeto (seção 6.3): instrução,
contexto, pergunta — nessa ordem, sempre. É este bloco inteiro que
vai para a LLM, nunca a pergunta sozinha; "Augmented" no nome do RAG
é exatamente este momento, a pergunta aumentada com os trechos que a
Etapa 5 recuperou.

A instrução é grounding (seção 6.4): prende a resposta ao contexto
recebido, em vez de deixar a LLM completar com o que ela "acha que
sabe". Três exigências nela, todas regra de negócio escrita em
português, não em código: usar só o contexto, admitir quando a
resposta não está lá, e apontar a página de origem.
"""

INSTRUCAO = (
    "Responda usando somente o contexto abaixo. Se a resposta não "
    "estiver nele, diga que não encontrou. Indique a página de onde "
    "cada informação veio."
)

# Contexto vazio (nenhum chunk passou do limiar da Etapa 5) ainda
# produz um prompt válido — um que instrui a LLM a dizer que não
# encontrou (seção 6.5), em vez de simplesmente não ter nada para
# perguntar.
SEM_CONTEXTO = "(nenhum trecho relevante foi encontrado no documento)"


def montar_prompt(pergunta: str, chunks: list[dict]) -> str:
    """
    Monta o prompt com as três partes, na ordem instrução → contexto
    → pergunta. `chunks` é o contrato da Etapa 5:

        [{"pagina": 3, "texto": "...", "distancia": 0.18}, ...]

    Cada chunk entra no contexto rotulado com a própria página
    (`[pág. N]`), para que a citação da Etapa 6 (seção 6.6) e o
    pedido de referência na instrução tenham de onde vir.
    """
    if chunks:
        contexto = "\n\n".join(
            f"[pág. {chunk['pagina']}] {chunk['texto']}" for chunk in chunks
        )
    else:
        contexto = SEM_CONTEXTO

    return f"{INSTRUCAO}\n\nContexto:\n{contexto}\n\nPergunta: {pergunta}"
