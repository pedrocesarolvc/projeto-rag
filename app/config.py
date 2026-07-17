"""
Configuração da aplicação via variável de ambiente.

Centraliza tudo que muda entre ambientes (string de conexão do
Postgres, chaves de API de embedding/LLM, limites de upload etc.)
para que nenhum outro módulo leia variáveis de ambiente diretamente —
config.py é o único ponto de acesso.

As variáveis concretas nascem junto com a etapa que passa a
depender delas (ex.: DATABASE_URL só é necessária a partir da Etapa 3,
armazenamento com pgvector). Ver .env.example na raiz do projeto.
"""
