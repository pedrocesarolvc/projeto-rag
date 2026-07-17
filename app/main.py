"""
Ponto de entrada da API.

Aqui vive a instância do FastAPI e as rotas expostas ao frontend:
upload do documento (Etapa 2), pergunta ao documento e resposta com
citação (etapas seguintes: busca e geração).

Este arquivo nasce quase vazio de propósito. As rotas de ingestão só
entram aqui quando a Etapa 2 (app/ingestao/) estiver implementada; as
rotas de pergunta/resposta, quando a busca e a geração existirem.
Pasta e rota nascem junto com o código que as justifica — não antes.
"""

from fastapi import FastAPI

app = FastAPI(title="Projeto RAG")

# Rotas de upload (Etapa 2), pergunta e resposta (etapas seguintes)
# entram aqui conforme cada etapa é implementada.
