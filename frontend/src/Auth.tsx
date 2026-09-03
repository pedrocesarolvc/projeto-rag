import { useState, type FormEvent } from "react";
import { login, registrar } from "./api";

// Etapa 7, seção 7.5: a tela de cadastro/login só aparece quando o
// usuário já subiu um documento e tenta fazer a primeira pergunta —
// nunca antes. Os dois detalhes que fazem essa interrupção não
// irritar: explicar o porquê na própria tela, e (em App.tsx) reenviar
// a pergunta já digitada assim que autenticar, sem pedir para
// redigitar.

interface AuthProps {
  onAutenticado: () => void;
}

export default function Auth({ onAutenticado }: AuthProps) {
  const [modo, setModo] = useState<"registrar" | "login">("registrar");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      if (modo === "registrar") {
        await registrar(email, senha);
      } else {
        await login(email, senha);
      }
      onAutenticado();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao autenticar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="cartao auth">
      <p className="auth-explicacao">
        {modo === "registrar"
          ? "Crie uma conta para salvar este documento e suas perguntas."
          : "Entre na sua conta para continuar."}
      </p>

      <form onSubmit={handleSubmit} className="form-auth">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="e-mail"
          required
          disabled={enviando}
        />
        <input
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          placeholder="senha (mínimo 8 caracteres)"
          minLength={8}
          required
          disabled={enviando}
        />
        <button type="submit" disabled={enviando}>
          {enviando ? "Enviando…" : modo === "registrar" ? "Criar conta" : "Entrar"}
        </button>
      </form>

      {erro && <p className="erro">{erro}</p>}

      <button
        type="button"
        className="auth-alternar"
        onClick={() => setModo(modo === "registrar" ? "login" : "registrar")}
      >
        {modo === "registrar" ? "Já tenho conta" : "Criar uma conta"}
      </button>
    </section>
  );
}
