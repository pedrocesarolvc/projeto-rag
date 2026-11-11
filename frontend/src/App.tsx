import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  acrescentarDocumento,
  apagarConversa,
  criarConversa,
  enviarDocumento,
  limparToken,
  listarConversas,
  obterConversa,
  obterToken,
  perguntar,
  removerDocumento,
  ErroAutenticacao,
  type Citacao,
  type ConversaResumo,
  type Documento,
  type Mensagem,
} from "./api";
import Auth from "./Auth";
import "./App.css";

// Cada assunto vive numa conversa, e cada conversa é uma lombada na
// estante: o nome dos PDFs enviados é o título do livro. O fluxo dentro
// de uma conversa é o de sempre — enviar até 2 PDFs, perguntar (conta
// exigida só aqui, cadastro adiado, seção 1.5), ler a resposta com as
// fontes — e agora o histórico fica guardado no servidor: ao voltar, a
// estante e as conversas estão onde foram deixadas.
//
// Uma conversa só passa a existir no servidor na primeira pergunta,
// porque ela exige login. Até lá é um rascunho local (`servidorId`
// nulo) com os PDFs já enviados.
//
// Cada pergunta continua independente das anteriores: o histórico é só
// para o usuário reler, o Lastro não "lembra" da conversa ao responder.
// De propósito — o prompt é onde mora o grounding, e fazer o modelo
// carregar a conversa mudaria justamente isso.

// Até 2 PDFs por pergunta: a resposta junta o que vier dos dois, e a
// caixa de seleção de cada um permite separá-los quando preciso. O teto
// espelha o do servidor — o servidor é quem de fato impõe; aqui ele só
// evita oferecer o que seria recusado.
const MAX_DOCUMENTOS = 2;

// A cor e a altura da lombada saem da identidade da conversa, não da
// posição na estante: assim um livro não muda de aspecto quando outro é
// removido.
const CORES_LOMBADA = ["#4a3324", "#2e4a5f", "#5a3e2b", "#2f4f46", "#6b4a33", "#3b3f5c"];
const ALTURAS_LOMBADA = [190, 172, 182, 166, 178, 170];

// Rascunhos locais usam 1, 2, 3…; as conversas do servidor usam
// DESLOCAMENTO_SERVIDOR + id, para as duas numerações nunca se cruzarem.
const DESLOCAMENTO_SERVIDOR = 1_000_000;

interface Conversa {
  chave: number;
  servidorId: number | null;
  documentos: Documento[];
  // Quais documentos entram na próxima pergunta. Todo upload novo já
  // nasce marcado — o caso comum é querer perguntar sobre tudo.
  selecionados: number[];
  pergunta: string;
  // null = conversa do servidor cujas mensagens ainda não foram buscadas.
  mensagens: Mensagem[] | null;
}

function novaConversa(chave: number): Conversa {
  return { chave, servidorId: null, documentos: [], selecionados: [], pergunta: "", mensagens: [] };
}

function daServidor(resumo: ConversaResumo): Conversa {
  return {
    chave: DESLOCAMENTO_SERVIDOR + resumo.id,
    servidorId: resumo.id,
    documentos: resumo.documentos,
    selecionados: resumo.documentos.filter((doc) => doc.status === "pronto").map((doc) => doc.id),
    pergunta: "",
    mensagens: null,
  };
}

// A LLM costuma responder com **negrito** e *itálico* em Markdown. Em
// vez de mostrar os asteriscos, converte só esses dois casos em
// <strong> e <em> — sem biblioteca de Markdown e sem
// dangerouslySetInnerHTML: o texto vem de um modelo que leu um PDF de
// terceiros, então nunca deve virar HTML.
function comEnfase(texto: string): ReactNode[] {
  return texto.split(/(\*\*.+?\*\*|\*[^*\n]+?\*)/g).map((parte, i) => {
    if (parte.length > 4 && parte.startsWith("**") && parte.endsWith("**")) {
      return <strong key={i}>{parte.slice(2, -2)}</strong>;
    }
    if (parte.length > 2 && parte.startsWith("*") && parte.endsWith("*")) {
      return <em key={i}>{parte.slice(1, -1)}</em>;
    }
    return parte;
  });
}

function semExtensao(nome: string): string {
  return nome.replace(/\.pdf$/i, "");
}

// Uma linha por documento: na lombada cada nome ganha a sua própria
// coluna, em vez de dois nomes disputando a mesma linha curta.
function linhasDaLombada(conversa: Conversa): string[] {
  if (conversa.documentos.length === 0) return ["Nova"];
  return conversa.documentos.map((doc) => semExtensao(doc.nome_original));
}

// O título completo, para leitor de tela e dica ao passar o mouse.
function tituloDaConversa(conversa: Conversa): string {
  if (conversa.documentos.length === 0) return "Nova conversa";
  return conversa.documentos.map((doc) => semExtensao(doc.nome_original)).join(" e ");
}

function RespostaCard({ texto, citacoes }: { texto: string; citacoes: Citacao[] }) {
  return (
    <section className="cartao resposta">
      <p className="selo-seguro">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
          <rect x="4" y="11" width="16" height="10" rx="2" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </svg>
        Fundamentada nos documentos
      </p>
      <p className="texto-resposta">{comEnfase(texto)}</p>

      {citacoes.length > 0 && (
        <div className="citacoes">
          <h2>Fontes</h2>
          {citacoes.map((citacao, indice) => (
            <blockquote key={indice} className="citacao">
              <p>{citacao.texto}</p>
              <footer>
                {citacao.documento} · página {citacao.pagina}
              </footer>
            </blockquote>
          ))}
        </div>
      )}
    </section>
  );
}

function App() {
  const [conversas, setConversas] = useState<Conversa[]>([novaConversa(1)]);
  const [ativaChave, setAtivaChave] = useState(1);
  const proximaChave = useRef(2);
  const fimDaConversa = useRef<HTMLDivElement>(null);

  const [logado, setLogado] = useState(() => obterToken() !== null);
  const [enviando, setEnviando] = useState(false);
  const [perguntando, setPerguntando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  // Cadastro adiado (seção 1.5): só vira true quando POST /perguntas
  // devolve 401 — nenhuma outra rota dispara isso (seção 7.2).
  const [precisaAutenticar, setPrecisaAutenticar] = useState(false);

  const ativa = conversas.find((c) => c.chave === ativaChave) ?? conversas[0];
  // Trocar de conversa no meio de um envio faria a resposta cair no
  // lugar errado; enquanto algo está em andamento, a estante espera.
  const ocupado = enviando || perguntando;

  // Só documentos prontos e marcados entram na pergunta: um que ainda
  // está "indexando" ou "falhou" não tem chunks para buscar.
  const idsParaPerguntar = ativa.documentos
    .filter((doc) => doc.status === "pronto" && ativa.selecionados.includes(doc.id))
    .map((doc) => doc.id);

  function atualizarConversa(chave: number, mudar: (conversa: Conversa) => Conversa) {
    setConversas((atuais) => atuais.map((c) => (c.chave === chave ? mudar(c) : c)));
  }

  // As conversas guardadas no servidor entram na estante, antes dos
  // rascunhos locais. Quem já está na estante não é duplicado.
  async function carregarConversas() {
    try {
      const lista = await listarConversas();
      setConversas((atuais) => {
        const jaTem = new Set(atuais.map((c) => c.servidorId));
        const novas = lista.filter((r) => !jaTem.has(r.id)).map(daServidor);
        return [...novas, ...atuais];
      });
    } catch (e) {
      // 401 aqui só quer dizer "token vencido": segue como quem ainda
      // não tem conta, sem abrir a tela de cadastro (ela é da pergunta).
      if (e instanceof ErroAutenticacao) {
        limparToken();
        setLogado(false);
      }
    }
  }

  useEffect(() => {
    if (obterToken() !== null) carregarConversas();
    // só na carga da página
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Ao abrir uma conversa nova ou ao chegar uma resposta, desce até o fim.
  useEffect(() => {
    fimDaConversa.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [ativa.chave, ativa.mensagens?.length]);

  async function carregarMensagens(chave: number, servidorId: number) {
    try {
      const detalhe = await obterConversa(servidorId);
      atualizarConversa(chave, (c) => ({
        ...c,
        documentos: detalhe.documentos,
        mensagens: detalhe.mensagens,
      }));
    } catch (e) {
      atualizarConversa(chave, (c) => ({ ...c, mensagens: [] }));
      setErro(e instanceof Error ? e.message : "Falha ao abrir a conversa.");
    }
  }

  function selecionarConversa(chave: number) {
    setAtivaChave(chave);
    setErro(null);
    setPrecisaAutenticar(false);
    const alvo = conversas.find((c) => c.chave === chave);
    if (alvo && alvo.servidorId !== null && alvo.mensagens === null) {
      carregarMensagens(alvo.chave, alvo.servidorId);
    }
  }

  function handleNovaConversa() {
    const chave = proximaChave.current++;
    setConversas((atuais) => [...atuais, novaConversa(chave)]);
    selecionarConversa(chave);
  }

  async function handleArquivo(evento: ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0];
    // Limpa o input para que escolher de novo o mesmo arquivo (depois de
    // removê-lo, por exemplo) volte a disparar o evento de mudança.
    evento.target.value = "";
    if (!arquivo) return;

    const conversa = ativa;
    setEnviando(true);
    setErro(null);
    try {
      const doc = await enviarDocumento(arquivo);
      let documentos = [...conversa.documentos, doc];

      // Numa conversa que já existe no servidor, o PDF novo precisa ser
      // ligado a ela ali também — é o "ampliar o conhecimento". Se a
      // ligação falhar, o PDF recém-enviado não fica solto no servidor.
      if (conversa.servidorId !== null) {
        try {
          documentos = (await acrescentarDocumento(conversa.servidorId, doc.id)).documentos;
        } catch (e) {
          await removerDocumento(doc.id).catch(() => undefined);
          throw e;
        }
      }

      atualizarConversa(conversa.chave, (c) => ({
        ...c,
        documentos,
        selecionados: [...c.selecionados, doc.id],
      }));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao enviar o documento.");
    } finally {
      setEnviando(false);
    }
  }

  function alternarSelecao(docId: number) {
    atualizarConversa(ativa.chave, (c) => ({
      ...c,
      selecionados: c.selecionados.includes(docId)
        ? c.selecionados.filter((outro) => outro !== docId)
        : [...c.selecionados, docId],
    }));
  }

  // Tira a conversa da estante. Se era a última, nasce um rascunho vazio
  // no lugar: a tela nunca fica sem uma conversa onde enviar PDFs.
  function tirarDaEstante(chave: number) {
    const outras = conversas.filter((c) => c.chave !== chave);
    if (outras.length === 0) {
      const nova = novaConversa(proximaChave.current++);
      setConversas([nova]);
      setAtivaChave(nova.chave);
      return;
    }
    setConversas(outras);
    selecionarConversa(outras[outras.length - 1].chave);
  }

  // Com o teto de 2, sem remover não haveria como trocar um PDF por
  // outro dentro da mesma conversa.
  async function handleRemover(docId: number) {
    setErro(null);
    try {
      await removerDocumento(docId);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao remover o documento.");
      return;
    }

    const restantes = ativa.documentos.filter((doc) => doc.id !== docId);
    if (restantes.length === 0) {
      // Livro sem nenhum documento não tem título: o servidor também o apagou.
      tirarDaEstante(ativa.chave);
      return;
    }
    atualizarConversa(ativa.chave, (c) => ({
      ...c,
      documentos: restantes,
      selecionados: c.selecionados.filter((outro) => outro !== docId),
    }));
  }

  async function handleApagarConversa() {
    if (!window.confirm("Apagar esta conversa e os documentos dela? Isso não pode ser desfeito.")) return;

    setErro(null);
    try {
      if (ativa.servidorId !== null) {
        await apagarConversa(ativa.servidorId);
      } else {
        // um rascunho não existe no servidor, mas os PDFs dele existem
        for (const doc of ativa.documentos) await removerDocumento(doc.id);
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao apagar a conversa.");
      return;
    }
    tirarDaEstante(ativa.chave);
  }

  // Separada de handlePergunta para poder ser chamada de novo, sozinha,
  // depois que o usuário autentica — sem ele precisar redigitar nada
  // (seção 7.5: "não perder a pergunta digitada").
  async function enviarPergunta(texto: string) {
    if (idsParaPerguntar.length === 0 || !texto.trim()) return;

    const conversa = ativa;
    setPerguntando(true);
    setErro(null);
    try {
      // A primeira pergunta de um rascunho é o que o transforma em
      // conversa de verdade. Ela nasce com TODOS os PDFs, marcados ou
      // não: um PDF desmarcado agora também pertence ao livro.
      let servidorId = conversa.servidorId;
      if (servidorId === null) {
        servidorId = (await criarConversa(conversa.documentos.map((doc) => doc.id))).id;
        const idCriado = servidorId;
        atualizarConversa(conversa.chave, (c) => ({ ...c, servidorId: idCriado }));
      }

      const resposta = await perguntar(idsParaPerguntar, texto, servidorId);
      atualizarConversa(conversa.chave, (c) => ({
        ...c,
        pergunta: "",
        mensagens: [
          ...(c.mensagens ?? []),
          { pergunta: texto, resposta: resposta.resposta, citacoes: resposta.citacoes },
        ],
      }));
    } catch (e) {
      if (e instanceof ErroAutenticacao) {
        setPrecisaAutenticar(true);
      } else {
        setErro(e instanceof Error ? e.message : "Falha ao perguntar.");
      }
    } finally {
      setPerguntando(false);
    }
  }

  function handlePergunta(evento: FormEvent) {
    evento.preventDefault();
    enviarPergunta(ativa.pergunta);
  }

  async function handleAutenticado() {
    setLogado(true);
    setPrecisaAutenticar(false);
    // Primeiro a estante, depois a pergunta: a conversa que a pergunta
    // vai criar ainda não existe aqui, então a lista não a duplica.
    await carregarConversas();
    enviarPergunta(ativa.pergunta);
  }

  return (
    <div className="layout">
      <aside className="estante" aria-label="Suas conversas">
        <h2 className="estante-titulo">Estante</h2>

        <ul className="prateleira">
          {conversas.map((conversa) => {
            const titulo = tituloDaConversa(conversa);
            const linhas = linhasDaLombada(conversa);
            const estilo = {
              "--cor": CORES_LOMBADA[conversa.chave % CORES_LOMBADA.length],
              "--altura": `${ALTURAS_LOMBADA[conversa.chave % ALTURAS_LOMBADA.length]}px`,
            } as CSSProperties;
            return (
              <li key={conversa.chave} className="lombada-slot">
                <button
                  type="button"
                  className={`lombada${conversa.documentos.length === 0 ? " lombada-vazia" : ""}${conversa.documentos.length > 1 ? " lombada-dupla" : ""}`}
                  style={estilo}
                  title={conversa.documentos.map((doc) => doc.nome_original).join(" e ") || titulo}
                  aria-label={`Conversa: ${titulo}`}
                  aria-current={conversa.chave === ativa.chave ? "true" : undefined}
                  onClick={() => selecionarConversa(conversa.chave)}
                  disabled={ocupado}
                >
                  <span className="lombada-textos">
                    {linhas.map((linha, i) => (
                      <span key={i} className="lombada-texto">
                        {linha}
                      </span>
                    ))}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        <button
          type="button"
          className="nova-conversa"
          onClick={handleNovaConversa}
          // Uma conversa vazia já é a "nova": abrir outra seria só empilhar vazios.
          disabled={ocupado || ativa.documentos.length === 0}
        >
          + Nova conversa
        </button>
        {!logado && (
          <p className="estante-nota">
            Suas conversas ficam guardadas depois que você criar uma conta, ao fazer a primeira
            pergunta.
          </p>
        )}
      </aside>

      <main className="conversa">
        <h1>Lastro</h1>
        <p className="subtitulo">
          Converse com até dois PDFs: respostas fundamentadas nos documentos, com o trecho, o arquivo e a
          página de origem.
        </p>

        {ativa.documentos.length > 0 && (
          <div className="conversa-cabecalho">
            <h2 className="conversa-titulo">{tituloDaConversa(ativa)}</h2>
            <button type="button" className="apagar" onClick={handleApagarConversa} disabled={ocupado}>
              apagar conversa
            </button>
          </div>
        )}

        <section className="cartao cartao-documentos">
          {ativa.documentos.length > 0 && (
            <ul className="lista-documentos">
              {ativa.documentos.map((doc) => (
                <li key={doc.id}>
                  <label className="doc-item">
                    <input
                      type="checkbox"
                      checked={ativa.selecionados.includes(doc.id)}
                      onChange={() => alternarSelecao(doc.id)}
                      disabled={doc.status !== "pronto"}
                    />
                    <span className="doc-nome">{doc.nome_original}</span>
                  </label>
                  <span className={`selo selo-${doc.status}`}>{doc.status}</span>
                  <button
                    type="button"
                    className="remover"
                    onClick={() => handleRemover(doc.id)}
                    disabled={ocupado}
                  >
                    remover
                  </button>
                </li>
              ))}
            </ul>
          )}

          {ativa.documentos.length < MAX_DOCUMENTOS && (
            <>
              <label className="upload">
                {enviando
                  ? "Processando o documento…"
                  : ativa.documentos.length === 0
                    ? "Escolher PDF"
                    : "Adicionar segundo PDF"}
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handleArquivo}
                  disabled={enviando}
                />
              </label>
              {ativa.documentos.length === 0 && (
                <p className="upload-dica">Até dois PDFs por conversa. Para enviar, não precisa de conta.</p>
              )}
            </>
          )}
        </section>

        {ativa.mensagens === null && !erro && <p className="carregando">Abrindo a conversa…</p>}

        {(ativa.mensagens ?? []).map((mensagem, indice) => (
          <article key={indice} className="mensagem">
            <p className="mensagem-pergunta">{mensagem.pergunta}</p>
            <RespostaCard texto={mensagem.resposta} citacoes={mensagem.citacoes} />
          </article>
        ))}

        {precisaAutenticar && <Auth onAutenticado={handleAutenticado} />}

        {idsParaPerguntar.length > 0 && !precisaAutenticar && (
          <section className="cartao">
            <form onSubmit={handlePergunta} className="form-pergunta">
              <input
                type="text"
                value={ativa.pergunta}
                onChange={(e) => {
                  const texto = e.target.value;
                  atualizarConversa(ativa.chave, (c) => ({ ...c, pergunta: texto }));
                }}
                placeholder="Qual é o prazo de rescisão?"
                aria-label="Sua pergunta"
                disabled={perguntando}
              />
              <button type="submit" disabled={perguntando || !ativa.pergunta.trim()}>
                {perguntando ? "Perguntando…" : "Perguntar"}
              </button>
            </form>
          </section>
        )}

        {erro && <p className="erro">{erro}</p>}

        <div ref={fimDaConversa} />
      </main>
    </div>
  );
}

export default App;
