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
| Embeddings | sentence-transformers (local, multilíngue) |
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
├── ingestao/               # Etapa 2
│   ├── upload.py           # validação e guarda do arquivo
│   └── extrator.py         # PDF → texto, página por página
├── chunking/                # Etapa 3
│   └── divisor.py            # texto → chunks, por corte recursivo
└── indexacao/                # Etapa 4
    ├── embedder.py            # texto → vetor (modelo local)
    └── armazenador.py         # grava chunks + vetores no PostgreSQL
tests/
├── fixtures/                # PDFs de teste
├── test_ingestao.py
├── test_chunking.py
├── test_embedder.py
└── test_armazenador.py
```

## Limitações conhecidas

| Limitação | Motivo |
|---|---|
| Chunk nunca atravessa página | Um parágrafo que atravessa a virada de página vira dois chunks. Trocado por citação sem ambiguidade — a página de um chunk nunca é um intervalo (ver `docs/documentacao.md`, Etapa 3, seção 3.7) |
| Tamanho do chunk (~450 caracteres) e sobreposição (~15%) são um chute educado | Ajustado para caber no teto de 128 tokens do modelo de embedding local (acima disso, o modelo trunca em silêncio — ver `docs/documentacao.md`, Etapa 4). Ainda sem evals para validar se é o tamanho ideal para este tipo de documento |
| `tests/test_armazenador.py` pula sem Docker num Windows local | pgvector não tem binário para Windows — exigiria compilar com Visual Studio Build Tools. A imagem `pgvector/pgvector` do Docker (Etapa 7) resolve isso sem build manual |

## Rodando localmente

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # e ajuste DATABASE_URL
pytest tests/
```

O primeiro `pytest` baixa o modelo de embedding (~1 GB, uma vez só — fica em cache local). Os testes de `test_armazenador.py` só rodam se `DATABASE_URL` apontar para um Postgres com a extensão `vector` já instalada; caso contrário, pulam automaticamente.
