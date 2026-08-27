/**
 * Core Configuration & Security Provider
 * NexusCRM Pro • Clean Architecture
 */

export const CONFIG = {
  APP_NAME: 'NexusCRM Pro',
  VERSION: '2.4.0',
  DEFAULT_COLUMNS: [
    { key: 'NOVO', label: 'Novos Leads', color: 'border-slate-800/80 bg-slate-900/40', badge: 'bg-slate-800 text-slate-300' },
    { key: 'APRESENTADO', label: 'Apresentados (PTT)', color: 'border-blue-900/50 bg-blue-950/10', badge: 'bg-blue-950 text-blue-400 border border-blue-800' },
    { key: 'NEGOCIACAO', label: 'Em Negociação', color: 'border-amber-900/50 bg-amber-950/10', badge: 'bg-amber-950 text-amber-400 border border-amber-800' },
    { key: 'FECHADO', label: 'Ganhos / Fechados', color: 'border-emerald-900/50 bg-emerald-950/10', badge: 'bg-emerald-950 text-emerald-400 border border-emerald-800' },
    { key: 'REJEITADO', label: 'Rejeitados', color: 'border-rose-900/50 bg-rose-950/10', badge: 'bg-rose-950 text-rose-400 border border-rose-800' }
  ],
  STORAGE_KEYS: {
    LEADS: 'nexus_leads_db',
    CAMPAIGNS: 'nexus_campaigns_db',
    PROMPTS: 'nexus_master_prompts',
    SETTINGS: 'nexus_app_settings'
  }
};
