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
├── ingestao/               # Etapa 2
│   ├── upload.py           # validação e guarda do arquivo
│   └── extrator.py         # PDF → texto, página por página
└── chunking/                # Etapa 3
    └── divisor.py            # texto → chunks, por corte recursivo
tests/
├── fixtures/                # PDFs de teste
├── test_ingestao.py
└── test_chunking.py
```

## Limitações conhecidas

| Limitação | Motivo |
|---|---|
| Chunk nunca atravessa página | Um parágrafo que atravessa a virada de página vira dois chunks. Trocado por citação sem ambiguidade — a página de um chunk nunca é um intervalo (ver `docs/documentacao.md`, Etapa 3, seção 3.7) |
| Tamanho do chunk (~1600 caracteres) e sobreposição (~15%) são um chute educado | Sem evals ainda, não há como medir se esses números são os certos para este tipo de documento — só que são razoáveis. Evals estão no roadmap |
