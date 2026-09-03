import { useState, type ChangeEvent, type FormEvent } from "react";
import { enviarDocumento, perguntar, ErroAutenticacao, type Documento, type Resposta } from "./api";
import Auth from "./Auth";
import "./App.css";

// Interface mínima (Etapa 7, seção 7.4): upload, pergunta, resposta,
// citação ao lado, e a tela de cadastro/login na primeira pergunta
// (seção 7.5). Nada além disso — sem histórico, múltiplos documentos
// ou tema escuro. A citação é o único capricho aceito, porque é ela
// que fecha o ciclo de confiança (Etapa 6, seção 6.6).

function App() {
  const [documento, setDocumento] = useState<Documento | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [pergunta, setPergunta] = useState("");
  const [resposta, setResposta] = useState<Resposta | null>(null);
  const [perguntando, setPerguntando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  // Cadastro adiado (seção 1.5): só vira true quando POST /perguntas
  // devolve 401 — nenhuma outra rota dispara isso (seção 7.2).
  const [precisaAutenticar, setPrecisaAutenticar] = useState(false);

  async function handleArquivo(evento: ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0];
    if (!arquivo) return;

    setEnviando(true);
    setErro(null);
    setResposta(null);
    try {
      const doc = await enviarDocumento(arquivo);
      setDocumento(doc);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao enviar o documento.");
    } finally {
      setEnviando(false);
    }
  }

  // Separada de handlePergunta para poder ser chamada de novo, sozinha,
  // depois que o usuário autentica — sem ele precisar redigitar nada
  // (seção 7.5: "não perder a pergunta digitada").
  async function enviarPergunta(texto: string) {
    if (!documento || !texto.trim()) return;

    setPerguntando(true);
    setErro(null);
    try {
      const r = await perguntar(documento.id, texto);
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
        Converse com um PDF: respostas fundamentadas no documento, com o trecho e a página de origem.
      </p>

      <section className="cartao">
        <label className="upload">
          {enviando
            ? "Processando o documento…"
            : documento
              ? `${documento.nome_original} (${documento.status})`
              : "Escolher PDF"}
          <input
            type="file"
            accept="application/pdf"
            onChange={handleArquivo}
            disabled={enviando}
          />
        </label>
      </section>

      {documento?.status === "pronto" && !precisaAutenticar && (
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
                  <footer>página {citacao.pagina}</footer>
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
