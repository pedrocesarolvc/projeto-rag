"""
Etapa 7 — Entrega: orquestração entre as etapas, chamada pelas rotas.

main.py fica fino (seção 7.2): recebe HTTP, valida com Pydantic,
delega para cá, devolve. Nenhuma lógica de RAG mora na camada de
rota — ela só traduz HTTP em chamada de função e volta.

As duas rotas da API (POST /documentos, POST /perguntas) são a
fronteira indexação/consulta, agora visível de fora: indexar_documento
roda as Etapas 2, 3 e 4; responder_pergunta roda as Etapas 5 e 6.
"""

from fastapi import UploadFile

from app.chunking.divisor import dividir
from app.geracao.responder import responder as gerar_resposta
from app.indexacao import armazenador
from app.ingestao.extrator import extrair
from app.ingestao.upload import receber_upload
from app.recuperacao.buscador import buscar


async def indexar_documento(conexao, arquivo: UploadFile) -> dict:
    """
    Roda a fase de indexação inteira para um upload: extrai (Etapa 2),
    divide em chunks (Etapa 3), gera embeddings e grava no banco
    (Etapa 4).

    Síncrono, por decisão do v1 (seção 7.3): a rota só responde depois
    que tudo terminou — o teto de 20 MB da Etapa 2 mantém isso dentro
    do aceitável. Fila assíncrona fica no roadmap.
    """
    meta = await receber_upload(arquivo)
    documento_id = armazenador.criar_documento(conexao, meta["nome_original"])

    try:
        paginas = extrair(meta["caminho"])
        chunks = dividir(paginas)
        armazenador.indexar(conexao, documento_id, chunks)
    except Exception:
        armazenador.atualizar_status_documento(conexao, documento_id, "falhou")
        raise

    armazenador.atualizar_status_documento(conexao, documento_id, "pronto")
    return {
        "id": documento_id,
        "nome_original": meta["nome_original"],
        "status": "pronto",
    }


def responder_pergunta(conexao, documento_id: int, pergunta: str) -> dict:
    """
    Roda a fase de consulta inteira: busca os chunks mais relevantes
    (Etapa 5) e gera a resposta ancorada neles (Etapa 6).
    """
    chunks = buscar(conexao, documento_id, pergunta)
    return gerar_resposta(pergunta, chunks)
