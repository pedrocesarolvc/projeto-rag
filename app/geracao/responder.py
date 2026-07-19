"""
Etapa 6 — Geração: monta o prompt e chama a LLM.

Entra a pergunta e os chunks que a Etapa 5 já recuperou; sai a
resposta, ancorada neles (seção 6.2). Este módulo não busca nada por
conta própria — a fronteira da seção 6.1 é estrita: "Recuperação
(Etapa 5): acha os trechos. Não escreve. Geração (Etapa 6): escreve
a resposta. Não busca." Se o chunk certo não veio da Etapa 5, nenhum
prompt conserta isso (seções 5.8 e 6.9) — o problema está lá, não
aqui.
"""

from app.geracao.llm import gerar
from app.geracao.prompt import montar_prompt


def responder(pergunta: str, chunks: list[dict]) -> dict:
    """
    `chunks` é o contrato da Etapa 5. Retorna:

        {"resposta": "...", "chunks": chunks}

    Os chunks voltam junto no retorno — não para reprocessamento, mas
    para a interface exibir a citação (trecho + página) ao lado da
    resposta, sem precisar buscar de novo (seção 6.6).
    """
    prompt = montar_prompt(pergunta, chunks)
    resposta = gerar(prompt)
    return {"resposta": resposta, "chunks": chunks}
