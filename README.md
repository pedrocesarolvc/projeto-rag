# Projeto RAG

Converse com um documento PDF. Respostas fundamentadas, mostrando o trecho e a página de origem.

O usuário sobe um PDF e pergunta sobre o conteúdo dele em linguagem natural. O sistema busca por
significado (não por palavra igual), monta um prompt com os trechos relevantes, e a LLM responde
citando o trecho e a página que fundamentaram a resposta. Nada é treinado: o conhecimento vive no
banco de dados, não no modelo.

Documentação completa, por etapas: `docs/documentacao.md`.

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| API | FastAPI + Uvicorn |
| Validação | Pydantic |
| Extração de PDF | PyMuPDF |
| Banco | PostgreSQL + pgvector |
| Frontend | TypeScript + React |
| Testes | pytest |
| Empacotamento | Docker Compose |

## Estrutura

```
app/
├── main.py               # FastAPI: app e rotas
├── config.py              # configuração via variável de ambiente
├── modelos.py              # schemas Pydantic (contratos entre etapas)
└── ingestao/               # Etapa 2
    ├── upload.py           # validação e guarda do arquivo
    └── extrator.py         # PDF → texto, página por página
tests/
├── fixtures/                # PDFs de teste
└── test_ingestao.py
```
