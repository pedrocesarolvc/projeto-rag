# Projeto RAG — Documentação

> **Documento em construção, escrito por etapas.**
> Cada etapa corresponde a um pedaço construível do projeto.

| Etapa | Conteúdo | Status |
|---|---|---|
| **1** | Visão, problema e escopo | ✅ escrita |
| **2** | Ingestão — upload e extração de texto | ✅ escrita |
| 3 | Chunking — divisão do texto | ⬜ pendente |
| 4 | Indexação — embeddings e pgvector | ⬜ pendente |
| 5 | Recuperação — a busca | ⬜ pendente |
| 6 | Geração — prompt, resposta e citação | ⬜ pendente |
| 7 | Entrega — API, interface, testes e Docker | ⬜ pendente |

---

# Etapa 1 — Visão, problema e escopo

## 1.1 O problema

Uma LLM sabe o que estava nos dados de treinamento dela. Ela não sabe o seu contrato, o seu manual técnico, o seu relatório financeiro. Se você perguntar, ela responde mesmo assim — inventando com confiança, porque gerar texto plausível é o que ela faz.

Ao mesmo tempo, quase toda empresa tem um acervo de documentos que ninguém lê inteiro: manuais de centenas de páginas, contratos, normas internas, relatórios. A informação existe, mas encontrar a resposta exige saber onde procurar.

**O projeto resolve os dois problemas ao mesmo tempo:** permite perguntar em linguagem natural a um acervo de documentos privados e receber uma resposta fundamentada, com o trecho exato que a originou.

## 1.2 O que é o projeto

Uma aplicação web onde o usuário sobe um documento e conversa com ele.

O usuário faz upload de um PDF. Depois pergunta: *"qual é o prazo de rescisão?"*. O sistema encontra os trechos do documento que tratam disso, entrega esses trechos para uma LLM junto com a pergunta, e devolve a resposta — mostrando de qual parte do documento ela saiu.

O ponto central, e a inversão mais comum de quem chega ao RAG: **nada é treinado. Nunca.** A LLM não aprende o documento — nem no upload, nem depois de mil perguntas. Ela recebe os trechos certos no momento da pergunta, responde, e volta a ser exatamente o que era.

O teste que fixa a ideia: se você apagar todos os documentos hoje, o modelo fica idêntico ao que era antes deste projeto existir. O conhecimento nunca esteve dentro dele — esteve no banco de dados, e foi emprestado por alguns segundos, dentro do prompt.

É por isso que o RAG existe: treinar é caro, lento e ensina fatos mal. RAG é a alternativa a treinar.

A analogia que resume tudo: é uma **prova com consulta**. O modelo não decora o livro. Ele recebe as páginas certas, já abertas, na hora em que a pergunta é feita.

## 1.3 Como funciona, em duas fases

O sistema tem dois fluxos que rodam em momentos diferentes.

**Fase de indexação** — acontece uma vez, quando o documento é enviado:

```
Documento  →  extrai texto  →  divide em pedaços  →  converte
              (parsing)         (chunking)            em vetores
                                                     (embeddings)
                                                          ↓
                                                    guarda no banco
```

**Fase de consulta** — acontece a cada pergunta:

```
Pergunta  →  vira vetor  →  busca os pedaços  →  monta o prompt  →  LLM responde
                             mais parecidos      (trechos +          citando os
                                                  pergunta)          trechos
```

A ideia que faz tudo funcionar: **texto vira número, e números parecidos significam textos com sentido parecido.** A busca é por **significado**, não por palavra igual.

A diferença é concreta. Suponha que o contrato diga:

> "O distrato deverá ser comunicado com 90 dias de antecedência."

E o usuário pergunte: *"qual o prazo de rescisão?"*

Nenhuma palavra da pergunta aparece no trecho. Não há "prazo", não há "rescisão". Uma busca por palavra igual retorna zero resultados. A busca por significado encontra, porque "distrato" e "rescisão" ficam próximos no espaço vetorial, e "90 dias de antecedência" carrega a ideia de prazo sem usar a palavra.

É esse o caso normal: ninguém pergunta usando o vocabulário exato do documento. A Etapa 4 explica o mecanismo — por ora, basta a intuição.

## 1.4 Escopo do v1

Esta é a seção mais importante do documento.

Um projeto de portfólio terminado vale mais do que um projeto ambicioso abandonado. O v1 abaixo é pequeno de propósito: ele é **completo e honesto**, e demonstra a arquitetura inteira ponta a ponta. Tudo que fica de fora vira roadmap declarado — o que, por si só, comunica visão de produto.

### Entra no v1

| Item | Detalhe |
|---|---|
| Upload | Um PDF por vez |
| Extração de texto | Apenas PDF |
| Divisão do texto | Tamanho fixo com sobreposição |
| Vetorização | Um modelo de embedding, sem comparações |
| Armazenamento | PostgreSQL com a extensão pgvector |
| Busca | Apenas semântica (por similaridade) |
| Resposta | Uma LLM, respondendo com base nos trechos |
| Citação | Exibe os trechos que fundamentaram a resposta |
| Interface | Upload + chat, sem enfeite |
| Testes | Pytest nas partes determinísticas |
| Empacotamento | Docker Compose subindo app + banco |

### Fica no roadmap

| Item | Por que fica de fora agora |
|---|---|
| Suporte a DOCX | O PDF já cobre a demonstração; DOCX é mais do mesmo |
| Múltiplos documentos | Exige gestão de coleções — complexidade sem novo aprendizado |
| Chunking estruturado | Melhoria de qualidade, não de arquitetura |
| Busca híbrida | O upgrade mais valioso do v2, mas depende da busca simples existir antes |
| Reranking | Otimização fina; só faz sentido com busca já funcionando |
| Evals | Só medem o que já existe |
| Streaming da resposta | Melhoria de experiência, não de arquitetura |
| Autenticação e multiusuário | Não demonstra nada sobre RAG |

**Regra para não crescer o escopo:** um item só sai do roadmap e entra no v1 quando **todo** o v1 estiver funcionando. Não antes.

## 1.5 Decisões de arquitetura

Cada decisão abaixo tem um porquê que vale ser dito em uma entrevista.

**PostgreSQL com pgvector, não Pinecone nem ChromaDB.**
Um banco de vetores dedicado é mais uma peça de infraestrutura para manter, e Pinecone é um serviço pago. O pgvector transforma o Postgres — que o projeto já usa para o resto — em banco vetorial. Uma peça a menos, e demonstra que o projeto monta infraestrutura de IA sem depender de SaaS.

*Bônus:* o Postgres também faz busca por palavra-chave nativamente, o que deixa a busca híbrida do v2 acessível sem adicionar nada novo.

**Sem LangChain e sem LlamaIndex.**
Esses frameworks entregam um RAG funcionando em uma tarde — escondendo exatamente as partes que este projeto existe para demonstrar: divisão do texto, busca e montagem do prompt. Construir manual dá mais trabalho e ensina o que o framework abstrai. Num portfólio, o que se quer provar é entendimento, não velocidade de montagem.

**Busca simples no v1, híbrida no v2.**
A busca por similaridade é boa com significado e ruim com literalidade — ela erra códigos, nomes próprios e números de cláusula. A busca híbrida corrige isso. Mas ela é uma *melhoria* da busca simples: não dá para melhorar o que ainda não existe.

**A citação não é enfeite de interface.**
Mostrar o trecho que originou a resposta é o mecanismo de confiança do produto. Sem ele, o usuário não consegue distinguir uma resposta correta de uma invenção — e o sistema inteiro perde a razão de existir. Por isso a citação está no v1, e não no roadmap.

## 1.6 Glossário desta etapa

Só os termos usados até aqui. Cada etapa seguinte adiciona os seus.

| Termo | O que é |
|---|---|
| **RAG** | *Retrieval-Augmented Generation* — recuperar trechos relevantes, aumentar o prompt com eles, e então gerar a resposta |
| **LLM** | *Large Language Model* — o modelo de linguagem que gera a resposta |
| **Parsing** | Extrair o texto de dentro de um arquivo (ex.: de um PDF) |
| **Chunk** | Um pedaço do documento, resultado da divisão do texto |
| **Chunking** | O processo de dividir o texto em chunks |
| **Embedding** | A representação de um texto como uma lista de números (um vetor) |
| **Vetor** | A lista de números que representa o significado de um texto |
| **Busca semântica** | Buscar por significado (vetores próximos), não por palavra exata |
| **pgvector** | Extensão do PostgreSQL que permite guardar vetores e buscar por proximidade |
| **Citação / grounding** | Ancorar a resposta em trechos reais e mostrar quais foram |
| **v1** | A primeira versão completa e funcional — o escopo desta documentação |

---

# Etapa 2 — Ingestão

## 2.1 O que esta etapa faz

**Entra:** um arquivo PDF enviado pelo usuário.
**Sai:** o texto do documento, página por página, pronto para ser dividido na Etapa 3.

É o primeiro passo da fase de indexação — aquela que roda uma vez, no upload, antes de qualquer pergunta existir.

Nada aqui envolve IA. É manipulação de arquivo e extração de texto. É a etapa menos glamourosa do projeto inteiro e uma das que mais determinam a qualidade final: **texto extraído errado vira resposta errada, e nenhum modelo conserta isso depois.** Lixo entra, lixo sai.

## 2.2 O upload

O FastAPI recebe o arquivo pelo tipo `UploadFile`, que transmite em pedaços em vez de carregar o arquivo inteiro na memória.

Três regras não negociáveis:

**Limite de tamanho.** Defina um teto (20 MB é razoável para o v1) e recuse acima disso. Sem limite, um único arquivo grande derruba o processo.

**Valide o tipo pelo conteúdo, não pela extensão.** Renomear `qualquer-coisa.exe` para `documento.pdf` é trivial. A verificação real é ler os primeiros bytes do arquivo: todo PDF começa com a assinatura `%PDF-`. Extensão é sugestão; bytes são fato.

**Nunca use o nome enviado pelo usuário para montar caminho no disco.** Um nome como `../../config/.env` escreve fora do diretório previsto. Gere um nome novo (UUID) e guarde o nome original apenas como metadado no banco.

Upload de arquivo é uma das superfícies de ataque mais clássicas que existem. Tratar isso com cuidado num projeto de portfólio é um sinal profissional forte — e conversa diretamente com o outro projeto do portfólio.

**Decisão do v1:** o PDF original é guardado, com nome gerado, fora da árvore da aplicação. Isso permite reindexar sem novo upload quando você mudar a estratégia de chunking na Etapa 3 — e você vai mudar.

## 2.3 Por que PDF é difícil

Este é o conceito central da etapa, e a razão de ela existir como etapa própria.

**PDF não é um formato de dados. É um formato de impressão.**

Ele não guarda "parágrafo", "coluna" ou "tabela". Ele guarda instruções de desenho: *"desenhe o glifo 'a' na coordenada (72, 340) usando a fonte X"*. A estrutura que o seu olho enxerga na tela não existe no arquivo — ela é uma ilusão produzida pelo posicionamento.

As consequências práticas:

**Ordem de leitura.** A ordem em que o texto aparece no arquivo não é necessariamente a ordem em que se lê. Um documento de duas colunas pode sair com as colunas intercaladas linha a linha, virando sopa.

**Tabelas não existem.** São linhas desenhadas mais texto posicionado. A extração cospe as células em sequência, sem qualquer noção de qual valor pertence a qual coluna.

**Cabeçalho e rodapé se misturam ao corpo.** "Confidencial — página 14 de 200" repete em toda página e entra no texto extraído como se fosse conteúdo.

**Hifenização.** Uma palavra quebrada no fim da linha vira duas palavras diferentes.

**PDF escaneado não tem texto.** É uma imagem de papel dentro de um envelope PDF. A extração retorna vazio, e nenhum ajuste resolve — só OCR.

## 2.4 A escolha da biblioteca

| Biblioteca | A favor | Contra |
|---|---|---|
| **PyMuPDF** (`fitz`) | Rápida, melhor qualidade de extração, entrega página e coordenadas | Licença AGPL |
| **pdfplumber** | Boa com tabelas, licença MIT | Lenta em documentos grandes |
| **pypdf** | Leve, licença BSD | Extração de texto mais fraca |
| **unstructured** | Faz tudo sozinha | Dependência pesada e esconde o trabalho — mesmo motivo pelo qual o LangChain foi descartado |

**Escolha do v1: PyMuPDF.** Melhor extração, e entrega o número da página nativamente — que é o que a citação precisa.

Sobre a licença AGPL: para um projeto de portfólio de código aberto, não há problema. Mas saber que essa distinção existe, e conseguir explicá-la, é o tipo de detalhe que separa quem escolheu a biblioteca por hábito de quem escolheu por decisão.

## 2.5 Extrair página por página

Aqui está a decisão que faz a citação funcionar.

Não extraia o documento inteiro para um único texto. Extraia **página por página**, carregando o número junto:

```python
import fitz

def extrair(caminho: str) -> list[dict]:
    doc = fitz.open(caminho)
    paginas = []
    for numero, pagina in enumerate(doc, start=1):
        texto = pagina.get_text("text", sort=True)
        if texto.strip():
            paginas.append({"pagina": numero, "texto": texto})
    doc.close()
    return paginas
```

O `sort=True` reordena os blocos de texto por posição na página, o que reduz — sem eliminar — o problema de ordem de leitura.

O ponto que vale gravar: **se o número da página se perder aqui, ele não volta nunca.** Todo metadado que a citação vai exibir lá na Etapa 6 nasce nesta etapa. É por isso que ingestão e citação, que parecem estar em pontas opostas do projeto, são a mesma decisão tomada em dois momentos.

## 2.6 Casos que quebram

| Caso | O que acontece | Comportamento do v1 |
|---|---|---|
| PDF escaneado | Extração retorna vazio | Recusa com mensagem clara. OCR fica no roadmap |
| PDF protegido por senha | A biblioteca levanta erro | Recusa com mensagem clara |
| PDF corrompido | Erro na abertura | Recusa |
| Arquivo que não é PDF | Assinatura de bytes falha | Recusa no upload |
| Texto em duas colunas | Sai embaralhado | Aceita — limitação conhecida |
| Tabelas | Viram texto corrido | Aceita — limitação conhecida |

Detectar PDF escaneado é simples: se a soma do texto de todas as páginas for praticamente vazia, é imagem. Uma mensagem clara — *"este PDF parece ser digitalizado; OCR não é suportado"* — vale muito mais do que uma resposta vazia e silenciosa três telas adiante.

**Declarar limitação no README é sinal de maturidade, não de fraqueza.** Todo sistema real tem limitações; a diferença é que os bons as conhecem e as escrevem.

## 2.7 O contrato de saída

Esta etapa entrega à Etapa 3 exatamente isto:

```python
[
    {"pagina": 1, "texto": "..."},
    {"pagina": 2, "texto": "..."},
]
```

Simples de propósito.

Ter o contrato entre etapas explícito é o que permite trocar a implementação de uma sem tocar na outra. Se amanhã o PyMuPDF for substituído por pdfplumber, o chunking não fica sabendo — desde que o contrato se mantenha. Essa é a ideia por trás de "arquitetura" quando se tira o jargão: definir o que cada peça promete entregar, e não deixar as peças espiarem dentro umas das outras.

## 2.8 Como testar

Parsing é determinístico — mesma entrada, mesma saída. Ou seja: perfeitamente testável, ao contrário da parte de IA que vem depois.

- PDF de texto simples → número de páginas e conteúdo conferem
- PDF com uma página em branco → a página não entra na lista
- PDF escaneado (só imagem) → detectado e recusado
- PDF com senha → recusado
- Arquivo `.txt` renomeado para `.pdf` → recusado no upload
- Arquivo acima do limite de tamanho → recusado
- Nome de arquivo com `../` → não escapa do diretório previsto

Guarde os PDFs de teste no repositório em `tests/fixtures/`. São arquivos pequenos e tornam a suíte reproduzível por qualquer pessoa que clonar o projeto.

## 2.9 Glossário desta etapa

| Termo | O que é |
|---|---|
| **UploadFile** | Tipo do FastAPI que recebe arquivo em pedaços, sem carregar tudo na memória |
| **Assinatura de arquivo** (*magic bytes*) | Primeiros bytes que identificam o formato real do arquivo. Em PDF: `%PDF-` |
| **Path traversal** | Ataque que usa `../` no nome do arquivo para escrever fora do diretório previsto |
| **Camada de texto** | O texto de verdade dentro do PDF. PDF escaneado não tem — só imagem |
| **OCR** | *Optical Character Recognition* — extrai texto de imagem. Fora do v1 |
| **Ordem de leitura** | A sequência correta de leitura do conteúdo, que o PDF não garante |
| **Contrato** | A estrutura de dados que uma etapa promete entregar à etapa seguinte |

---

## Próxima etapa

**Etapa 3 — Chunking:** por que dividir o texto, onde cortar, e por que essa é a decisão mais subestimada do projeto inteiro.
