"""
Etapa 6 — Geração: chamada à LLM.

Isola a chamada por trás de uma função só, gerar(prompt) -> texto,
sem espalhar o cliente pelo resto do código (seção 6.7). Trocar de
provedor — ou, como aqui, para um modelo local — mexe neste arquivo,
não em dez. O provedor de LLM é borda, substituível; o pipeline de
RAG é núcleo, e não deveria nem saber qual modelo respondeu.

Decisão revista: modelo local via Ollama, não API paga. A seção 6.7
lista as duas rotas e já nomeia esta como legítima — "Local: grátis
após baixar, nada sai da máquina, setup pesado". Trocamos o ponto de
partida do v1 (API) pela rota local para não depender de chave nem de
cartão de crédito para rodar o projeto: mesmo princípio de
privacidade que já vale para o embedding (Etapa 4), agora também na
geração.

Segunda decisão, só para a instância pública: sem GPU nem CPU
dedicada, um modelo local não responde com latência aceitável numa
demonstração ao vivo. `LLM_PROVIDER=groq` (app/config.py) troca a
chamada para a API gratuita da Groq nessa instância específica — o
resto do pipeline (retrieval, prompt, grounding) não muda uma linha,
porque a fronteira já era esta função.
"""

import ollama
from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL, LLM_PROVIDER

# Testado contra o 3B (llama3.2:3b): o 8B extrai e cita página
# corretamente em perguntas diretas; o 3B era mais impreciso no
# básico. Nenhum dos dois faz a ponte "distrato" -> "rescisão" sem
# ajuda — ambos preferem dizer "não encontrou" a inferir uma
# equivalência que o contexto não afirma literalmente. Isso não é bug
# de tamanho de modelo; é o grounding (seção 6.4) funcionando de
# forma conservadora, mesmo em modelos pequenos.
NOME_MODELO_OLLAMA = "llama3.1:8b"


def gerar(prompt: str) -> str:
    """
    Envia `prompt` (instrução + contexto + pergunta, já montado por
    prompt.montar_prompt) à LLM e devolve o texto da resposta.
    `LLM_PROVIDER` decide o provedor — ollama (padrão, local) ou groq
    (usado só na instância pública).
    """
    if LLM_PROVIDER == "groq":
        return _gerar_groq(prompt)
    return _gerar_ollama(prompt)


def _gerar_ollama(prompt: str) -> str:
    try:
        resposta = ollama.chat(
            model=NOME_MODELO_OLLAMA,
            messages=[{"role": "user", "content": prompt}],
        )
    except ConnectionError:
        raise RuntimeError(
            "Ollama não está rodando. Inicie o Ollama e confirme que o "
            f"modelo foi baixado (ollama pull {NOME_MODELO_OLLAMA})."
        )
    except ollama.ResponseError as erro:
        raise RuntimeError(f"Erro do Ollama: {erro}")

    return resposta["message"]["content"]


def _gerar_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY não configurada — defina no .env (local) ou nas "
            "secrets do Space (deploy)."
        )

    cliente = Groq(api_key=GROQ_API_KEY)
    try:
        resposta = cliente.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as erro:
        raise RuntimeError(f"Erro do Groq: {erro}")

    return resposta.choices[0].message.content
