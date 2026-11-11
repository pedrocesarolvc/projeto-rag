// Etapa 7 — cliente HTTP fino para as rotas do backend.
// Nenhuma lógica de RAG (nem de auth) mora aqui: só monta a
// requisição e devolve o corpo tipado. Caminhos relativos de
// propósito — em produção o FastAPI serve este build como estático,
// mesma origem, sem CORS.

export interface Documento {
  id: number;
  nome_original: string;
  status: "indexando" | "pronto" | "falhou";
}

export interface Citacao {
  documento: string;
  pagina: number;
  texto: string;
  distancia: number;
}

export interface Resposta {
  resposta: string;
  citacoes: Citacao[];
  conversa_id: number;
}

// Uma pergunta e a resposta dela, como ficam gravadas na conversa.
export interface Mensagem {
  pergunta: string;
  resposta: string;
  citacoes: Citacao[];
}

// Uma conversa na estante: os documentos dela dão o título da lombada.
export interface ConversaResumo {
  id: number;
  documentos: Documento[];
}

export interface ConversaDetalhe extends ConversaResumo {
  mensagens: Mensagem[];
}

// --- sessão anônima e token (cadastro adiado, seção 1.5) ---
//
// Todo upload precisa de um dono: ou um usuário autenticado, ou uma
// sessão anônima (seção 1.5, "a sessão anônima precisa de
// identificação própria"). O navegador gera esse identificador uma
// vez e guarda em localStorage — sobrevive a recarregar a página,
// que é exatamente o que permite perguntar depois de logar sem subir
// o documento de novo.

const CHAVE_SESSAO = "lastro_sessao_anonima";
const CHAVE_TOKEN = "lastro_token";

function obterSessaoAnonima(): string {
  let sessao = localStorage.getItem(CHAVE_SESSAO);
  if (!sessao) {
    sessao = crypto.randomUUID();
    localStorage.setItem(CHAVE_SESSAO, sessao);
  }
  return sessao;
}

export function obterToken(): string | null {
  return localStorage.getItem(CHAVE_TOKEN);
}

export function salvarToken(token: string): void {
  localStorage.setItem(CHAVE_TOKEN, token);
}

// Para um token que o servidor deixou de aceitar (expirou): guardá-lo
// só faria toda carga de página falhar com 401.
export function limparToken(): void {
  localStorage.removeItem(CHAVE_TOKEN);
}

function cabecalhosAuth(): HeadersInit {
  const cabecalhos: Record<string, string> = { "X-Sessao-Anonima": obterSessaoAnonima() };
  const token = obterToken();
  if (token) cabecalhos["Authorization"] = `Bearer ${token}`;
  return cabecalhos;
}

// Marca especificamente o 401 de POST /perguntas — é o único sinal
// que deve abrir a tela de login (seção 7.2: "é essa exigência, e só
// ela, que dispara a tela de login no frontend").
export class ErroAutenticacao extends Error {}

// FastAPI devolve `detail` de duas formas bem diferentes: uma string
// para erros que a própria rota levanta (HTTPException, ex.: "E-mail
// já cadastrado"), e uma LISTA de {loc, msg, type} quando é o
// Pydantic recusando o corpo antes mesmo de a rota rodar (422 —
// ex.: senha curta demais). Tratar só o caso string escondia o motivo
// real por trás de um genérico "Erro inesperado" nesse segundo caso.
function mensagemDeErro(detalhe: unknown, statusText: string): string {
  if (typeof detalhe === "string") return detalhe;

  if (Array.isArray(detalhe) && detalhe.length > 0) {
    return detalhe
      .map((erro: { loc?: unknown[]; msg?: string }) => {
        const campo = Array.isArray(erro.loc) ? erro.loc.at(-1) : undefined;
        return campo && erro.msg ? `${campo}: ${erro.msg}` : erro.msg;
      })
      .filter(Boolean)
      .join(" ");
  }

  return statusText || "Erro inesperado.";
}

async function tratarErro(resposta: globalThis.Response): Promise<never> {
  const corpo = await resposta.json().catch(() => null);
  const mensagem = mensagemDeErro(corpo?.detail, resposta.statusText);
  if (resposta.status === 401) throw new ErroAutenticacao(mensagem);
  throw new Error(mensagem);
}

export async function enviarDocumento(arquivo: File): Promise<Documento> {
  const formData = new FormData();
  formData.append("arquivo", arquivo);

  const resposta = await fetch("/documentos", {
    method: "POST",
    headers: cabecalhosAuth(),
    body: formData,
  });
  if (!resposta.ok) await tratarErro(resposta);
  return resposta.json();
}

export async function removerDocumento(documentoId: number): Promise<void> {
  const resposta = await fetch(`/documentos/${documentoId}`, {
    method: "DELETE",
    headers: cabecalhosAuth(),
  });
  if (!resposta.ok) await tratarErro(resposta);
}

// A pergunta vale para todos os documentos da lista (o servidor limita
// a 2): a resposta junta o que vier de cada um.
export async function perguntar(
  documentoIds: number[],
  pergunta: string,
  conversaId: number,
): Promise<Resposta> {
  const resposta = await fetch("/perguntas", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cabecalhosAuth() },
    body: JSON.stringify({ documento_ids: documentoIds, pergunta, conversa_id: conversaId }),
  });
  if (!resposta.ok) await tratarErro(resposta);
  return resposta.json();
}

// --- conversas (as lombadas da estante) ---
//
// Só existem para quem tem conta: todas respondem 401 sem login. Quem
// as chama na carga da página trata esse 401 como "ainda não há
// conversas", e não como motivo para abrir a tela de cadastro — só a
// primeira pergunta faz isso (seção 7.2).

async function pedirJson<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const resposta = await fetch(caminho, {
    ...opcoes,
    headers: { "Content-Type": "application/json", ...cabecalhosAuth() },
  });
  if (!resposta.ok) await tratarErro(resposta);
  return resposta.status === 204 ? (undefined as T) : resposta.json();
}

// Cria a conversa com TODOS os documentos, não só os marcados na hora:
// um PDF desmarcado também pertence ao livro.
export const criarConversa = (documentoIds: number[]) =>
  pedirJson<ConversaResumo>("/conversas", {
    method: "POST",
    body: JSON.stringify({ documento_ids: documentoIds }),
  });

export const listarConversas = () => pedirJson<ConversaResumo[]>("/conversas");

export const obterConversa = (id: number) => pedirJson<ConversaDetalhe>(`/conversas/${id}`);

export const apagarConversa = (id: number) => pedirJson<void>(`/conversas/${id}`, { method: "DELETE" });

export const acrescentarDocumento = (conversaId: number, documentoId: number) =>
  pedirJson<ConversaResumo>(`/conversas/${conversaId}/documentos`, {
    method: "POST",
    body: JSON.stringify({ documento_id: documentoId }),
  });

// --- conta (Etapa 7, seção 7.3) ---

async function autenticar(rota: "registrar" | "login", email: string, senha: string): Promise<string> {
  const resposta = await fetch(`/auth/${rota}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cabecalhosAuth() },
    body: JSON.stringify({ email, senha }),
  });
  if (!resposta.ok) await tratarErro(resposta);
  const { token } = await resposta.json();
  salvarToken(token);
  return token;
}

export const registrar = (email: string, senha: string) => autenticar("registrar", email, senha);
export const login = (email: string, senha: string) => autenticar("login", email, senha);
