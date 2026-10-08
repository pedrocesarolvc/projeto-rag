import { useState, type ChangeEvent, type FormEvent } from "react";
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

// Interface mínima (Etapa 7, seção 7.4): upload, pergunta, resposta,
// citação ao lado, e a tela de cadastro/login na primeira pergunta
// (seção 7.5). Sem histórico de conversas nem tema escuro. A citação é
// o único capricho aceito, porque é ela que fecha o ciclo de confiança
// (Etapa 6, seção 6.6).
//
// Até 2 PDFs por pergunta: a resposta junta o que vier dos dois, e a
// caixa de seleção de cada um permite separá-los quando preciso
// (desmarcar um faz a pergunta valer só para o outro). O teto espelha
// o do servidor (PerguntaRequest.documento_ids) — o servidor é quem
// de fato impõe; aqui ele só evita oferecer o que seria recusado.
const MAX_DOCUMENTOS = 2;

function App() {
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  // Quais documentos entram na próxima pergunta. Todo upload novo já
  // nasce marcado — o caso comum é querer perguntar sobre tudo.
  const [selecionados, setSelecionados] = useState<number[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [pergunta, setPergunta] = useState("");
  const [resposta, setResposta] = useState<Resposta | null>(null);
  const [perguntando, setPerguntando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  // Cadastro adiado (seção 1.5): só vira true quando POST /perguntas
  // devolve 401 — nenhuma outra rota dispara isso (seção 7.2).
  const [precisaAutenticar, setPrecisaAutenticar] = useState(false);

  // Só documentos prontos e marcados entram na pergunta: um que ainda
  // está "indexando" ou "falhou" não tem chunks para buscar.
  const idsParaPerguntar = documentos
    .filter((doc) => doc.status === "pronto" && selecionados.includes(doc.id))
    .map((doc) => doc.id);

  async function handleArquivo(evento: ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0];
    // Limpa o input para que escolher de novo o mesmo arquivo (depois de
    // removê-lo, por exemplo) volte a disparar o evento de mudança.
    evento.target.value = "";
    if (!arquivo) return;

    setEnviando(true);
    setErro(null);
    setResposta(null);
    try {
      const doc = await enviarDocumento(arquivo);
      setDocumentos((atuais) => [...atuais, doc]);
      setSelecionados((atuais) => [...atuais, doc.id]);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao enviar o documento.");
    } finally {
      setEnviando(false);
    }
  }

  function alternarSelecao(id: number) {
    setSelecionados((atuais) =>
      atuais.includes(id) ? atuais.filter((outro) => outro !== id) : [...atuais, id],
    );
  }

  // Com o teto de 2, sem remover não haveria como trocar um PDF por
  // outro dentro da mesma tela.
  async function handleRemover(id: number) {
    setErro(null);
    try {
      await removerDocumento(id);
      setDocumentos((atuais) => atuais.filter((doc) => doc.id !== id));
      setSelecionados((atuais) => atuais.filter((outro) => outro !== id));
      setResposta(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao remover o documento.");
    }
  }

  // Separada de handlePergunta para poder ser chamada de novo, sozinha,
  // depois que o usuário autentica — sem ele precisar redigitar nada
  // (seção 7.5: "não perder a pergunta digitada").
  async function enviarPergunta(texto: string) {
    if (idsParaPerguntar.length === 0 || !texto.trim()) return;

    setPerguntando(true);
    setErro(null);
    try {
      const r = await perguntar(idsParaPerguntar, texto);
      setResposta(r);
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
    enviarPergunta(pergunta);
  }

  function handleAutenticado() {
    setPrecisaAutenticar(false);
    enviarPergunta(pergunta);
  }

  return (
    <main className="pagina">
      <h1>Lastro</h1>
      <p className="subtitulo">
        Converse com até dois PDFs: respostas fundamentadas nos documentos, com o trecho, o arquivo e a
        página de origem.
      </p>

      <section className="cartao">
        {documentos.length > 0 && (
          <ul className="lista-documentos">
            {documentos.map((doc) => (
              <li key={doc.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={selecionados.includes(doc.id)}
                    onChange={() => alternarSelecao(doc.id)}
                    disabled={doc.status !== "pronto"}
                  />
                  {doc.nome_original} ({doc.status})
                </label>
                <button
                  type="button"
                  className="remover"
                  onClick={() => handleRemover(doc.id)}
                  disabled={enviando || perguntando}
                >
                  remover
                </button>
              </li>
            ))}
          </ul>
        )}

        {documentos.length < MAX_DOCUMENTOS && (
          <label className="upload">
            {enviando
              ? "Processando o documento…"
              : documentos.length === 0
                ? "Escolher PDF"
                : "Adicionar segundo PDF"}
            <input
              type="file"
              accept="application/pdf"
              onChange={handleArquivo}
              disabled={enviando}
            />
          </label>
        )}
      </section>

      {idsParaPerguntar.length > 0 && !precisaAutenticar && (
        <section className="cartao">
          <form onSubmit={handlePergunta} className="form-pergunta">
            <input
              type="text"
              value={pergunta}
              onChange={(e) => setPergunta(e.target.value)}
              placeholder="Qual é o prazo de rescisão?"
              disabled={perguntando}
            />
            <button type="submit" disabled={perguntando || !pergunta.trim()}>
              {perguntando ? "Perguntando…" : "Perguntar"}
            </button>
          </form>
        </section>
      )}

      {precisaAutenticar && <Auth onAutenticado={handleAutenticado} />}

      {erro && <p className="erro">{erro}</p>}

      {resposta && (
        <section className="cartao resposta">
          <p className="texto-resposta">{resposta.resposta}</p>

          {resposta.citacoes.length > 0 && (
            <div className="citacoes">
              <h2>Fontes</h2>
              {resposta.citacoes.map((citacao, indice) => (
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
  );
}

export default App;
