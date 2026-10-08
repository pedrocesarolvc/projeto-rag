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
resposta não está lá, e apontar o documento e a página de origem.
Com mais de um PDF na mesma pergunta, uma quarta: apontar quando eles
divergirem, em vez de a LLM escolher um lado em silêncio.
"""

INSTRUCAO = (
    "Responda usando somente o contexto abaixo. Se a resposta não "
    "estiver nele, diga que não encontrou. Indique o documento e a "
    "página de onde cada informação veio. Se documentos diferentes "
    "disserem coisas diferentes sobre o mesmo ponto, aponte a "
    "divergência em vez de escolher um lado."
)

# Contexto vazio (nenhum chunk passou do limiar da Etapa 5) ainda
# produz um prompt válido — um que instrui a LLM a dizer que não
# encontrou (seção 6.5), em vez de simplesmente não ter nada para
# perguntar.
SEM_CONTEXTO = "(nenhum trecho relevante foi encontrado no documento)"


def montar_prompt(pergunta: str, chunks: list[dict]) -> str:
    """
    Monta o prompt com as três partes, na ordem instrução → contexto
    → pergunta. `chunks` é o contrato da Etapa 5, já com o nome do
    documento acrescentado por pipeline.py:

        [{"documento": "contrato.pdf", "pagina": 3, "texto": "...", "distancia": 0.18}, ...]

    Cada chunk entra no contexto rotulado com o documento e a página
    (`[contrato.pdf, pág. N]`), para que a citação da Etapa 6 (seção
    6.6) e o pedido de referência na instrução tenham de onde vir — e
    para que, com mais de um PDF na pergunta, a LLM consiga atribuir
    cada fato ao arquivo certo em vez de misturá-los sem rastro.
    """
    if chunks:
        contexto = "\n\n".join(
            f"[{chunk['documento']}, pág. {chunk['pagina']}] {chunk['texto']}"
            for chunk in chunks
        )
    else:
        contexto = SEM_CONTEXTO

    return f"{INSTRUCAO}\n\nContexto:\n{contexto}\n\nPergunta: {pergunta}"
