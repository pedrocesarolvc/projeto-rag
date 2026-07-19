// Etapa 7 — cliente HTTP fino para as duas rotas do backend.
// Nenhuma lógica de RAG mora aqui: só monta a requisição e devolve
// o corpo tipado. Caminhos relativos de propósito — em produção o
// FastAPI serve este build como estático, mesma origem, sem CORS.

export interface Documento {
  id: number;
  nome_original: string;
  status: "indexando" | "pronto" | "falhou";
}

export interface Citacao {
  pagina: number;
  texto: string;
  distancia: number;
}

export interface Resposta {
  resposta: string;
  citacoes: Citacao[];
}

async function tratarErro(resposta: globalThis.Response): Promise<never> {
  const corpo = await resposta.json().catch(() => null);
  const detalhe = corpo?.detail ?? resposta.statusText;
  throw new Error(typeof detalhe === "string" ? detalhe : "Erro inesperado.");
}

export async function enviarDocumento(arquivo: File): Promise<Documento> {
  const formData = new FormData();
  formData.append("arquivo", arquivo);

  const resposta = await fetch("/documentos", { method: "POST", body: formData });
  if (!resposta.ok) await tratarErro(resposta);
  return resposta.json();
}

export async function perguntar(documentoId: number, pergunta: string): Promise<Resposta> {
  const resposta = await fetch("/perguntas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ documento_id: documentoId, pergunta }),
  });
  if (!resposta.ok) await tratarErro(resposta);
  return resposta.json();
}
