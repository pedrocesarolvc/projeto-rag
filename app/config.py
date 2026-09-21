"""
Configuração da aplicação via variável de ambiente.

Centraliza tudo que muda entre ambientes (string de conexão do
Postgres, limites de upload etc.) para que nenhum outro módulo leia
variáveis de ambiente diretamente — config.py é o único ponto de
acesso.

As variáveis concretas nascem junto com a etapa que passa a
depender delas (ex.: DATABASE_URL só é necessária a partir da Etapa 4,
armazenamento com pgvector). Ver .env.example na raiz do projeto.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# String de conexão do PostgreSQL (Etapa 4). Ausente é uma condição
# válida até algum módulo realmente precisar conectar — só então o
# erro aparece, com uma mensagem clara em vez de um KeyError na
# importação de todo o projeto.
DATABASE_URL = os.environ.get("DATABASE_URL")

# A LLM que gera a resposta (Etapa 6) roda local via Ollama, assim
# como o modelo de embedding (Etapa 4) — nenhuma das duas precisa de
# chave de API (seção 6.7 da documentação, decisão revista).
#
# Exceção deliberada para a instância pública: um ambiente sem GPU
# nem CPU dedicada não roda um modelo local com latência aceitável ao
# vivo. LLM_PROVIDER=groq troca só a geração (o embedding continua
# local, ver app/indexacao/embedder.py) pela API gratuita da Groq —
# mais rápida que qualquer alternativa hospedada de graça, e sem
# exigir cartão de crédito. O padrão continua Ollama; isto não muda
# nada para quem roda localmente.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# Assina e verifica o token de autenticação (Etapa 7, app/auth/).
# Trocar essa chave invalida todos os tokens emitidos — usuários
# precisam logar de novo, mas nenhum dado é perdido.
SECRET_KEY = os.environ.get("SECRET_KEY")
