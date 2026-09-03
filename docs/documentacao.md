# Lastro — Documentação

> **Documento em construção, escrito por etapas.**
> Cada etapa corresponde a um pedaço construível do projeto.

| Etapa | Conteúdo | Status |
|---|---|---|
| **1** | Visão, problema e escopo | ✅ escrita |
| **2** | Ingestão — upload e extração de texto | ✅ escrita |
| **3** | Chunking — divisão do texto | ✅ escrita |
| **4** | Indexação — embeddings e pgvector | ✅ escrita |
| **5** | Recuperação — a busca | ✅ escrita |
| **6** | Geração — prompt, resposta e citação | ✅ escrita |
| **7** | Entrega — API, interface, testes e Docker | ✅ escrita |

---

# Etapa 1 — Visão, problema e escopo

## 1.1 O problema

Uma LLM sabe o que estava nos dados de treinamento dela. Ela não sabe o seu contrato, o seu manual técnico, o seu relatório financeiro. Se você perguntar, ela responde mesmo assim — inventando com confiança, porque gerar texto plausível é o que ela faz.

Ao mesmo tempo, quase toda empresa tem um acervo de documentos que ninguém lê inteiro: manuais de centenas de páginas, contratos, normas internas, relatórios. A informação existe, mas encontrar a resposta exige saber onde procurar.

**O projeto resolve os dois problemas ao mesmo tempo:** permite perguntar em linguagem natural a um acervo de documentos privados e receber uma resposta fundamentada, com o trecho exato que a originou.

## 1.2 O que é o projeto

**Lastro** é uma aplicação web onde o usuário sobe um documento e o consulta em linguagem natural.

O nome não é ornamental: *lastro* é aquilo que dá sustentação e garantia. É exatamente o que distingue o sistema de um chatbot qualquer — toda resposta é ancorada em um trecho verificável do documento, e o usuário vê qual.

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
| Divisão do texto | Corte recursivo por separadores, com sobreposição *(revisto na Etapa 3)* |
| Vetorização | Um modelo de embedding, sem comparações |
| Armazenamento | PostgreSQL com a extensão pgvector |
| Busca | Apenas semântica (por similaridade) |
| Resposta | Uma LLM, respondendo com base nos trechos |
| Citação | Exibe os trechos que fundamentaram a resposta |
| Cadastro e login | Exigidos apenas no momento da primeira pergunta (ver 1.5) |
| Documentos por usuário | Cada usuário acessa apenas os próprios documentos |
| Interface | Upload + chat, sem enfeite |
| Testes | Pytest nas partes determinísticas |
| Empacotamento | Docker Compose subindo app + banco |

### Fica no roadmap

| Item | Por que fica de fora agora |
|---|---|
| Suporte a DOCX | O PDF já cobre a demonstração; DOCX é mais do mesmo |
| Múltiplos documentos na mesma consulta | Exige gestão de coleções — complexidade sem novo aprendizado |
| Chunking estruturado | Melhoria de qualidade, não de arquitetura |
| Busca híbrida | O upgrade mais valioso do v2, mas depende da busca simples existir antes |
| Reranking | Otimização fina; só faz sentido com busca já funcionando |
| Evals | Só medem o que já existe |
| Streaming da resposta | Melhoria de experiência, não de arquitetura |
| OCR para PDFs digitalizados | Recusado com mensagem clara no v1 |
| Compartilhamento de documentos entre usuários | Exige permissões; o v1 isola por dono |

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

**Cadastro adiado: autenticação só na primeira pergunta.**
O usuário pode enviar um documento e vê-lo processado sem qualquer cadastro. A tela de login e cadastro aparece apenas quando ele tenta fazer a **primeira pergunta**.

O motivo é de produto: exigir cadastro antes de o usuário ver qualquer valor é a forma mais eficiente de perdê-lo. Ao adiar a barreira para o momento em que ele já subiu um documento e quer a resposta, o cadastro deixa de ser um pedágio e passa a ser o que preserva o trabalho já feito — o documento processado e o histórico de perguntas ficam vinculados à conta, e ele retoma de onde parou.

Isso tem uma **consequência técnica que precisa ser tratada explicitamente**: entre o upload e o cadastro, o documento pertence a uma sessão anônima. No momento em que a conta é criada ou o login é feito, esse documento precisa ser **transferido para o usuário recém-autenticado**. Se essa migração falhar, o usuário se cadastra e descobre que perdeu o upload — resultado pior do que ter pedido o cadastro logo no início. A transferência é detalhada na Etapa 7 e tem teste próprio.

Duas consequências menores, registradas para não virarem surpresa:

- **Documentos anônimos consomem processamento.** Alguém pode subir arquivos e nunca se cadastrar. O v1 trata isso com o limite de tamanho já previsto na Etapa 2 e com expiração de sessões anônimas antigas.
- **A sessão anônima precisa de identificação própria** — um identificador de sessão, distinto do usuário — para que o documento tenha dono mesmo antes de existir conta.

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
| **Cadastro adiado** | Exigir a conta apenas quando o usuário já viu valor — aqui, na primeira pergunta |
| **Sessão anônima** | Identificação temporária que dá dono ao documento antes de existir conta |
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

O chunk é, ao mesmo tempo, **três coisas**:

- a **unidade de busca** — é o chunk que vira vetor, e é entre chunks que a busca compara
- a **unidade de contexto** — é o chunk que vai dentro do prompt da LLM
- a **unidade de citação** — é o chunk que o usuário vê como "de onde saiu essa resposta"

Uma decisão, três consequências. Errar o chunk estraga a busca, o prompt e a citação de uma vez — e nenhuma etapa posterior conserta.

### O motivo que quase ninguém explica: diluição

A razão óbvia para dividir é que um PDF de 300 páginas não cabe no prompt. Verdade, mas é a razão menos interessante.

A razão de verdade é esta: **um chunk gera um único vetor.** Um só. Aquele vetor precisa representar o significado do chunk inteiro.

Se o chunk fala de um assunto, o vetor aponta com precisão para aquele assunto. Se o chunk fala de cinco assuntos, o vetor é a **média** dos cinco — e média de cinco significados não é nenhum dos cinco. É como misturar cinco tintas de cores diferentes: o resultado não é nenhuma delas, é um marrom que não serve para nada.

Um chunk grande demais produz um vetor sem foco. Ele fica vagamente parecido com tudo e fortemente parecido com nada — e some da busca justamente quando a pergunta é específica.

**Chunk pequeno não é economia. É foco.**

## 3.3 O dilema do tamanho

Se pequeno é focado, por que não cortar tudo em frases soltas?

Porque o chunk também precisa **se sustentar sozinho**. Ele será lido fora de contexto — pela busca e pela LLM — e ninguém vai buscar o que veio antes.

Considere este chunk:

> "Ele deverá ser comunicado com 90 dias de antecedência."

Quem é "ele"? O chunk anterior dizia "o distrato". Este aqui, sozinho, não significa nada: o vetor dele aponta para "algo com prazo de 90 dias", e a pergunta *"qual o prazo de rescisão?"* passa longe. O pronome ficou órfão.

| Chunk grande demais | Chunk pequeno demais |
|---|---|
| Vetor diluído, some da busca | Vetor focado, mas em nada útil |
| Enche o prompt de ruído | Perde o sujeito da frase |
| Citação vaga: "está nesta página aí" | Referências órfãs, pronomes sem dono |
| Custa mais tokens por pergunta | Fragmenta uma ideia em cinco pedaços |

Não existe tamanho universalmente certo. Existe o tamanho certo **para o seu tipo de documento**, e ele se descobre medindo — que é exatamente o que os evals fazem, e por isso eles estão no roadmap.

## 3.4 Sobreposição (overlap)

O corte é cego: ele cai onde cair, e muitas vezes cai no meio de uma ideia.

A sobreposição resolve isso repetindo o final do chunk anterior no início do próximo. A ideia cortada aparece inteira em pelo menos um dos dois.

```
Chunk 1: [────────────────────]
Chunk 2:                 [────────────────────]
                          ↑ repete o fim do anterior
```

Valor típico: **10% a 20%** do tamanho do chunk.

O preço: o texto repetido ocupa espaço no banco, e o mesmo trecho pode ser recuperado duas vezes pela busca. É um preço barato perto de mutilar uma cláusula ao meio.

## 3.5 As estratégias de corte

| Estratégia | Como funciona | A favor | Contra |
|---|---|---|---|
| **Tamanho fixo** | Corta a cada N caracteres | Trivial de escrever | Corta no meio da palavra, da frase, da ideia |
| **Recursivo por separadores** | Tenta cortar em `\n\n`; se o pedaço ainda for grande, tenta `\n`; depois `. `; depois espaço | Respeita fronteiras naturais do texto | Ainda usa tamanho como teto |
| **Estruturado** | Corta por seção, cláusula, título | Melhor qualidade possível | Depende de detectar estrutura — que o PDF não entrega (ver Etapa 2) |
| **Semântico** | Corta onde o assunto muda, medindo por embedding | Sofisticado | Caro e complexo; vetoriza para decidir onde vetorizar |

### A decisão do v1: corte recursivo

**Correção honesta:** a Etapa 1 dizia "tamanho fixo com sobreposição". Escrevendo esta etapa, isso está errado. O corte recursivo custa umas vinte linhas a mais e é muito melhor — parágrafo é uma fronteira de significado, e cortar nele é praticamente de graça. A Etapa 1 já foi corrigida.

Documentação é viva. Revisar uma decisão quando você entende melhor o problema não é falha de planejamento — é o planejamento funcionando.

**Por que não o estruturado:** ele depende de saber onde começa uma seção. E a Etapa 2 já estabeleceu que o PDF não guarda estrutura — guarda glifos em coordenadas. Detectar título por tamanho de fonte é heurística frágil, e vira um projeto dentro do projeto. Fica no roadmap.

## 3.6 Escolhendo os números

**Caractere ou token?** O modelo de embedding conta em **tokens**, não em caracteres. Token é o pedaço de palavra que o modelo enxerga — em português, um token dá mais ou menos 4 caracteres. Todo modelo de embedding tem um teto de tokens; passar do teto significa texto **silenciosamente truncado**, e o final do chunk simplesmente não existe para a busca.

**Ponto de partida do v1:**

| Parâmetro | Valor | Por quê |
|---|---|---|
| Tamanho do chunk | ~400 tokens (~1600 caracteres) | Cabe um parágrafo ou dois — grande o bastante para se sustentar, pequeno o bastante para focar |
| Sobreposição | ~60 tokens (15%) | Cobre a ideia cortada na fronteira |

**Esses números são um chute educado, e está tudo bem.** Sem evals, não há como afirmar que 400 é melhor que 300 — só há como afirmar que é razoável. Declare isso no README em vez de fingir precisão que não existe.

Você vai querer mudar esses números. É exatamente por isso que a Etapa 2 decidiu guardar o PDF original: reindexar com outro tamanho, sem pedir upload de novo.

## 3.7 O chunk que atravessa a página

Aqui aparece um conflito que só existe porque a Etapa 2 tomou a decisão certa de guardar a página.

Se você juntar todas as páginas num texto só e cortar, um chunk pode começar na página 4 e terminar na 5. Aí "qual é a página deste chunk?" não tem resposta única — precisa virar `pagina_inicial` e `pagina_final`, e o corte precisa rastrear posição durante a concatenação.

**Decisão do v1: o chunk nunca atravessa a página.** Corta-se dentro de cada página, independentemente.

O que se ganha: página não ambígua, citação exata, código simples.

O que se perde: um parágrafo que atravessa a virada de página vira dois chunks mutilados — exatamente o problema do pronome órfão da seção 3.3, agora causado pela sua própria decisão.

É um trade-off real, não uma escolha óbvia. O v1 escolhe a citação exata; o roadmap fica com o chunk multipágina. **Isso vai no README como limitação conhecida.**

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

O teste da sobreposição é o que mais pega bug. É fácil escrever um splitter que *parece* sobrepor e não sobrepõe.

## 3.10 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Chunk** | Um pedaço do documento. Unidade de busca, de contexto e de citação, ao mesmo tempo |
| **Chunking** | O processo de dividir o texto em chunks |
| **Overlap** (sobreposição) | Repetir o fim de um chunk no início do seguinte, para não mutilar ideias na fronteira |
| **Token** | O pedaço de palavra que o modelo enxerga. Em português, cerca de 4 caracteres |
| **Diluição** | O efeito de um chunk com muitos assuntos gerar um vetor que é a média deles — e não representa nenhum |
| **Splitter recursivo** | Cortador que tenta separadores em ordem de prioridade: parágrafo, linha, frase, palavra |
| **Truncamento** | Quando o texto passa do limite de tokens do modelo e o excedente é descartado em silêncio |
| **Granularidade** | O tamanho da unidade escolhida. Grossa = chunks grandes; fina = chunks pequenos |

---

## Próxima etapa

**Etapa 4 — Indexação:** o que é um embedding de verdade, por que texto vira número, e como o PostgreSQL guarda e busca vetores.

---

# Etapa 4 — Indexação

## 4.1 O que esta etapa faz

**Entra:** a lista de chunks da Etapa 3.
**Sai:** os mesmos chunks, cada um agora com um vetor, gravados no PostgreSQL e prontos para busca.

É o último passo da fase de indexação. Depois desta etapa, o documento está inteiramente preparado no banco — e, como você mesmo formulou, preparado para uma pergunta que talvez nunca venha.

Aqui, enfim, aparece a IA. Mas não a IA que gera resposta — essa é a Etapa 6. A IA daqui faz uma coisa só, e mais estranha: transforma texto em números.

## 4.2 O embedding, sem misticismo

Um **modelo de embedding** recebe um texto e devolve uma lista de números. Sempre do mesmo tamanho — 384, 768, 1024 números, dependendo do modelo. Essa lista é o **vetor**.

```
"prazo de rescisão"  →  [0.021, -0.44, 0.87, ..., 0.03]
                         └────────  768 números  ────────┘
```

O mesmo texto sempre gera o mesmo vetor. Textos diferentes geram vetores diferentes. Até aqui, poderia ser qualquer função que embaralha texto em número.

A propriedade que muda tudo é uma só:

**Textos com significado parecido geram vetores próximos. Textos com significado distante geram vetores distantes.**

Não é sobre as palavras. É sobre o sentido. "Cão", "cachorro" e "canino" caem quase no mesmo lugar. "Distrato" e "rescisão" caem perto. "Planilha" cai longe dos três. Ninguém programou uma lista de sinônimos — a proximidade **emergiu** do treinamento do modelo em bilhões de frases, onde palavras que aparecem em contextos parecidos foram empurradas para posições parecidas.

## 4.3 A intuição que faz assentar: o mapa

Esqueça 768 dimensões — ninguém visualiza isso. Pense em duas.

Imagine um mapa onde cada texto é um ponto. O modelo de embedding é o cartógrafo: ele posiciona cada texto no mapa de modo que **distância = diferença de significado**.

- "prazo de rescisão" e "distrato em 90 dias" ficam no mesmo bairro
- "receita de bolo" fica do outro lado da cidade
- "cláusula de multa" fica na região vizinha à de rescisão — perto, mas não em cima

Buscar, então, é geometria pura: você joga a pergunta no mapa e pega os pontos mais próximos. Sem entender nada de linguagem — só medindo distância.

O vetor de verdade tem centenas de dimensões em vez de duas, o que dá ao modelo espaço para representar nuance ("prazo de rescisão" difere de "prazo de pagamento" numa dimensão, mas ambos são "prazo" em outra). A intuição do mapa, porém, se mantém inteira: **perto é parecido, longe é diferente.**

## 4.4 Como se mede a distância

Duas formas aparecem o tempo todo:

**Distância euclidiana** — a distância "de régua" entre dois pontos. A que a intuição do mapa sugere.

**Similaridade de cosseno** — mede o **ângulo** entre dois vetores, ignorando o comprimento. É a mais usada em RAG, e a razão é sutil mas importante: um chunk longo e um chunk curto sobre o mesmo assunto têm vetores de comprimentos diferentes, mas *apontam para a mesma direção*. O cosseno enxerga que falam do mesmo tema; a euclidiana se confunde com a diferença de tamanho.

Para o v1, basta saber que o cosseno é o padrão e o porquê. O pgvector implementa as duas — a escolha é um operador na query.

## 4.5 A escolha do modelo

O modelo de embedding **não é** a LLM que responde. São dois modelos diferentes, com funções diferentes: o de embedding converte texto em vetor (Etapa 4); a LLM gera texto (Etapa 6). Confundi-los é comum e vale separar desde já.

Duas rotas para gerar embeddings:

| | Via API | Local (`sentence-transformers`) |
|---|---|---|
| Como funciona | Manda o texto para um serviço, recebe o vetor | Roda o modelo na sua máquina |
| A favor | Zero setup, qualidade alta | Grátis, offline, dado não sai da máquina |
| Contra | Custa por uso, exige rede, dado sai | Consome RAM, qualidade um pouco menor |

**Decisão do v1: modelo local, multilíngue.** Um modelo da família `sentence-transformers` com suporte a português. Três motivos: é grátis (importa num projeto de portfólio), roda offline (a demo funciona sem internet e sem chave de API), e não manda o documento para fora — o que conversa direto com a tese do outro projeto do portfólio.

**A regra inegociável:** o mesmo modelo que vetoriza os chunks tem de vetorizar a pergunta. Vetores de modelos diferentes vivem em mapas diferentes — medir distância entre eles é comparar coordenadas de duas cidades distintas. É por isso que o modelo escolhido é configuração fixa do projeto, não uma escolha por requisição. Trocar o modelo obriga a reindexar tudo.

## 4.6 O número de dimensões é um compromisso

Cada modelo produz vetores de um tamanho fixo. Mais dimensões capturam mais nuance, mas custam mais espaço no banco e deixam a busca mais lenta. Menos dimensões são enxutas e rápidas, com menos capacidade de distinção fina.

Para o v1 isso não é uma decisão sua: você adota o tamanho que o modelo escolhido produz. Só há uma regra rígida — **a coluna do banco precisa ter exatamente esse tamanho.** Um modelo de 768 exige uma coluna `vector(768)`. Cravar o número errado é erro de dimensão na primeira inserção.

## 4.7 O pgvector

O **pgvector** é a extensão que ensina o PostgreSQL a guardar vetores e a medir distância entre eles. É o que dispensa um banco vetorial dedicado.

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

Esse `ORDER BY ... LIMIT 5` **é** a busca semântica inteira. Toda a Etapa 5 é, no fundo, essa query e o que se faz ao redor dela. A "busca" que parecia o coração misterioso do RAG é uma ordenação por distância.

## 4.8 O índice: a pegadinha que todo mundo encontra

A query acima, sem índice, compara a pergunta com **todos** os chunks, um por um. Para um PDF são milhares — tolerável. Para um acervo, milhões — lento demais.

Um índice vetorial resolve, e o pgvector oferece dois: **HNSW** e **IVFFlat**. Para o v1 basta saber que o HNSW é o padrão atual (mais rápido nas buscas, um pouco mais lento para construir) e que ele existe para não varrer a tabela inteira a cada pergunta.

Mas aqui está a pegadinha que quase todo projeto encontra — e vale saber **antes** de bater nela:

**O índice vetorial é aproximado.** O "A" de HNSW é de *Approximate*. Para ganhar velocidade, ele pode não devolver o vizinho mais próximo exato — devolve algo quase sempre certo, com uma chance pequena de pular o melhor resultado.

Ou seja: **com índice, a busca fica rápida e ligeiramente imprecisa; sem índice, fica exata e lenta.** Para um acervo grande, troca-se de bom grado um pouquinho de precisão por muita velocidade. Saber que esse trade-off existe — e que a lentidão sem índice não é bug, é a busca exata trabalhando — é exatamente o tipo de coisa que separa quem leu tutorial de quem entendeu.

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

Repare em como cada coluna nasceu numa etapa diferente. `pagina` na 2, `indice` e `texto` na 3, `vetor` na 4. **A tabela é a fase de indexação inteira, materializada.** Cada decisão anterior deixou aqui a sua marca — e a citação, lá na Etapa 6, vai ler `texto` e `pagina` destas linhas.

O `texto` é guardado ao lado do vetor de propósito: na hora da resposta, você precisa do texto legível para mandar à LLM e para mostrar na citação. O vetor serve para achar; o texto, para usar.

## 4.10 Como testar

Aqui a testabilidade começa a mudar de natureza, e vale entender por quê.

O embedding **não é determinístico no sentido de que você não sabe prever os números** — não dá para escrever "o vetor de 'contrato' deve ser `[0.2, ...]`". Então some o tipo de teste que a ingestão e o chunking permitiam. O que se testa aqui são **propriedades e comportamentos**, não valores:

- O vetor gerado tem exatamente a dimensão da coluna (768) — pega erro de configuração
- O mesmo texto gera o mesmo vetor duas vezes — confirma determinismo do modelo
- Dois textos de sentido próximo ("cachorro" / "cão") produzem distância **menor** que dois distantes ("cachorro" / "planilha") — este é o teste que prova que o embedding *funciona*, e é lindo de ver passar
- Inserir e recuperar um vetor do Postgres devolve o mesmo vetor — valida o pgvector
- A query de distância devolve os chunks na ordem esperada num documento pequeno e controlado

Esse terceiro teste é o mais valioso do projeto até aqui: ele verifica, em código, a afirmação central de toda a etapa — *perto é parecido*. Se ele passa, o conceito não é fé; é fato medido.

## 4.11 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Embedding** | A representação de um texto como vetor de números fixos |
| **Modelo de embedding** | O modelo que converte texto em vetor. **Não** é a LLM que responde |
| **Vetor** | A lista de números. Uma posição num mapa de significados |
| **Espaço vetorial** | O "mapa" onde os textos são pontos e a distância mede diferença de sentido |
| **Dimensão** | Quantos números o vetor tem (384, 768, 1024...). Fixo por modelo |
| **Similaridade de cosseno** | Distância pelo ângulo entre vetores, ignorando o comprimento. Padrão em RAG |
| **pgvector** | Extensão que dá ao PostgreSQL o tipo vetor e os operadores de distância |
| **HNSW / IVFFlat** | Índices vetoriais. Trocam um pouco de precisão por muita velocidade |
| **Busca aproximada (ANN)** | *Approximate Nearest Neighbor* — acha vizinhos quase sempre certos, muito mais rápido |
| **Reindexar** | Gerar os vetores de novo. Necessário se o modelo ou o chunking mudarem |

---

## Próxima etapa

**Etapa 5 — Recuperação:** a pergunta entra, vira vetor, e a query de distância escolhe os trechos. Onde a fase de consulta finalmente começa — e onde os limites da busca semântica pura aparecem.

---

# Etapa 5 — Recuperação

## 5.1 A virada: começa a fase de consulta

As quatro etapas anteriores foram todas a mesma fase — indexação. Prepararam o documento e pararam. O banco tem um mapa de pontos, imóvel, esperando.

**Esta etapa é outra fase.** Aqui alguém pergunta.

A diferença não é decorativa. A indexação roda uma vez por documento, offline, sem pressa. A consulta roda a cada pergunta, com o usuário esperando a resposta na tela. O que antes podia levar um minuto agora precisa levar frações de segundo.

Guarde a fronteira, porque ela é o resumo de todo o RAG:

> **Indexação (Etapas 2–4):** prepara o documento. Uma vez. Sem pergunta.
> **Consulta (Etapas 5–6):** responde à pergunta. Toda vez. Sem tocar no documento.

A Etapa 5 é a primeira metade da consulta: pegar a pergunta e achar os trechos certos. A Etapa 6 é a segunda: transformar esses trechos em resposta.

## 5.2 O que esta etapa faz

**Entra:** a pergunta do usuário, em texto.
**Sai:** os poucos chunks mais relevantes para ela — o texto de cada um e a página.

Nada de LLM ainda. A recuperação não gera uma palavra. Ela **escolhe** — separa, de milhares de chunks, o punhado que importa. A geração é a Etapa 6.

Essa separação é deliberada e vale entendê-la: recuperar e gerar são problemas diferentes, com falhas diferentes. Misturá-los num passo só é o que impede de descobrir qual dos dois quebrou quando a resposta vem ruim — e, como a seção 5.8 mostra, quase sempre é a recuperação.

## 5.3 Os três passos

A recuperação inteira são três movimentos:

```
   pergunta em texto
          │
          ▼
   1. vira vetor          ← o mesmo cartógrafo da Etapa 4
          │
          ▼
   2. mede distância      ← a query pgvector: ORDER BY vetor <=> pergunta
          │
          ▼
   3. pega os top-k        ← LIMIT k
          │
          ▼
   os k chunks mais próximos
```

### Passo 1 — a pergunta vira ponto no mesmo mapa

A pergunta passa pelo **mesmo modelo de embedding** que vetorizou os chunks. Isso não é detalhe de implementação — é a condição para que a busca funcione.

Volta à imagem do mapa: os chunks foram posicionados pelo cartógrafo da Etapa 4. Se a pergunta for posicionada por um cartógrafo diferente, ela cai num mapa diferente, e medir distância entre os dois é comparar "rua tal em São Paulo" com "rua tal no Rio" — mesmo nome, cidades distintas. Vetores de modelos diferentes não são comparáveis.

Por isso o modelo de embedding é configuração fixa do projeto, e trocá-lo obriga a reindexar tudo. A regra da seção 4.5 reaparece aqui como a razão de a busca dar certo.

### Passo 2 — mede a distância

Agora, sim, as distâncias são calculadas — o que **não** aconteceu na Etapa 4. O ponto da pergunta contra cada ponto de chunk, pela query que a seção 4.7 já mostrou:

```sql
SELECT indice, pagina, texto
FROM chunks
WHERE documento_id = :doc
ORDER BY vetor <=> :vetor_da_pergunta
LIMIT :k;
```

O `<=>` é a distância de cosseno. O `ORDER BY` ordena do mais próximo ao mais distante. É literalmente a busca semântica — sem mistério, sem IA nesta linha, só geometria em SQL.

### Passo 3 — pega os top-k

O `LIMIT k` corta nos k primeiros. Esse **k** é a primeira decisão de verdade da etapa, e a próxima seção é só sobre ele.

## 5.4 O top-k: quantos trechos recuperar

k é quantos chunks você entrega para a Etapa 6 usar como contexto.

| k pequeno (ex.: 2) | k grande (ex.: 20) |
|---|---|
| Contexto enxuto e focado | Contexto amplo |
| Risco: deixar de fora o trecho que tinha a resposta | Risco: afogar a resposta em ruído |
| Barato em tokens na Etapa 6 | Caro, e reaparece o "perdido no meio" |
| Se a resposta exige juntar 3 trechos, falha | Cobre respostas espalhadas |

Os dois extremos falham, por motivos opostos. k pequeno **amputa** — a resposta estava no chunk que ficou de fora. k grande **dilui** — o trecho certo entrou, mas enterrado sob dez irrelevantes, e a LLM se perde (o mesmo "perdido no meio" que motivou o RAG a existir, reaparecendo em escala menor).

**Ponto de partida do v1: k entre 4 e 6.** É um chute educado, como o tamanho do chunk foi. E qual o k ideal? Depende do documento e do tipo de pergunta — o que significa que a resposta honesta é *medir*, e medir recuperação é exatamente o que os evals fazem. Outra vez o roadmap aparece como "o lugar onde esse número deixa de ser chute".

## 5.5 Distância não é relevância: o limiar

Um erro sutil: o `LIMIT k` **sempre** devolve k chunks. Sempre. Mesmo que a pergunta não tenha nada a ver com o documento.

Pergunte "qual a receita de lasanha?" a um contrato de aluguel. O banco não tem nada relevante — mas o `ORDER BY ... LIMIT 5` obedece e devolve os 5 chunks "menos distantes", que ainda assim estão longíssimos. Eles não respondem nada; são só os menos ruins de um monte ruim.

Se você repassar isso cru para a Etapa 6, a LLM recebe cinco trechos irrelevantes e é instruída a responder com base neles — a receita para uma alucinação confiante.

A defesa é um **limiar de distância** (threshold): descarte o chunk cuja distância passe de um teto. Se, depois do corte, não sobrar nenhum, a resposta honesta é *"não encontrei isso no documento"* — que é uma resposta **correta**, não uma falha. Um RAG que sabe dizer "não sei" vale mais que um que sempre inventa algo.

Calibrar esse teto tem o mesmo trade-off de tudo nesta área: apertado demais rejeita trecho bom, frouxo demais deixa passar lixo. Valor de partida no v1, e ajuste com evals. (O paralelo com o SecureFlow é exato: lá era falso positivo contra falso negativo na detecção de PII; aqui é rejeitar contexto bom contra aceitar contexto ruim. O mesmo botão, outro domínio.)

## 5.6 O que a busca semântica erra

A busca por significado é excelente com sentido e **fraca com literalidade**. Ela acha "distrato" quando você pergunta "rescisão" — e erra quando você precisa do exato.

Casos onde ela tropeça:

- **Códigos e identificadores** — "produto XPT-4471", "processo 0801234-56". O vetor de um código é quase vazio de significado; "XPT-4471" e "XPT-4472" parecem quase idênticos para o embedding, e são coisas diferentes.
- **Nomes próprios** — "contrato com a Silveira Advogados". Semanticamente, todo nome de escritório é parecido.
- **Números exatos** — "a cláusula 7.3", "o valor de R$ 4.500". O embedding capta "é um número de cláusula", não *qual*.
- **Termos raros e siglas internas** — jargão que aparece pouco no treino do modelo tem vetor mal posicionado.

O padrão: quando a resposta depende do **símbolo exato**, e não do sentido, a busca semântica escorrega. E, ironia, é justo aí que a busca burra por palavra-chave — que só casa caractere — acerta em cheio.

## 5.7 Por que não resolver isso agora: a busca híbrida

A correção tem nome: **busca híbrida** — rodar a busca semântica e a busca por palavra-chave em paralelo e fundir os resultados. A semântica cobre o sentido; a palavra-chave cobre o literal. Onde uma é cega, a outra enxerga.

E o PostgreSQL faz as duas: pgvector para a semântica, full-text search nativo (`tsvector`) para a palavra-chave. Nenhuma peça nova.

**Então por que fica no roadmap, e não no v1?** Por disciplina de escopo — a mesma que salvou este projeto lá atrás. A busca híbrida é uma *melhoria* da busca semântica: precisa que a busca simples exista, funcione e esteja testada antes de ter o que aprimorar. Construir as duas de uma vez, sem a primeira firme, é misturar duas fontes de bug e não saber qual delas falhou.

A ordem certa: busca simples funcionando no v1, com a limitação da 5.6 **declarada no README**. Busca híbrida como o primeiro item do v2 — o upgrade mais valioso e mais natural que o projeto tem. Declarar a limitação e apontar a solução no roadmap demonstra mais domínio do que esconder o problema com uma implementação apressada.

## 5.8 A verdade que ordena as prioridades

Guarde isto, porque é o que distingue quem já operou RAG de quem só montou um:

**A maioria esmagadora das respostas ruins de um RAG nasce na recuperação, não na geração.**

Se o trecho certo não entra no top-k, a Etapa 6 está condenada antes de começar — nenhuma LLM responde bem a partir do contexto errado; ela vai gerar algo plausível e incorreto. Quando a resposta vem ruim, o instinto é culpar o modelo e trocá-lo. Quase sempre o defeito está aqui: chunk mal cortado (Etapa 3), k mal escolhido, limiar mal calibrado, ou o caso literal da 5.6.

A consequência prática para o seu tempo: **quando algo falhar, olhe o que foi recuperado antes de mexer no prompt.** Imprima os top-k. Se o trecho certo não está lá, o problema é a recuperação, e mexer no prompt é perda de tempo. É o motivo de recuperação e geração serem etapas separadas — e o motivo de os evals medirem as duas isoladamente.

## 5.9 O contrato de saída

A Etapa 5 entrega à 6:

```python
[
    {"pagina": 3, "texto": "...", "distancia": 0.18},
    {"pagina": 7, "texto": "...", "distancia": 0.24},
]
```

A `distancia` viaja junto de propósito: alimenta o limiar da 5.5 e, na interface, permite mostrar ao usuário o quão forte foi cada correspondência. `pagina` e `texto` são o que a citação da Etapa 6 vai exibir — os mesmos campos que nasceram nas Etapas 2 e 3, atravessando o pipeline inteiro até a tela.

## 5.10 Como testar

A recuperação é mais testável do que parece, desde que você monte o cenário. Com um documento pequeno e conhecido indexado:

- Uma pergunta cuja resposta está claramente na página X → o chunk da página X vem no top-k
- Uma pergunta sobre assunto ausente do documento → o limiar zera o resultado (testa o "não sei")
- k = 3 devolve no máximo 3 chunks
- Os resultados vêm ordenados por distância crescente
- A pergunta com sinônimo ("rescisão" quando o texto diz "distrato") recupera o trecho certo — o teste que prova a busca semântica de ponta a ponta
- Uma pergunta por código exato ("XPT-4471") **falha** em recuperar — e tudo bem: documenta a limitação da 5.6 como teste, provando que você conhece a fronteira

Esse último é raro e valioso: um teste que **afirma uma limitação conhecida**. Ele não pega bug — ele prova que a fraqueza é entendida e esperada, não uma surpresa. É a diferença entre "não sabia" e "sei, e está no roadmap".

## 5.11 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Recuperação** (*retrieval*) | Achar, entre todos os chunks, os mais relevantes para a pergunta |
| **Fase de consulta** | O fluxo que roda a cada pergunta. Oposto da indexação, que roda uma vez |
| **top-k** | Os k chunks mais próximos que a busca devolve. k é você quem escolhe |
| **Limiar** (*threshold*) | Distância máxima aceita. Além dela, o chunk é descartado por irrelevância |
| **Busca semântica** | Busca por proximidade de significado (vetores). Forte no sentido, fraca no literal |
| **Busca por palavra-chave** | Busca por casamento de termos (`tsvector`). Forte no literal, cega ao sentido |
| **Busca híbrida** | As duas combinadas, com os rankings fundidos. Primeiro item do roadmap |
| **"Perdido no meio"** | A tendência da LLM de ignorar informação enterrada no meio de um contexto longo |

---

## Próxima etapa

**Etapa 6 — Geração:** os trechos recuperados viram resposta. O prompt que ancora o modelo no contexto, a instrução de admitir ignorância, e a citação que fecha o ciclo de confiança.

---

# Etapa 6 — Geração

## 6.1 Onde estamos

A pergunta chegou (Etapa 5), virou vetor, e a busca devolveu um punhado de chunks — texto e página de cada um, os que sobreviveram ao limiar. Agora esses trechos viram resposta.

Esta é a segunda metade da fase de consulta, e a última do pipeline. É também, enfim, a etapa em que a LLM aparece para fazer o que ela faz de melhor: escrever.

Vale reancorar a fronteira uma última vez, porque ela é a espinha do projeto:

> **Recuperação (Etapa 5):** acha os trechos. Não escreve.
> **Geração (Etapa 6):** escreve a resposta. Não busca.

A geração confia inteiramente no que a recuperação entregou. Ela não vai atrás de mais nada — trabalha só com os chunks que recebeu. É por isso que a Etapa 5 decide o teto de qualidade da resposta: **a geração não conserta uma recuperação ruim, ela só redige em cima do que veio.** A seção 5.8 dita, aqui é onde a consequência dela se realiza.

## 6.2 O que esta etapa faz

**Entra:** a pergunta do usuário e os chunks recuperados (texto + página).
**Sai:** uma resposta em texto, ancorada nesses chunks, com a indicação de onde cada parte saiu.

O "G" de RAG mora aqui — *Generation*. Mas é uma geração **presa à coleira**: o modelo não responde do que sabe, responde do que recebeu. Transformar uma LLM que sabe de tudo num modelo que só fala do documento é o trabalho central da etapa, e ele é feito com uma coisa só — o prompt.

## 6.3 O prompt é a lógica de negócio

Lembra que, lá na discussão das camadas, ficou dito que este projeto tem *pouca* lógica de negócio — e que a que existe mora no prompt? É aqui. Este é o ponto do projeto inteiro onde uma regra de negócio é escrita, literalmente, em português.

O prompt de RAG tem três partes, montadas a cada pergunta:

```
┌─────────────────────────────────────────────┐
│ INSTRUÇÃO                                   │
│ "Responda usando somente o contexto abaixo. │
│  Se a resposta não estiver nele, diga que   │
│  não encontrou. Indique a página."          │
├─────────────────────────────────────────────┤
│ CONTEXTO                                     │
│ [chunk 1 — pág. 3]  ...texto...              │
│ [chunk 2 — pág. 7]  ...texto...              │
│  (os top-k que a Etapa 5 entregou)          │
├─────────────────────────────────────────────┤
│ PERGUNTA                                     │
│ "qual é o prazo de rescisão?"               │
└─────────────────────────────────────────────┘
```

Instrução, contexto, pergunta. É este bloco inteiro que vai para a LLM — não a pergunta sozinha, nunca a pergunta sozinha. **A pergunta sem o contexto é só uma pergunta a um modelo que não conhece o seu documento; o RAG está exatamente em juntar os dois.** A palavra "Augmented" do nome é este momento: a pergunta *aumentada* com os trechos recuperados.

## 6.4 Grounding: prender o modelo ao contexto

A instrução do topo tem um nome técnico — **grounding** (ancoragem). É o que obriga a resposta a se sustentar no contexto, e não no que o modelo "acha que sabe".

Sem grounding, a LLM faz o que ela sempre faz: completa com o conhecimento geral dela. Aí some a razão do RAG existir. Se o modelo fosse responder do próprio treino, você não precisava de documento nenhum — e a resposta viria com a confiança de sempre, esteja certa ou não.

A instrução de grounding faz três exigências ao modelo:

1. **Use apenas o contexto.** Não complemente com conhecimento externo, mesmo que você "saiba" a resposta.
2. **Admita quando não está lá.** Se o contexto não contém a resposta, diga isso — não invente.
3. **Aponte a origem.** Indique de qual trecho ou página cada afirmação veio.

As três são regras de negócio. Nenhuma é código no sentido tradicional — são frases em português que definem o comportamento do produto. Trocar essas frases muda o que o sistema é, tanto quanto trocar uma função mudaria.

## 6.5 "Não sei" é uma resposta certa

Este é o ponto que separa um RAG confiável de um gerador de plausibilidades — e ele conecta direto com o limiar da Etapa 5.

Uma LLM, por padrão, **detesta dizer que não sabe.** Ela foi treinada para ser prestativa, e o caminho de menor resistência é sempre produzir *algo*. Peça o que não está no contexto e, sem instrução em contrário, ela preenche a lacuna com uma invenção fluente e convincente. Isso é alucinação, e num sistema que promete responder sobre documentos reais, é o pior defeito possível.

Dois freios trabalham juntos, um em cada etapa:

- **O limiar da Etapa 5** evita que lixo chegue como contexto. Se nada passou de perto, a Etapa 6 recebe contexto vazio.
- **O grounding da Etapa 6** instrui o modelo a dizer "não encontrei no documento" quando o contexto não contém a resposta — inclusive quando ele chega vazio.

Um RAG que responde *"isso não está no documento"* está **funcionando corretamente**. Parece um fracasso — o usuário não recebeu o que queria — mas é o oposto: é o sistema recusando-se a inventar. A alternativa, uma resposta bonita e falsa, é o único resultado verdadeiramente inaceitável, porque o usuário não tem como distinguir a mentira sem ir conferir no documento — e se ele vai conferir de qualquer jeito, o RAG não serviu para nada.

Vale escrever isso no README como característica, não como limitação: *o sistema admite quando não sabe.* É um argumento de confiança.

## 6.6 A citação fecha o ciclo

A citação — mostrar o trecho e a página que fundamentaram a resposta — foi decidida como parte do v1 lá na Etapa 1, e não como enfeite. Agora dá para ver por quê.

A resposta de uma LLM sempre parece confiante. O texto tem a mesma cara segura quando está certo e quando alucina. **A citação é o que devolve ao usuário o poder de verificar.** Com o trecho e a página na tela, ele confere em dois segundos se a resposta bate com a fonte. Sem isso, ele teria que reler o documento inteiro — e aí o RAG não economizou nada.

E repare no caminho que a página percorreu para chegar aqui:

> extraída na **Etapa 2** (PyMuPDF, página a página) → preservada no chunk na **Etapa 3** (o chunk não atravessa página, justamente para isto) → gravada na coluna `pagina` na **Etapa 4** → carregada pela busca na **Etapa 5** → exibida na citação na **Etapa 6**.

Cinco etapas atrás, decidir extrair "página por página" parecia um detalhe técnico da ingestão. Era, na verdade, a primeira metade desta citação. **É por isso que a decisão da Etapa 2 e a feature da Etapa 6 são a mesma coisa, tomada em dois momentos** — algo que a Etapa 2 já prenunciava e que só agora se completa.

Como conseguir a citação, na prática: peça no prompt que o modelo referencie a página de cada afirmação, já que cada chunk entra no contexto rotulado com a sua (`[pág. 3]`). No v1 basta isso, mais exibir na interface os chunks que a Etapa 5 recuperou, ao lado da resposta. O usuário lê a resposta e vê, do lado, os trechos originais com a página. Ciclo de confiança fechado.

## 6.7 A LLM: local ou API

Como no embedding, duas rotas — e a decisão é independente da que você tomou lá, porque são dois modelos diferentes (o de embedding vetoriza, este redige).

| | Via API (OpenAI, Anthropic, etc.) | Local (Llama, Mistral, etc.) |
|---|---|---|
| Qualidade da redação | Alta, consistente | Boa, variável conforme o modelo e a máquina |
| Custo | Por uso | Grátis após baixar |
| Privacidade | O contexto sai da máquina | Nada sai |
| Setup | Uma chave de API | Pesado: precisa de máquina com folga |

**Decisão do v1: uma abstração fina que permita os dois, começando pela API.** A geração exige mais do modelo do que o embedding, e um modelo local de qualidade pede hardware que nem todo mundo tem. Começar pela API tira o gargalo de máquina do caminho e deixa você focar no que a etapa ensina — o prompt.

Mas isole a chamada atrás de uma função só (`gerar(prompt) -> texto`), sem espalhar o cliente da API pelo código. Assim, trocar para um modelo local depois — ou trocar de provedor — mexe em um arquivo, não em dez. Essa é a mesma ideia de "borda vs. núcleo" da discussão de camadas: o provedor de LLM é borda, substituível; o pipeline de RAG é núcleo, e não deveria nem saber qual modelo respondeu.

*(Nota de privacidade, ponte com o outro projeto do portfólio: usar API significa que o contexto — trechos do documento — sai da sua máquina para um terceiro. Se o documento tiver dado pessoal, isso é exatamente o problema que o SecureFlow resolve, anonimizando antes do envio. É a integração possível que ficou no roadmap dos dois — mencionada aqui porque a Etapa 6 é o ponto exato onde ela se encaixaria.)*

## 6.8 Streaming: por que fica no roadmap

Você já viu o ChatGPT "digitar" a resposta palavra por palavra. Isso é **streaming** — a resposta aparece token a token conforme é gerada, em vez de surgir pronta depois de uma espera.

É uma melhoria de *experiência*, não de arquitetura. A resposta é idêntica; só a forma de entregar muda. Como não ensina nada sobre RAG e adiciona complexidade (SSE, streaming no frontend), fica no roadmap. O v1 espera a resposta ficar pronta e a mostra de uma vez. Funciona; só é menos vistoso.

## 6.9 O que pode dar errado aqui

Vale separar as falhas que nascem *nesta* etapa das que só *aparecem* nela mas vêm de trás:

| Sintoma | Origem real | Onde corrigir |
|---|---|---|
| Resposta inventa fato que não está no doc | Grounding fraco no prompt | Etapa 6 — reforçar a instrução |
| Resposta ignora um trecho que tinha a informação | O trecho não foi recuperado | **Etapa 5** — não é aqui |
| Modelo responde do conhecimento geral dele | Falta instrução de usar só o contexto | Etapa 6 — grounding |
| Resposta certa, mas sem citar página | Prompt não pediu a origem | Etapa 6 — pedir referência |
| "Não sei" para algo que estava no documento | Recuperação falhou, ou limiar apertado demais | **Etapa 5** — não é aqui |

Metade dos sintomas que *parecem* da geração são, na verdade, da recuperação — exatamente o que a seção 5.8 avisou. **Antes de reescrever o prompt pela décima vez, imprima o contexto que chegou.** Se o trecho certo não está nele, nenhum prompt salva. Este é o hábito de depuração mais valioso do projeto inteiro, e é a razão de recuperação e geração serem etapas separadas.

## 6.10 Como testar

Aqui a testabilidade chega ao seu ponto mais escorregadio, e é honesto admitir por quê: **a saída da LLM não é determinística.** A mesma pergunta pode gerar redações diferentes. Some qualquer teste do tipo "a resposta é exatamente esta string".

O que ainda dá para testar de forma confiável são os **arredores** da geração, que são determinísticos:

- O prompt é montado com as três partes na ordem certa (instrução, contexto, pergunta) — testável, é construção de string
- Todos os chunks recuperados entram no contexto, cada um com a sua página — testável
- Contexto vazio (nada passou do limiar) produz um prompt que instrui o "não sei" — testável
- A função de LLM é chamada uma vez, com o prompt montado — testável com um dublê no lugar da API real

E o comportamento do modelo em si — grounding, "não sei", fidelidade ao contexto — testa-se com um **conjunto de perguntas de avaliação**: perguntas cuja resposta você conhece, rodadas contra um documento conhecido, conferindo se a resposta bate e se o "não sei" dispara quando deve. Isso tem nome, e é o roadmap reaparecendo pela última vez: **evals**. No v1, um punhado dessas perguntas conferidas à mão já basta; a suíte formal de evals é o item do v2 que transforma "parece que melhorou" em "melhorou, medido".

Repare no arco que se fechou: começamos na Etapa 2 com testes 100% determinísticos (mesma entrada, mesma saída), e terminamos aqui, onde o núcleo só se avalia por amostragem. Não é o projeto ficando desleixado — é a natureza do que se testa mudando, de código para comportamento. Saber *o que* dá para garantir com teste e o que só dá para *medir por evals* é, em si, entendimento de engenharia de IA.

## 6.11 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Geração** (*generation*) | A LLM produzindo a resposta a partir do contexto recuperado |
| **Grounding** (ancoragem) | Prender a resposta ao contexto fornecido, proibindo conhecimento externo |
| **Prompt** | O bloco instrução + contexto + pergunta enviado à LLM a cada consulta |
| **Alucinação** | Resposta fluente e confiante que não se sustenta no contexto (ou é falsa) |
| **Citação** | Exibir o trecho e a página que fundamentaram a resposta. O mecanismo de verificação |
| **Streaming / SSE** | Entregar a resposta token a token, em tempo real. Melhoria de experiência, no roadmap |
| **Evals** | Conjunto de perguntas de avaliação que medem a qualidade das respostas de forma reproduzível |
| **Dublê de teste** (*mock*) | Substituto da API real nos testes, para não depender de rede nem gastar chamadas |

---

## O pipeline está completo

Com a Etapa 6, o núcleo fecha de ponta a ponta:

> PDF entra → texto extraído (2) → picotado em chunks (3) → vetorizado e gravado (4) → **pergunta chega** → recuperados os trechos certos (5) → resposta ancorada, com citação (6).

Falta a **Etapa 7 — Entrega:** juntar essas seis peças numa API coerente, dar uma interface, escrever os testes de ponta a ponta, empacotar em Docker e fechar o README. Não há conceito novo de RAG aqui — é a etapa que transforma seis peças que funcionam num projeto que se apresenta.

---

# Etapa 7 — Entrega

## 7.1 O que muda de mentalidade aqui

As seis etapas anteriores responderam "como o RAG funciona?". Esta responde outra pergunta: **"como alguém que não é você usa e avalia isto?"**

Isso inclui o usuário que sobe um PDF, mas inclui principalmente **o recrutador que abre o repositório**. Num projeto de portfólio, esse é o usuário mais importante — e ele decide em dois minutos se vale continuar lendo. A Etapa 7 é, em boa parte, engenharia para esses dois minutos.

Não há conceito novo de RAG. Há o trabalho que separa "funciona na minha máquina" de "funciona, e qualquer um consegue ver funcionando".

## 7.2 A API: juntar as peças numa superfície

Até aqui, cada etapa é uma função. A API é o que as expõe ao mundo. Duas rotas sustentam o núcleo do v1:

| Método | Rota | O que faz | Etapas que aciona |
|---|---|---|---|
| `POST` | `/documentos` | Recebe o PDF, roda a indexação, responde quando está pronto | 2, 3, 4 |
| `POST` | `/perguntas` | Recebe a pergunta, roda a consulta, devolve resposta + citações | 5, 6 |

Repare que as rotas são o corte entre as duas fases, agora visível de fora: `/documentos` é a fase de indexação inteira atrás de um endpoint; `/perguntas` é a fase de consulta inteira atrás de outro. A fronteira que escorregou tantas vezes na leitura virou, no fim, a divisão mais natural da API.

Ao redor delas, as rotas de conta:

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/auth/registrar` | Cria a conta e adota os documentos da sessão anônima |
| `POST` | `/auth/login` | Autentica e adota os documentos da sessão anônima |
| `GET` | `/documentos` | Lista os documentos do usuário (ou da sessão anônima) |
| `DELETE` | `/documentos/{id}` | Remove o documento e os dados dele derivados |

**A regra de acesso que atravessa todas elas:** `/documentos` e `/perguntas` aceitam tanto um usuário autenticado quanto uma sessão anônima — **exceto `POST /perguntas`, que exige conta.** É essa exigência, e só ela, que dispara a tela de login no frontend. O servidor responde `401` e o cliente abre o cadastro; nenhuma outra rota faz isso.

Complementos úteis, sem exagero:

- `GET /health` — responde "estou de pé". Trivial, e é o primeiro sinal de profissionalismo que um avaliador procura.
- `GET /documentos/{id}` — estado do documento (indexando / pronto / falhou), que a próxima seção justifica.

O `main.py` continua fino: recebe, valida com Pydantic, delega para a função da etapa certa, devolve. Nenhuma lógica de RAG mora na camada de rota — ela só traduz HTTP em chamada de função e volta. Isso é a fronteira borda/núcleo, agora no topo da pilha.

## 7.3 A adoção da sessão anônima

O cadastro adiado (seção 1.5) concentra sua dificuldade num único momento: **o instante em que a conta nasce.**

Antes dele, o documento pertence a uma sessão anônima, identificada por um token de sessão que o cliente guarda. Depois dele, precisa pertencer ao usuário. A operação que faz essa passagem:

```
POST /auth/registrar
  ├── cria o usuário
  ├── lê o token de sessão anônima da requisição
  ├── transfere os documentos daquela sessão para o novo usuário
  └── devolve o token de autenticação
```

Três cuidados que a implementação exige:

**A transferência e a criação da conta são uma coisa só.** Se a conta for criada e a transferência falhar, o usuário fica cadastrado e sem o documento — o pior resultado possível, porque ele pagou o custo do cadastro e perdeu o trabalho. As duas operações vivem na mesma transação.

**Login também adota.** Não é só o cadastro. Se o usuário já tinha conta, subiu um documento sem perceber que estava deslogado e então faz login, o documento precisa ir para a conta dele igualmente.

**A sessão anônima só entrega o que é dela.** A transferência move os documentos daquele token de sessão, e de nenhum outro. Um token forjado não deve conseguir puxar documento alheio — é a mesma disciplina de isolamento que vale para o resto do sistema.

## 7.4 A indexação demora: a decisão do síncrono

Aqui aparece o primeiro problema real que só a entrega revela.

Indexar um PDF de 300 páginas — extrair, picotar, gerar centenas de embeddings — leva segundos, às vezes minutos. Se `POST /documentos` fizer tudo isso antes de responder, a requisição fica pendurada o tempo todo, e um PDF grande estoura o tempo limite do navegador.

A solução completa é processar em segundo plano: a rota responde na hora com "recebido, estou processando", e o trabalho pesado roda numa fila. É o padrão de produção — e é exatamente a arquitetura do **projeto de monitoramento de preços** que foi cogitado lá no começo (fila de tarefas, Celery/ARQ, Redis).

**Decisão do v1: processamento síncrono, com limite de tamanho honesto.** A rota indexa e só então responde; o teto de 20 MB da Etapa 2 mantém o tempo dentro do aceitável. A fila fica no roadmap.

O motivo é disciplina de escopo, a mesma do projeto todo: fila assíncrona é uma peça de infraestrutura inteira (broker, worker, monitoramento de job) que não ensina nada sobre RAG e adiciona muita superfície. Fazê-la aqui inflaria o escopo de novo — o erro que quase afundou o projeto no início. **Declarar no README "indexação síncrona no v1; fila assíncrona no roadmap" demonstra que você conhece o padrão de produção e escolheu não implementá-lo agora** — o que vale mais do que uma fila mal feita.

## 7.5 A interface: só o que prova o produto

A interface do v1 tem uma responsabilidade única: **deixar a demo acontecer em dez segundos**. Nada além disso.

O mínimo que prova tudo:

- uma área para subir o PDF
- um campo de pergunta
- a resposta
- **as citações ao lado da resposta — o trecho e a página**
- as telas de **cadastro e login**, que aparecem na primeira pergunta

A citação não é opcional na interface, pelo motivo da Etapa 6: é ela que transforma "a IA afirmou algo" em "a IA afirmou, e aqui está a prova, confira você mesmo". Uma demo de RAG sem citação visível parece um chatbot qualquer; com citação, parece a ferramenta que é. Se houver um único capricho de frontend, é este.

**Sobre o momento do cadastro.** O usuário sobe o PDF, vê o documento ser processado, digita a pergunta — e só então a tela aparece. Duas coisas fazem essa transição funcionar em vez de irritar:

- **Explicar o porquê ali mesmo.** Uma linha basta: "crie uma conta para salvar este documento e suas perguntas". O cadastro deixa de parecer pedágio e passa a parecer preservação do que ele já fez.
- **Não perder a pergunta digitada.** Depois de autenticar, a pergunta que ele já havia escrito deve ser enviada automaticamente. Fazê-lo redigitar desfaz o benefício inteiro do padrão.

O que **não** entra: histórico de conversas, gerenciamento de coleções de documentos, recuperação de senha, tema escuro. Tudo isso é polimento que não demonstra o núcleo. A interface serve ao produto, não o contrário.

## 7.6 Testes de ponta a ponta

Cada etapa já tem seus testes. Falta o teste que atravessa o pipeline inteiro — o que dá confiança de que as peças, juntas, funcionam:

**Suba um PDF conhecido, faça uma pergunta cuja resposta você sabe, verifique que a resposta bate e que a citação aponta a página certa.**

Esse teste é o que, sozinho, prova que o projeto funciona. Ele é mais lento (roda tudo) e, por incluir a LLM, tem o componente não-determinístico da Etapa 6 — então verifique propriedades, não a string exata: que a resposta menciona o fato esperado, que veio citação, que a página é a correta. A recuperação e a montagem do prompt, essas, são determinísticas e você verifica com precisão.

Um segundo teste de ponta a ponta fecha o par, e é o que mais impressiona: **pergunte algo que não está no documento e verifique que o sistema diz que não sabe.** Ele prova, de fora, que os dois freios da Etapa 5 e 6 — limiar e grounding — trabalham juntos. É o teste que demonstra que o RAG é honesto, e honestidade é o argumento de confiança do produto.

E um terceiro, que a decisão do cadastro adiado torna obrigatório: **suba um documento sem estar logado, cadastre-se, e confirme que o documento continua acessível na conta nova.** É o teste da seção 7.3, e ele protege contra a falha mais custosa do padrão — o usuário se cadastrar e descobrir que perdeu o upload. Vale um par: o mesmo cenário terminando em login, em vez de cadastro.

## 7.7 Docker: o que faz "clona e roda"

Este é o passo isolado de maior retorno da Etapa 7, e talvez do projeto.

Um projeto que exige instalar Python na versão certa, subir um PostgreSQL, instalar a extensão pgvector, baixar o modelo, configurar variáveis e rezar — a maioria dos avaliadores desiste antes de ver rodar. Um projeto onde `docker compose up` levanta tudo é um projeto que **funciona na frente de quem importa.**

O `docker-compose.yml` do v1 sobe dois serviços:

- **a aplicação** (FastAPI + o código das sete etapas)
- **o PostgreSQL com pgvector já incluído** — usando a imagem `pgvector/pgvector`, não a `postgres` pura, pela armadilha da Etapa 4

Com isso, a distância entre "vi o repositório" e "estou conversando com um PDF na minha máquina" vira um comando. Num portfólio, essa distância é a diferença entre ser avaliado e ser ignorado.

O que vai no `.env.example` (nunca no `.env` versionado, pela Etapa 2): a string do banco, a chave da API de LLM, o nome do modelo de embedding. Um README que diz "copie `.env.example` para `.env`, ponha sua chave, rode `docker compose up`" é um README que respeita o tempo de quem lê.

## 7.8 O README: o verdadeiro ponto de entrada

Dito sem rodeio: **mais gente vai ler seu README do que rodar seu código.** Ele não é documentação acessória — é a interface primária do projeto para o mercado.

O que um bom README de portfólio tem, em ordem:

1. **Uma frase que diz o que é** — "converse com um PDF; respostas com a fonte e a página". Sem jargão.
2. **Um GIF ou print da demo** — a coisa funcionando, antes de qualquer texto. É o que segura o leitor.
3. **Como rodar** — os três comandos do Docker. Se exigir mais que isso, encurte.
4. **As decisões de arquitetura, com o porquê** — pgvector em vez de Pinecone, sem LangChain, busca simples antes da híbrida. **Esta é a seção que um avaliador técnico lê,** e é onde todo o entendimento que você construiu nas seis etapas vira evidência. As decisões que você sabe defender aqui são as mesmas que você vai defender na entrevista.
5. **Limitações conhecidas e roadmap** — declarar o que não faz e o que viria depois. Sinal de maturidade, não de fraqueza.

A documentação por etapas (este documento) vive ao lado, em `docs/`, para quem quiser o mergulho fundo. O README é a porta; a documentação é a casa.

## 7.9 O arco fechado

Vale olhar para trás uma vez, porque o projeto conta uma história coerente quando visto inteiro:

| Etapa | O que ficou | Onde reaparece |
|---|---|---|
| 1 | O escopo enxuto que salvou o projeto | Todo "fica no roadmap" veio daqui |
| 2 | Extrair página por página | Virou a citação da Etapa 6 |
| 3 | O chunk como unidade tripla | Definiu busca, contexto e citação |
| 4 | O mapa de significados | A busca inteira é distância nesse mapa |
| 5 | Recuperar não é gerar; o limiar | O teto de qualidade da resposta |
| 6 | Gerar preso ao contexto; "não sei" | A confiança do produto |
| 7 | Empacotar, e o cadastro no momento certo | O que torna tudo acima visível e retomável |

Cada decisão de escopo — o que ficou de fora — não foi corte por incapacidade, foi corte por foco. E o roadmap que se acumulou (busca híbrida, reranking, evals, fila assíncrona, DOCX, streaming, OCR, compartilhamento entre usuários, anonimização via SecureFlow) não é uma lista de dívidas: é a prova de que você conhece o caminho de produção inteiro e escolheu, conscientemente, onde parar a v1.

**Essa é a diferença entre um projeto de estudante e um projeto de engenheiro:** não é fazer tudo. É saber o que fazer primeiro, fazer isso completo, e conseguir explicar cada coisa que ficou para depois.

## 7.10 Glossário desta etapa

| Termo | O que é |
|---|---|
| **Endpoint** | Uma rota da API — um endereço que aceita requisições (ex.: `POST /perguntas`) |
| **Síncrono** | A rota faz todo o trabalho antes de responder. Simples, mas prende a requisição |
| **Assíncrono / fila** | O trabalho pesado roda em segundo plano; a rota responde na hora. Roadmap |
| **Health check** | Rota que confirma que o serviço está no ar |
| **Teste de ponta a ponta** (E2E) | Teste que exercita o pipeline inteiro, do upload à resposta |
| **docker-compose** | Arquivo que sobe vários serviços (app + banco) com um comando |
| **README** | O documento de entrada do repositório. A interface do projeto para quem avalia |
| **Cadastro adiado** | Exigir a conta só no momento em que o usuário já viu valor — aqui, a primeira pergunta |
| **Sessão anônima** | Identificação temporária que dá dono ao documento antes de existir conta |
| **Adoção** | Transferir os documentos da sessão anônima para o usuário no cadastro ou login |

---

## Fim da documentação do v1

As sete etapas estão escritas. O pipeline foi construído. O que existe ao final:

> **Lastro** — um serviço que recebe um PDF, permite perguntar sobre ele em linguagem natural, e responde com base no conteúdo — citando o trecho e a página — ou admite quando a resposta não está lá. O cadastro é exigido apenas na primeira pergunta, e preserva o documento já enviado. Empacotado em Docker, testado de ponta a ponta, documentado decisão por decisão.

O roadmap — busca híbrida, reranking, evals, fila assíncrona, DOCX, streaming, OCR, compartilhamento entre usuários e a anonimização via SecureFlow — fica declarado no README como o caminho da v2 em diante. Não como dívida: como mapa.
