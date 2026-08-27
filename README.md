# BotClientes - Backend Completo

Sistema de mineração de leads, automação WhatsApp e CRM com arquitetura híbrida Node.js + Python (FastAPI).

## Arquitetura

```
backend/
├── app/                    # FastAPI Application
│   ├── main.py            # Entry point + API routes
│   └── services/
│       ├── scraping_service.py      # Google Maps scraping + qualificação
│       └── github_ingestion.py      # Análise de repo GitHub para ICP
├── worker/                 # Background Workers
│   └── audio_queue.py     # Fila isolada RTX 3050 + Evolution API
├── node-services/          # Node.js Services
│   └── src/index.js       # Evolution API webhooks + Socket.io
├── voice-api/              # Local TTS API (RTX 3050)
│   └── main.py            # Edge-TTS / Coqui / Piper
├── schemas/                # Pydantic Schemas (validação rigorosa)
│   ├── campaign.py
│   ├── lead.py
│   ├── scraping.py
│   └── audio.py
├── config/                 # Configuração centralizada
│   ├── settings.py        # Pydantic Settings
│   └── database.py        # Supabase clients
├── migrations/             # SQL Schema + RLS
│   └── 001_initial_schema.sql
├── requirements.txt        # Python deps
└── Dockerfile

frontend/
├── src/
│   ├── actions/           # Next.js Server Actions
│   │   ├── leads.ts
│   │   └── campaigns.ts
│   ├── components/        # React Components
│   │   ├── KanbanBoard.tsx
│   │   └── ScrapingMap.tsx
│   ├── hooks/             # Custom Hooks
│   │   └── useLeads.ts
│   ├── lib/               # API Client
│   │   └── api.ts
│   └── types/             # TypeScript Types
│       └── index.ts
```

## Funcionalidades Implementadas

### Motor de Mineração e Contexto (Backend)
- **Scraping Georreferenciado**: Google Places API com validação estrita (Pydantic)
- **Filtros de Qualificação Ativa**: 
  - Validação de telefone E.164 obrigatório
  - Detecção de infraestrutura concorrente (placeholder)
- **Ingestão de Repositórios**: Análise de arquivos estratégicos do GitHub para deduzir ICP
- **Processamento Físico Isolado**: Fila de áudio com concorrência = 1 (RTX 3050)

### Engenharia Frontend (Next.js)
- **Server Components**: Kanban com `useOptimistic` para mutações instantâneas
- **Server Actions**: Validação server-side com `revalidatePath`
- **UI Anti-IA**: Tipografia expressiva, cores OKLCH, focus-visible, animações
- **Estados Visuais**: Skeletons, empty states, feedback tátil

### Segurança e Dados
- **Isolamento Multitenant**: PostgreSQL + RLS (Row Level Security) no Supabase
- **Proteção de Segredos**: Pydantic Settings + .env
- **Validação Estrita**: Schemas Pydantic = Zod equivalent

## Como Rodar

### Pré-requisitos
- Docker + Docker Compose
- Google Maps API Key
- Evolution API rodando (ou use o container)
- Conta Supabase (ou PostgreSQL local)

### 1. Configurar Variáveis
```bash
cp backend/.env.example backend/.env
# Edite backend/.env com suas chaves
```

### 2. Subir Tudo
```bash
docker-compose up -d
```

### 3. Acessar
- Backend API: http://localhost:8000/docs
- Node Services: http://localhost:3001
- Voice API: http://localhost:8001
- Evolution API: http://localhost:8080
- Frontend: `cd frontend && npm run dev` → http://localhost:3000

### 4. Executar Migrations
No Supabase SQL Editor, execute o conteúdo de `backend/migrations/001_initial_schema.sql`

## Endpoints Principais

### Campanhas
```
POST   /api/v1/campaigns              # Criar campanha
GET    /api/v1/campaigns              # Listar campanhas
GET    /api/v1/campaigns/{id}         # Obter campanha
PATCH  /api/v1/campaigns/{id}         # Atualizar campanha
DELETE /api/v1/campaigns/{id}         # Deletar campanha
POST   /api/v1/campaigns/{id}/scrape  # Executar scraping
POST   /api/v1/campaigns/{id}/analyze-repo  # Analisar GitHub para ICP
```

### Leads
```
POST   /api/v1/leads                  # Criar lead
GET    /api/v1/campaigns/{id}/leads   # Listar leads da campanha
GET    /api/v1/leads/{id}             # Obter lead
PATCH  /api/v1/leads/{id}             # Atualizar lead
POST   /api/v1/leads/{id}/move        # Mover no Kanban (Server Action)
POST   /api/v1/leads/{id}/outreach    # Disparar WhatsApp
```

### Áudio / Fila
```
GET    /api/v1/audio/queue/status     # Status da fila
GET    /api/v1/audio/jobs/{job_id}    # Status do job
```

### Node Services (Webhooks + Real-time)
```
POST   /webhook/evolution             # Webhook Evolution API
WS     /socket.io                     # Real-time updates
```

## Fluxo de Outreach Completo

```
1. IA decide mensagem + áudio (precisa_áudio: true)
       ↓
2. Job entra na AudioQueue (max 1 concorrente)
       ↓
3. Voice API (RTX 3050) gera .ogg via Edge-TTS/Coqui/Piper
       ↓
4. OutreachOrchestrator:
   - Simula "digitando..." (4-6s)
   - Envia texto via Evolution API
   - Simula "gravando áudio..." (5-8s)  
   - Envia áudio PTT via Evolution API
       ↓
5. Atualiza lead no CRM (status: APRESENTADO, calls_count: 1)
       ↓
6. DELAY ANTI-BAN CRÍTICO: 5-10 minutos antes do próximo
```

## Tecnologias

| Camada | Stack |
|--------|-------|
| API Backend | FastAPI + Pydantic v2 + Uvicorn |
| Workers | Python asyncio + BullMQ (Redis) |
| Node Services | Express + Socket.io + BullMQ |
| Voice API | Edge-TTS (padrão) / Coqui XTTS v2 / Piper |
| Database | PostgreSQL (Supabase) + RLS |
| Queue | Redis + BullMQ |
| WhatsApp | Evolution API (Baileys) |
| Maps | Google Places API |
| Frontend | Next.js 14 App Router + TypeScript + Tailwind |

## Variáveis de Ambiente Críticas

```env
# Obrigatórias
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_ROLE_KEY=
GOOGLE_MAPS_API_KEY=
EVOLUTION_API_URL=
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=
SECRET_KEY=

# Opcionais
GITHUB_TOKEN=
OPENAI_API_KEY=
VOICE_API_URL=http://localhost:8001
TTS_ENGINE=edge-tts  # ou coqui, piper
```

## Próximos Passos

- [ ] Implementar autenticação (Supabase Auth + JWT)
- [ ] Adicionar testes unitários (pytest + jest)
- [ ] Configurar CI/CD (GitHub Actions)
- [ ] Adicionar monitoramento (Sentry + Prometheus)
- [ ] Implementar rate limiting na API
- [ ] Adicionar dashboard de métricas KPI