import { useState, type ChangeEvent, type FormEvent } from "react";
import { enviarDocumento, perguntar, type Documento, type Resposta } from "./api";
import "./App.css";

// Interface mínima (Etapa 7, seção 7.4): upload, pergunta, resposta,
// citação ao lado. Nada além disso — sem login, histórico, múltiplos
// documentos ou tema escuro. A citação é o único capricho aceito,
// porque é ela que fecha o ciclo de confiança (Etapa 6, seção 6.6).

function App() {
  const [documento, setDocumento] = useState<Documento | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [pergunta, setPergunta] = useState("");
  const [resposta, setResposta] = useState<Resposta | null>(null);
  const [perguntando, setPerguntando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

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

  async function handlePergunta(evento: FormEvent) {
    evento.preventDefault();
    if (!documento || !pergunta.trim()) return;

    setPerguntando(true);
    setErro(null);
    try {
      const r = await perguntar(documento.id, pergunta);
      setResposta(r);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao perguntar.");
    } finally {
      setPerguntando(false);
    }
  }

  return (
    <main className="pagina">
      <h1>Converse com um PDF</h1>
      <p className="subtitulo">
        Respostas fundamentadas no documento, com o trecho e a página de origem.
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

      {documento?.status === "pronto" && (
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
