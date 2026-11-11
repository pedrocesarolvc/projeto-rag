import {
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  enviarDocumento,
  perguntar,
  removerDocumento,
  ErroAutenticacao,
  type Documento,
  type Resposta,
} from "./api";
import Auth from "./Auth";
import "./App.css";

// Cada assunto vive numa conversa, e cada conversa é uma lombada na
// estante: o nome dos PDFs enviados é o título do livro. O fluxo dentro
// de uma conversa é o de sempre — enviar até 2 PDFs, perguntar (conta
// exigida só aqui, cadastro adiado, seção 1.5), ler a resposta com as
// fontes.
//
// Por enquanto as conversas só existem em memória, nesta janela: o
// servidor ainda não guarda histórico. Cada pergunta continua
// independente das anteriores (o Lastro não "lembra" da conversa) —
// de propósito, para não mexer em como o prompt é montado, que é onde
// mora o grounding.

// Até 2 PDFs por pergunta: a resposta junta o que vier dos dois, e a
// caixa de seleção de cada um permite separá-los quando preciso. O teto
// espelha o do servidor (PerguntaRequest.documento_ids) — o servidor é
// quem de fato impõe; aqui ele só evita oferecer o que seria recusado.
const MAX_DOCUMENTOS = 2;

// A cor e a altura da lombada saem do id da conversa, não da posição na
// estante: assim um livro não muda de aspecto quando outro é removido.
const CORES_LOMBADA = ["#4a3324", "#2e4a5f", "#5a3e2b", "#2f4f46", "#6b4a33", "#3b3f5c"];
const ALTURAS_LOMBADA = [190, 172, 182, 166, 178, 170];

interface Conversa {
  id: number;
  documentos: Documento[];
  // Quais documentos entram na próxima pergunta. Todo upload novo já
  // nasce marcado — o caso comum é querer perguntar sobre tudo.
  selecionados: number[];
  pergunta: string;
  resposta: Resposta | null;
}

function novaConversa(id: number): Conversa {
  return { id, documentos: [], selecionados: [], pergunta: "", resposta: null };
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

function App() {
  const [conversas, setConversas] = useState<Conversa[]>([novaConversa(1)]);
  const [ativaId, setAtivaId] = useState(1);
  const proximoId = useRef(2);

  const [enviando, setEnviando] = useState(false);
  const [perguntando, setPerguntando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  // Cadastro adiado (seção 1.5): só vira true quando POST /perguntas
  // devolve 401 — nenhuma outra rota dispara isso (seção 7.2).
  const [precisaAutenticar, setPrecisaAutenticar] = useState(false);

  const ativa = conversas.find((c) => c.id === ativaId) ?? conversas[0];
  // Trocar de conversa no meio de um envio faria a resposta cair no
  // lugar errado; enquanto algo está em andamento, a estante espera.
  const ocupado = enviando || perguntando;

  // Só documentos prontos e marcados entram na pergunta: um que ainda
  // está "indexando" ou "falhou" não tem chunks para buscar.
  const idsParaPerguntar = ativa.documentos
    .filter((doc) => doc.status === "pronto" && ativa.selecionados.includes(doc.id))
    .map((doc) => doc.id);

  function atualizarConversa(id: number, mudar: (conversa: Conversa) => Conversa) {
    setConversas((atuais) => atuais.map((c) => (c.id === id ? mudar(c) : c)));
  }

  function selecionarConversa(id: number) {
    setAtivaId(id);
    setErro(null);
    setPrecisaAutenticar(false);
  }

  function handleNovaConversa() {
    const id = proximoId.current++;
    setConversas((atuais) => [...atuais, novaConversa(id)]);
    selecionarConversa(id);
  }

  async function handleArquivo(evento: ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0];
    // Limpa o input para que escolher de novo o mesmo arquivo (depois de
    // removê-lo, por exemplo) volte a disparar o evento de mudança.
    evento.target.value = "";
    if (!arquivo) return;

    const conversaId = ativa.id;
    setEnviando(true);
    setErro(null);
    try {
      const doc = await enviarDocumento(arquivo);
      atualizarConversa(conversaId, (c) => ({
        ...c,
        documentos: [...c.documentos, doc],
        selecionados: [...c.selecionados, doc.id],
        resposta: null,
      }));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao enviar o documento.");
    } finally {
      setEnviando(false);
    }
  }

  function alternarSelecao(docId: number) {
    atualizarConversa(ativa.id, (c) => ({
      ...c,
      selecionados: c.selecionados.includes(docId)
        ? c.selecionados.filter((outro) => outro !== docId)
        : [...c.selecionados, docId],
    }));
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
    if (restantes.length === 0 && conversas.length > 1) {
      // Livro sem nenhum documento não tem título: sai da estante.
      const outras = conversas.filter((c) => c.id !== ativa.id);
      setConversas(outras);
      selecionarConversa(outras[outras.length - 1].id);
      return;
    }
    atualizarConversa(ativa.id, (c) => ({
      ...c,
      documentos: restantes,
      selecionados: c.selecionados.filter((outro) => outro !== docId),
      resposta: null,
    }));
  }

  // Separada de handlePergunta para poder ser chamada de novo, sozinha,
  // depois que o usuário autentica — sem ele precisar redigitar nada
  // (seção 7.5: "não perder a pergunta digitada").
  async function enviarPergunta(texto: string) {
    if (idsParaPerguntar.length === 0 || !texto.trim()) return;

    const conversaId = ativa.id;
    setPerguntando(true);
    setErro(null);
    try {
      const r = await perguntar(idsParaPerguntar, texto);
      atualizarConversa(conversaId, (c) => ({ ...c, resposta: r }));
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

  function handleAutenticado() {
    setPrecisaAutenticar(false);
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
              "--cor": CORES_LOMBADA[conversa.id % CORES_LOMBADA.length],
              "--altura": `${ALTURAS_LOMBADA[conversa.id % ALTURAS_LOMBADA.length]}px`,
            } as CSSProperties;
            return (
              <li key={conversa.id} className="lombada-slot">
                <button
                  type="button"
                  className={`lombada${conversa.documentos.length === 0 ? " lombada-vazia" : ""}${conversa.documentos.length > 1 ? " lombada-dupla" : ""}`}
                  style={estilo}
                  title={conversa.documentos.map((doc) => doc.nome_original).join(" e ") || titulo}
                  aria-label={`Conversa: ${titulo}`}
                  aria-current={conversa.id === ativa.id ? "true" : undefined}
                  onClick={() => selecionarConversa(conversa.id)}
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
        <p className="estante-nota">
          Por enquanto, as conversas duram até você recarregar a página.
        </p>
      </aside>

      <main className="conversa">
        <h1>Lastro</h1>
        <p className="subtitulo">
          Converse com até dois PDFs: respostas fundamentadas nos documentos, com o trecho, o arquivo e a
          página de origem.
        </p>

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

        {idsParaPerguntar.length > 0 && !precisaAutenticar && (
          <section className="cartao">
            <form onSubmit={handlePergunta} className="form-pergunta">
              <input
                type="text"
                value={ativa.pergunta}
                onChange={(e) => {
                  const texto = e.target.value;
                  atualizarConversa(ativa.id, (c) => ({ ...c, pergunta: texto }));
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

        {precisaAutenticar && <Auth onAutenticado={handleAutenticado} />}

        {erro && <p className="erro">{erro}</p>}

        {ativa.resposta && (
          <section className="cartao resposta">
            <p className="selo-seguro">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
                <rect x="4" y="11" width="16" height="10" rx="2" />
                <path d="M8 11V7a4 4 0 0 1 8 0v4" />
              </svg>
              Fundamentada nos documentos
            </p>
            <p className="texto-resposta">{comEnfase(ativa.resposta.resposta)}</p>

            {ativa.resposta.citacoes.length > 0 && (
              <div className="citacoes">
                <h2>Fontes</h2>
                {ativa.resposta.citacoes.map((citacao, indice) => (
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
        )}
      </main>
    </div>
  );
}

export default App;
