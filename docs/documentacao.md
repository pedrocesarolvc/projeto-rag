# Projeto RAG — Documentação

> **Documento em construção, escrito por etapas.**
> Cada etapa corresponde a um pedaço construível do projeto.

| Etapa | Conteúdo | Status |
|---|---|---|
| **1** | Visão, problema e escopo | ✅ escrita |
| **2** | Ingestão — upload e extração de texto | ✅ escrita |
| **3** | Chunking — divisão do texto | ✅ escrita |
| **4** | Indexação — embeddings e pgvector | ✅ escrita |
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
| Divisão do texto | Corte recursivo por separadores, com sobreposição |
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

# Etapa 3 — Chunking

## 3.1 O que esta etapa faz

**Entra:** a lista de páginas com texto, entregue pela Etapa 2.
**Sai:** uma lista de chunks — pedaços de texto — cada um carregando a página de onde veio.

Ainda é fase de indexação, e ainda não tem IA. É recorte de string. Mas é a decisão mais consequente do projeto inteiro, e a razão está na próxima seção.

## 3.2 Por que o chunk decide tudo

O chunk é, ao mesmo tempo, três coisas:

- **a unidade de busca** — é o chunk que vira vetor, e é entre chunks que a busca compara
- **a unidade de contexto** — é o chunk que vai dentro do prompt da LLM
- **a unidade de citação** — é o chunk que o usuário vê como "de onde saiu essa resposta"

Uma decisão, três consequências. Errar o chunk estraga a busca, o prompt e a citação de uma vez — e nenhuma etapa posterior conserta.

**O motivo que quase ninguém explica: diluição**

A razão óbvia para dividir é que um PDF de 300 páginas não cabe no prompt. Verdade, mas é a razão menos interessante.

A razão de verdade é esta: um chunk gera um único vetor. Um só. Aquele vetor precisa representar o significado do chunk inteiro.

Se o chunk fala de um assunto, o vetor aponta com precisão para aquele assunto. Se o chunk fala de cinco assuntos, o vetor é a média dos cinco — e média de cinco significados não é nenhum dos cinco. É como misturar cinco tintas de cores diferentes: o resultado não é nenhuma delas, é um marrom que não serve para nada.

Um chunk grande demais produz um vetor sem foco. Ele fica vagamente parecido com tudo e fortemente parecido com nada — e some da busca justamente quando a pergunta é específica.

**Chunk pequeno não é economia. É foco.**

## 3.3 O dilema do tamanho

Se pequeno é focado, por que não cortar tudo em frases soltas?

Porque o chunk também precisa se sustentar sozinho. Ele será lido fora de contexto — pela busca e pela LLM — e ninguém vai buscar o que veio antes.

Considere este chunk:

> "Ele deverá ser comunicado com 90 dias de antecedência."

Quem é "ele"? O chunk anterior dizia "o distrato". Este aqui, sozinho, não significa nada: o vetor dele aponta para "algo com prazo de 90 dias", e a pergunta "qual o prazo de rescisão?" passa longe. O pronome ficou órfão.

| Chunk grande demais | Chunk pequeno demais |
|---|---|
| Vetor diluído, some da busca | Vetor focado, mas em nada útil |
| Enche o prompt de ruído | Perde o sujeito da frase |
| Citação vaga: "está nesta página aí" | Referências órfãs, pronomes sem dono |
| Custa mais tokens por pergunta | Fragmenta uma ideia em cinco pedaços |

Não existe tamanho universalmente certo. Existe o tamanho certo para o seu tipo de documento, e ele se descobre medindo — que é exatamente o que os evals fazem, e por isso eles estão no roadmap.

## 3.4 Sobreposição (overlap)

O corte é cego: ele cai onde cair, e muitas vezes cai no meio de uma ideia.

A sobreposição resolve isso repetindo o final do chunk anterior no início do próximo. A ideia cortada aparece inteira em pelo menos um dos dois.

```
Chunk 1: [────────────────────]
Chunk 2:                 [────────────────────]
                          ↑ repete o fim do anterior
```

Valor típico: 10% a 20% do tamanho do chunk.

O preço: o texto repetido ocupa espaço no banco, e o mesmo trecho pode ser recuperado duas vezes pela busca. É um preço barato perto de mutilar uma cláusula ao meio.

## 3.5 As estratégias de corte

| Estratégia | Como funciona | A favor | Contra |
|---|---|---|---|
| Tamanho fixo | Corta a cada N caracteres | Trivial de escrever | Corta no meio da palavra, da frase, da ideia |
| Recursivo por separadores | Tenta cortar em `\n\n`; se o pedaço ainda for grande, tenta `\n`; depois `.`; depois espaço | Respeita fronteiras naturais do texto | Ainda usa tamanho como teto |
| Estruturado | Corta por seção, cláusula, título | Melhor qualidade possível | Depende de detectar estrutura — que o PDF não entrega (ver Etapa 2) |
| Semântico | Corta onde o assunto muda, medindo por embedding | Sofisticado | Caro e complexo; vetoriza para decidir onde vetorizar |

**A decisão do v1: corte recursivo**

Correção honesta: a Etapa 1 dizia "tamanho fixo com sobreposição". Escrevendo esta etapa, isso está errado. O corte recursivo custa umas vinte linhas a mais e é muito melhor — parágrafo é uma fronteira de significado, e cortar nele é praticamente de graça. A Etapa 1 já foi corrigida.

Documentação é viva. Revisar uma decisão quando você entende melhor o problema não é falha de planejamento — é o planejamento funcionando.

Por que não o estruturado: ele depende de saber onde começa uma seção. E a Etapa 2 já estabeleceu que o PDF não guarda estrutura — guarda glifos em coordenadas. Detectar título por tamanho de fonte é heurística frágil, e vira um projeto dentro do projeto. Fica no roadmap.

## 3.6 Escolhendo os números

Caractere ou token? O modelo de embedding conta em tokens, não em caracteres. Token é o pedaço de palavra que o modelo enxerga — em português, um token dá mais ou menos 4 caracteres. Todo modelo de embedding tem um teto de tokens; passar do teto significa texto silenciosamente truncado, e o final do chunk simplesmente não existe para a busca.

Ponto de partida do v1:

| Parâmetro | Valor | Por quê |
|---|---|---|
| Tamanho do chunk | ~110 tokens (~450 caracteres) | Cabe dentro do teto de 128 tokens do modelo de embedding escolhido na Etapa 4, com margem |
| Sobreposição | ~15 tokens (15%) | Cobre a ideia cortada na fronteira |

Esses números são um chute educado, e está tudo bem. Sem evals, não há como afirmar que o tamanho ideal é exatamente este — só há como afirmar que é razoável. Declare isso no README em vez de fingir precisão que não existe.

**Correção, feita na Etapa 4:** esta seção originalmente propunha ~400 tokens (~1600 caracteres). Medindo depois, na Etapa 4, descobri que o modelo de embedding escolhido trunca silenciosamente acima de 128 tokens — exatamente o risco que o primeiro parágrafo desta seção descreve. Um chunk de 1600 caracteres virava vetor de só ~37% do seu próprio texto. Números ajustados para caber no modelo de verdade, não no chute original.

Você vai querer mudar esses números. É exatamente por isso que a Etapa 2 decidiu guardar o PDF original: reindexar com outro tamanho, sem pedir upload de novo.

## 3.7 O chunk que atravessa a página

Aqui aparece um conflito que só existe porque a Etapa 2 tomou a decisão certa de guardar a página.

Se você juntar todas as páginas num texto só e cortar, um chunk pode começar na página 4 e terminar na 5. Aí "qual é a página deste chunk?" não tem resposta única — precisa virar `pagina_inicial` e `pagina_final`, e o corte precisa rastrear posição durante a concatenação.

**Decisão do v1:** o chunk nunca atravessa a página. Corta-se dentro de cada página, independentemente.

O que se ganha: página não ambígua, citação exata, código simples.

O que se perde: um parágrafo que atravessa a virada de página vira dois chunks mutilados — exatamente o problema do pronome órfão da seção 3.3, agora causado pela sua própria decisão.

É um trade-off real, não uma escolha óbvia. O v1 escolhe a citação exata; o roadmap fica com o chunk multipágina. Isso vai no README como limitação conhecida.

## 3.8 O contrato de saída

```python
[
    {
        "indice": 0,          # posição do chunk no documento
        "pagina": 1,
        "texto": "...",
    },
    {
        "indice": 1,
        "pagina": 1,
        "texto": "...",
    },
]
```

O `indice` serve para ordenar e para uma melhoria futura barata: ao exibir a citação, mostrar o chunk vizinho para dar contexto ao usuário.

A Etapa 4 acrescenta o vetor a cada um desses registros. O contrato cresce; a forma não muda.

## 3.9 Como testar

Chunking é determinístico — dá para testar de verdade, como a ingestão. Aproveite, porque a partir da Etapa 5 acaba a certeza.

- Texto menor que o tamanho do chunk → devolve exatamente 1 chunk
- Texto vazio → devolve 0 chunks
- Nenhum chunk excede o tamanho máximo
- Nenhuma palavra é cortada ao meio
- Todo chunk carrega uma página válida
- Nenhum chunk atravessa páginas
- A sobreposição existe de fato: o fim do chunk N aparece no início do chunk N+1
- Os índices são sequenciais e sem buraco
- Um parágrafo curto seguido de outro não é fundido nem estilhaçado

O teste da sobreposição é o que mais pega bug. É fácil escrever um splitter que parece sobrepor e não sobrepõe.

## 3.10 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Chunk** | Um pedaço do documento. Unidade de busca, de contexto e de citação, ao mesmo tempo |
| **Chunking** | O processo de dividir o texto em chunks |
| **Overlap (sobreposição)** | Repetir o fim de um chunk no início do seguinte, para não mutilar ideias na fronteira |
| **Token** | O pedaço de palavra que o modelo enxerga. Em português, cerca de 4 caracteres |
| **Diluição** | O efeito de um chunk com muitos assuntos gerar um vetor que é a média deles — e não representa nenhum |
| **Splitter recursivo** | Cortador que tenta separadores em ordem de prioridade: parágrafo, linha, frase, palavra |
| **Truncamento** | Quando o texto passa do limite de tokens do modelo e o excedente é descartado em silêncio |
| **Granularidade** | O tamanho da unidade escolhida. Grossa = chunks grandes; fina = chunks pequenos |

---

# Etapa 4 — Indexação

## 4.1 O que esta etapa faz

**Entra:** a lista de chunks da Etapa 3.
**Sai:** os mesmos chunks, cada um agora com um vetor, gravados no PostgreSQL e prontos para busca.

É o último passo da fase de indexação. Depois desta etapa, o documento está inteiramente preparado no banco — e, como você mesmo formulou, preparado para uma pergunta que talvez nunca venha.

Aqui, enfim, aparece a IA. Mas não a IA que gera resposta — essa é a Etapa 6. A IA daqui faz uma coisa só, e mais estranha: transforma texto em números.

## 4.2 O embedding, sem misticismo

Um modelo de embedding recebe um texto e devolve uma lista de números. Sempre do mesmo tamanho — 384, 768, 1024 números, dependendo do modelo. Essa lista é o vetor.

```
"prazo de rescisão"  →  [0.021, -0.44, 0.87, ..., 0.03]
                         └────────  768 números  ────────┘
```

O mesmo texto sempre gera o mesmo vetor. Textos diferentes geram vetores diferentes. Até aqui, poderia ser qualquer função que embaralha texto em número.

A propriedade que muda tudo é uma só:

**Textos com significado parecido geram vetores próximos. Textos com significado distante geram vetores distantes.**

Não é sobre as palavras. É sobre o sentido. "Cão", "cachorro" e "canino" caem quase no mesmo lugar. "Distrato" e "rescisão" caem perto. "Planilha" cai longe dos três. Ninguém programou uma lista de sinônimos — a proximidade emergiu do treinamento do modelo em bilhões de frases, onde palavras que aparecem em contextos parecidos foram empurradas para posições parecidas.

## 4.3 A intuição que faz assentar: o mapa

Esqueça 768 dimensões — ninguém visualiza isso. Pense em duas.

Imagine um mapa onde cada texto é um ponto. O modelo de embedding é o cartógrafo: ele posiciona cada texto no mapa de modo que distância = diferença de significado.

- "prazo de rescisão" e "distrato em 90 dias" ficam no mesmo bairro
- "receita de bolo" fica do outro lado da cidade
- "cláusula de multa" fica na região vizinha à de rescisão — perto, mas não em cima

Buscar, então, é geometria pura: você joga a pergunta no mapa e pega os pontos mais próximos. Sem entender nada de linguagem — só medindo distância.

O vetor de verdade tem centenas de dimensões em vez de duas, o que dá ao modelo espaço para representar nuance ("prazo de rescisão" difere de "prazo de pagamento" numa dimensão, mas ambos são "prazo" em outra). A intuição do mapa, porém, se mantém inteira: perto é parecido, longe é diferente.

## 4.4 Como se mede a distância

Duas formas aparecem o tempo todo:

**Distância euclidiana** — a distância "de régua" entre dois pontos. A que a intuição do mapa sugere.

**Similaridade de cosseno** — mede o ângulo entre dois vetores, ignorando o comprimento. É a mais usada em RAG, e a razão é sutil mas importante: um chunk longo e um chunk curto sobre o mesmo assunto têm vetores de comprimentos diferentes, mas apontam para a mesma direção. O cosseno enxerga que falam do mesmo tema; a euclidiana se confunde com a diferença de tamanho.

Para o v1, basta saber que o cosseno é o padrão e o porquê. O pgvector implementa as duas — a escolha é um operador na query.

## 4.5 A escolha do modelo

O modelo de embedding não é a LLM que responde. São dois modelos diferentes, com funções diferentes: o de embedding converte texto em vetor (Etapa 4); a LLM gera texto (Etapa 6). Confundi-los é comum e vale separar desde já.

Duas rotas para gerar embeddings:

| | Via API | Local (sentence-transformers) |
|---|---|---|
| Como funciona | Manda o texto para um serviço, recebe o vetor | Roda o modelo na sua máquina |
| A favor | Zero setup, qualidade alta | Grátis, offline, dado não sai da máquina |
| Contra | Custa por uso, exige rede, dado sai | Consome RAM, qualidade um pouco menor |

**Decisão do v1: modelo local, multilíngue.** Um modelo da família sentence-transformers com suporte a português. Três motivos: é grátis (importa num projeto de portfólio), roda offline (a demo funciona sem internet e sem chave de API), e não manda o documento para fora — o que conversa direto com a tese do outro projeto do portfólio.

**A regra inegociável:** o mesmo modelo que vetoriza os chunks tem de vetorizar a pergunta. Vetores de modelos diferentes vivem em mapas diferentes — medir distância entre eles é comparar coordenadas de duas cidades distintas. É por isso que o modelo escolhido é configuração fixa do projeto, não uma escolha por requisição. Trocar o modelo obriga a reindexar tudo.

## 4.6 O número de dimensões é um compromisso

Cada modelo produz vetores de um tamanho fixo. Mais dimensões capturam mais nuance, mas custam mais espaço no banco e deixam a busca mais lenta. Menos dimensões são enxutas e rápidas, com menos capacidade de distinção fina.

Para o v1 isso não é uma decisão sua: você adota o tamanho que o modelo escolhido produz. Só há uma regra rígida — a coluna do banco precisa ter exatamente esse tamanho. Um modelo de 768 exige uma coluna `vector(768)`. Cravar o número errado é erro de dimensão na primeira inserção.

## 4.7 O pgvector

O pgvector é a extensão que ensina o PostgreSQL a guardar vetores e a medir distância entre eles. É o que dispensa um banco vetorial dedicado.

Ele adiciona:

**Um tipo de coluna** — `vector(768)`, uma coluna que guarda a lista de números.

**Operadores de distância** — símbolos que calculam proximidade direto no SQL:

| Operador | Mede |
|---|---|
| `<->` | Distância euclidiana |
| `<=>` | Distância de cosseno |
| `<#>` | Produto interno negativo |

Com isso, "ache os 5 chunks mais próximos desta pergunta" é uma query comum:

```sql
SELECT indice, pagina, texto
FROM chunks
ORDER BY vetor <=> :vetor_da_pergunta
LIMIT 5;
```

Esse `ORDER BY ... LIMIT 5` é a busca semântica inteira. Toda a Etapa 5 é, no fundo, essa query e o que se faz ao redor dela. A "busca" que parecia o coração misterioso do RAG é uma ordenação por distância.

## 4.8 O índice: a pegadinha que todo mundo encontra

A query acima, sem índice, compara a pergunta com todos os chunks, um por um. Para um PDF são milhares — tolerável. Para um acervo, milhões — lento demais.

Um índice vetorial resolve, e o pgvector oferece dois: HNSW e IVFFlat. Para o v1 basta saber que o HNSW é o padrão atual (mais rápido nas buscas, um pouco mais lento para construir) e que ele existe para não varrer a tabela inteira a cada pergunta.

Mas aqui está a pegadinha que quase todo projeto encontra — e vale saber antes de bater nela:

O índice vetorial é **aproximado**. O "A" de HNSW é de *Approximate*. Para ganhar velocidade, ele pode não devolver o vizinho mais próximo exato — devolve algo quase sempre certo, com uma chance pequena de pular o melhor resultado.

Ou seja: com índice, a busca fica rápida e ligeiramente imprecisa; sem índice, fica exata e lenta. Para um acervo grande, troca-se de bom grado um pouquinho de precisão por muita velocidade. Saber que esse trade-off existe — e que a lentidão sem índice não é bug, é a busca exata trabalhando — é exatamente o tipo de coisa que separa quem leu tutorial de quem entendeu.

## 4.9 O que se grava

A tabela que fecha a fase de indexação:

```sql
CREATE TABLE chunks (
    id          BIGSERIAL PRIMARY KEY,
    documento_id BIGINT NOT NULL,
    indice      INT NOT NULL,       -- posição no documento (Etapa 3)
    pagina      INT NOT NULL,       -- de onde veio (Etapa 2)
    texto       TEXT NOT NULL,      -- o texto do chunk
    vetor       VECTOR(768) NOT NULL -- o embedding (Etapa 4)
);
```

Repare em como cada coluna nasceu numa etapa diferente. `pagina` na 2, `indice` e `texto` na 3, `vetor` na 4. A tabela é a fase de indexação inteira, materializada. Cada decisão anterior deixou aqui a sua marca — e a citação, lá na Etapa 6, vai ler `texto` e `pagina` destas linhas.

O texto é guardado ao lado do vetor de propósito: na hora da resposta, você precisa do texto legível para mandar à LLM e para mostrar na citação. O vetor serve para achar; o texto, para usar.

## 4.10 Como testar

Aqui a testabilidade começa a mudar de natureza, e vale entender por quê.

O embedding não é determinístico no sentido de que você não sabe prever os números — não dá para escrever "o vetor de 'contrato' deve ser [0.2, ...]". Então some o tipo de teste que a ingestão e o chunking permitiam. O que se testa aqui são propriedades e comportamentos, não valores:

- O vetor gerado tem exatamente a dimensão da coluna (768) — pega erro de configuração
- O mesmo texto gera o mesmo vetor duas vezes — confirma determinismo do modelo
- Dois textos de sentido próximo ("cachorro" / "cão") produzem distância menor que dois distantes ("cachorro" / "planilha") — este é o teste que prova que o embedding funciona, e é lindo de ver passar
- Inserir e recuperar um vetor do Postgres devolve o mesmo vetor — valida o pgvector
- A query de distância devolve os chunks na ordem esperada num documento pequeno e controlado

Esse terceiro teste é o mais valioso do projeto até aqui: ele verifica, em código, a afirmação central de toda a etapa — perto é parecido. Se ele passa, o conceito não é fé; é fato medido.

## 4.11 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Embedding** | A representação de um texto como vetor de números fixos |
| **Modelo de embedding** | O modelo que converte texto em vetor. Não é a LLM que responde |
| **Vetor** | A lista de números. Uma posição num mapa de significados |
| **Espaço vetorial** | O "mapa" onde os textos são pontos e a distância mede diferença de sentido |
| **Dimensão** | Quantos números o vetor tem (384, 768, 1024...). Fixo por modelo |
| **Similaridade de cosseno** | Distância pelo ângulo entre vetores, ignorando o comprimento. Padrão em RAG |
| **pgvector** | Extensão que dá ao PostgreSQL o tipo vetor e os operadores de distância |
| **HNSW / IVFFlat** | Índices vetoriais. Trocam um pouco de precisão por muita velocidade |
| **Busca aproximada (ANN)** | *Approximate Nearest Neighbor* — acha vizinhos quase sempre certos, muito mais rápido |
| **Reindexar** | Gerar os vetores de novo. Necessário se o modelo ou o chunking mudarem |

Um lembrete que vem do seu próprio insight: a dimensão da coluna (`vector(768)` ou o que o seu modelo produzir) tem que bater exata com o que o modelo gera. Erro de dimensão estoura na primeira inserção, e a mensagem do Postgres nem sempre é óbvia — se der um erro estranho ao inserir vetor, olhe a dimensão primeiro.

**Um segundo lembrete, que a dimensão sozinha não cobre:** dimensão errada estoura na hora — é barulhento, você percebe na primeira inserção. O teto de tokens do modelo (`max_seq_length`) é o oposto: estoura em silêncio. O modelo local escolhido nesta etapa aceita só 128 tokens; o tamanho de chunk da Etapa 3 previa ~400. Um chunk de 1600 caracteres virava vetor de apenas ~37% do próprio texto — sem erro, sem aviso, só busca pior. A Etapa 3 já foi corrigida (seção 3.6) para caber no teto real do modelo. Ao trocar de modelo de embedding no futuro, confira os dois números — dimensão e `max_seq_length` — não só o primeiro.

---

## Próxima etapa

**Etapa 5 — Recuperação:** a busca de verdade — como a pergunta vira a mesma query `ORDER BY ... LIMIT` que fechou esta etapa, e o que fazer com os chunks que ela devolve.
