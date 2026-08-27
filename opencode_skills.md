# OpenCode - Pack Unificado de Skills & Diretrizes

Este arquivo consolida todas as skills, diretrizes operacionais e regras de desenvolvimento para o OpenCode. Ele é estruturado em blocos modulares para cobrir desenvolvimento de software, economia de tokens, UI/UX de alta fidelidade e segurança rigorosa.

---

## 🚀 1. Eficiência Máxima & Economia de Contexto (Token Savers)

### `skill-token-saver-diff-only`
- **Regra de Ouro:** NUNCA reescreva arquivos inteiros se apenas algumas linhas/funções foram modificadas.
- **Formato Cirúrgico:** Forneça apenas o bloco de código modificado com contexto mínimo de localização ou via patch/diff.
- **Zero Ruído:** Não adicione saudações ("Olá!"), encerramentos ("Espero ter ajudado") ou anúncios óbvios ("Aqui está o código:").

### `skill-token-saver-terse-mode`
- **Estilo:** Telegráfico, direto e denso em conteúdo.
- **Explicação Condicional:** Só justifique a mudança se houver risco de quebra de contrato ou trade-off arquitetural crítico. Não explique conceitos elementares.
- **Estruturação:** Utilize bullet points objetivos ou tabelas compactas em vez de longos parágrafos narrativos.

### `skill-token-saver-precision-debugger`
- **Formato Obrigatório de Debugging (Máximo 3 tópicos):**
  1. **Causa Raiz:** 1 a 2 frases identificando o arquivo, linha e motivo do bug.
  2. **Correção:** Apenas o bloco modificado exato.
  3. **Risco / Efeitos Colaterais:** 1 linha (somente se aplicável).

---

## 💻 2. Engenharia de Software & Arquitetura

### `skill-frontend-expert`
- **Stack:** React, Next.js (App Router), TypeScript, Tailwind CSS, Lucide Icons, Shadcn/UI.
- **Diretrizes:**
  - Componentização atômica e tipagem estrita (proibido o uso de `any`).
  - Isole lógica de negócio e chamadas de API em custom hooks reutilizáveis.
  - Priorize Server Components por padrão; declare `"use client"` apenas quando houver estado local, hooks de ciclo de vida ou eventos interativos.
  - Otimize renderização e utilize `next/image` para imagens estáticas/dinâmicas.

### `skill-backend-database`
- **Stack:** Python (Django / FastAPI), Node.js, PostgreSQL, SQLite, Prisma / Drizzle / SQLAlchemy.
- **Diretrizes:**
  - Padronize respostas REST/JSON: `{ "success": boolean, "data"?: any, "error"?: { "code": string, "message": string } }`.
  - Validação estrita de entrada (Zod / Pydantic) em todos os endpoints antes de qualquer processamento.
  - Modelagem relacional eficiente: crie índices para colunas de busca/filtros e chaves estrangeiras.
  - Elimine problemas de N+1 queries utilizando `select_related`/`prefetch_related` ou `joins` apropriados.

### `skill-saas-architecture-byok`
- **Diretrizes SaaS & IA:**
  - Em fluxos BYOK (Bring Your Own Key) e chamadas a modelos de IA, execute todas as requisições server-side; nunca exponha chaves no cliente.
  - Isole os dados de cada usuário/organização por `tenant_id` ou `user_id` em todas as operações de banco.
  - Implemente tratamento de rate limit (HTTP 429), retries com backoff exponencial e sanitização das respostas de LLMs antes de persistir.

### `skill-refactor-clean-code`
- **Diretrizes:**
  - Aplique o Princípio da Responsabilidade Única (SRP): funções curtas e focadas.
  - Remova dead code, imports não utilizados e `console.log`/`print` de depuração temporários.
  - Respeite as convenções do projeto (KISS e YAGNI).

---

## 🎨 3. Design de Interface & UI/UX

### `skill-ui-tokens-system`
- **Tokens Semânticos:** Use variáveis CSS e classes semânticas do Tailwind (`bg-background`, `text-foreground`, `border-border`, `bg-muted`, `text-muted-foreground`).
- **Escala Padronizada:** Evite valores arbitrários isolados (como `w-[347px]`); utilize a escala nativa de espaçamento, tipografia e bordas (`rounded-lg`, `rounded-md`).
- **Suporte a Dark Mode:** Garanta contraste e legibilidade acessível em ambos os modos de cor.

### `skill-ui-responsive-layout`
- **Mobile-First:** Escreva classes base para dispositivos móveis e adicione breakpoints progressivos (`sm:`, `md:`, `lg:`, `xl:`).
- **Proteção Visual:** Evite quebras de layout usando `min-w-0` em containers flexíveis e `truncate` / `line-clamp-*` com `title` acessível em textos longos.

### `skill-ui-component-states`
- **Estados Visuais Obrigatórios:**
  - **Loading / Skeleton:** `animate-pulse bg-muted rounded` respeitando a estrutura do card/tabela.
  - **Empty State:** Ícone sutil centralizado, título explicativo e botão de ação primária (CTA).
  - **Error State:** Banner contextual com mensagem legível e ação de retry.
  - **Interações:** `hover:opacity-90`, `active:scale-[0.98]`, `disabled:opacity-50 disabled:pointer-events-none`.

### `skill-ui-accessibility-a11y`
- **Acessibilidade:**
  - Utilize tags semânticas HTML5 (`<button>`, `<nav>`, `<aside>`, `<main>`).
  - Formulários sempre vinculados via `<label htmlFor="...">`.
  - Anéis de foco visíveis para navegação por teclado (`focus-visible:ring-2 focus-visible:ring-ring`).
  - Botões exclusivamente com ícones DEVEM conter `aria-label` descritivo.

### `skill-ui-motion-framer`
- **Animações:** Rápidas e funcionais (`150ms` a `300ms`), curvas `ease-out` em entradas e suporte a `motion-reduce:transition-none`.

---

## 🛡️ 4. Segurança de Aplicação (AppSec)

### `skill-sec-input-validation-owasp`
- **Prevenção OWASP:**
  - Valide payloads usando schemas estritos no backend.
  - Sanitize saídas HTML dinâmicas contra XSS (evite `dangerouslySetInnerHTML` sem DOMPurify).
  - Use consultas parametrizadas ou ORMs em 100% dos acessos ao banco para evitar SQL Injection.
  - Trate caminhos de arquivos com `path.basename` e restrinja diretórios para impedir Path Traversal.

### `skill-sec-auth-rbac`
- **Autenticação & Controle:**
  - Tokens e sessões devem residir em cookies `HttpOnly`, `Secure` e `SameSite=Lax/Strict` (nunca em `localStorage`).
  - Valide permissões no backend (middleware/service layer), nunca confiando na visibilidade de elementos no frontend.
  - Hash de senhas exclusivamente com Argon2id ou Bcrypt.

### `skill-sec-api-secrets-guard`
- **Segredos & Resiliência:**
  - NUNCA versione credenciais ou `.env` no Git.
  - Configure rate limiting por IP/usuário em rotas sensíveis de login e APIs de LLM.
  - Implemente headers defensivos (`CSP`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS`).
  - Nunca retorne stack traces ou mensagens internas do banco para o cliente.