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
  pagina: number;
  texto: string;
  distancia: number;
}

export interface Resposta {
  resposta: string;
  citacoes: Citacao[];
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

export async function perguntar(documentoId: number, pergunta: string): Promise<Resposta> {
  const resposta = await fetch("/perguntas", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cabecalhosAuth() },
    body: JSON.stringify({ documento_id: documentoId, pergunta }),
  });
  if (!resposta.ok) await tratarErro(resposta);
  return resposta.json();
}

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
