'use client';

import { useOptimistic, useState, useCallback } from 'react';
import { GripVertical, Phone, Bot, ChevronLeft, ChevronRight, Plus, Search, MapPin, RefreshCw, AlertTriangle } from 'lucide-react';
import { moveLeadAction } from '@/actions/leads';
import { Lead, LeadStatus } from '@/lib/api';

const COLUMNS: { key: LeadStatus; label: string; color: string }[] = [
  { key: 'NOVO', label: 'Novos', color: 'bg-zinc-800/50 border-zinc-700' },
  { key: 'APRESENTADO', label: 'Apresentados', color: 'bg-blue-900/20 border-blue-800' },
  { key: 'NEGOCIACAO', label: 'Negociação', color: 'bg-amber-900/20 border-amber-800' },
  { key: 'FECHADO', label: 'Fechados', color: 'bg-emerald-900/20 border-emerald-800' },
  { key: 'REJEITADO', label: 'Rejeitados', color: 'bg-rose-900/20 border-rose-800' },
];

interface KanbanBoardProps {
  initialLeads: Lead[];
  campaignId: string;
}

function LeadCard({ lead, onDragStart }: { lead: Lead; onDragStart: (e: React.DragEvent, leadId: string) => void }) {
  return (
    <article
      draggable
      onDragStart={(e) => onDragStart(e, lead.id)}
      className="group relative bg-zinc-900/60 border border-zinc-700 rounded-xl p-4 transition-all duration-200 hover:border-zinc-600 hover:shadow-xl hover:shadow-zinc-900/50 cursor-grab active:cursor-grabbing"
      style={{ minWidth: '280px', maxWidth: '320px' }}
    >
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-zinc-100 tracking-[-0.01em] truncate pr-8">
          {lead.business_name}
        </h3>
        <button aria-label="Mover lead" className="cursor-grab text-zinc-500 hover:text-zinc-300 opacity-0 group-hover:opacity-100 transition-opacity">
          <GripVertical size={16} />
        </button>
      </div>

      <div className="flex items-center gap-2 mt-1">
        <span className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
          lead.calls_count > 0 ? 'bg-rose-950 text-rose-400' : 'bg-emerald-950 text-emerald-400'
        }`}>
          <Phone size={10} /> {lead.calls_count > 0 ? 'Ligação Usada' : 'Ligação Livre'}
        </span>
        {lead.status === 'APRESENTADO' && (
          <span className="inline-flex items-center gap-1 rounded-sm bg-violet-950 px-2 py-0.5 text-[10px] font-bold text-violet-400 uppercase">
            <Bot size={10} /> Áudio Clonado
          </span>
        )}
      </div>

      {lead.preview_url && (
        <a href={lead.preview_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-200 text-sm transition-colors">
          <MapPin size={12} /> Ver no Mapa
        </a>
      )}

      <div className="mt-3 pt-3 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-500">
        <span>{lead.phone_number}</span>
        <span>{new Date(lead.created_at).toLocaleDateString('pt-BR')}</span>
      </div>
    </article>
  );
}

function Column({ status, label, leads, onDragOver, onDragLeave, onDrop, onDragStart }: {
  status: LeadStatus;
  label: string;
  leads: Lead[];
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, status: LeadStatus) => void;
  onDragStart: (e: React.DragEvent, leadId: string) => void;
}) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setIsDragOver(true);
    onDragOver(e);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    onDragLeave(e);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    onDrop(e, status);
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`${status === 'NOVO' ? 'bg-zinc-800/50 border-zinc-700' : ''} rounded-2xl border-2 transition-colors duration-200 ${isDragOver ? 'border-violet-500 bg-violet-900/10' : ''} flex flex-col min-h-[500px]`}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700">
        <h2 className="font-medium text-zinc-300 flex items-center gap-2">
          <span className="px-2 py-0.5 rounded text-xs font-bold bg-zinc-800 text-zinc-400">
            {leads.length}
          </span>
          {label}
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3" role="list" aria-label={`${label} leads`}>
        {leads.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <p className="text-sm">Nenhum lead</p>
            <p className="text-xs mt-1">Arraste leads para cá</p>
          </div>
        ) : (
          leads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onDragStart={onDragStart} />
          ))
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({ initialLeads, campaignId }: KanbanBoardProps) {
  const [leads, setLeads] = useState<Lead[]>(initialLeads);
  const [draggedLeadId, setDraggedLeadId] = useState<string | null>(null);
  const [optimisticLeads, setOptimisticLeads] = useOptimistic(leads, (state, newLeads: Lead[]) => newLeads);

  const handleDragStart = useCallback((e: React.DragEvent, leadId: string) => {
    setDraggedLeadId(leadId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', leadId);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent, newStatus: LeadStatus) => {
    e.preventDefault();
    const leadId = draggedLeadId || e.dataTransfer.getData('text/plain');
    
    if (!leadId) return;

    const lead = leads.find(l => l.id === leadId);
    if (!lead || lead.status === newStatus) {
      setDraggedLeadId(null);
      return;
    }

    // Optimistic update
    const updatedLeads = leads.map(l => 
      l.id === leadId ? { ...l, status: newStatus } : l
    );
    setOptimisticLeads(updatedLeads);

    try {
      await moveLeadAction(leadId, newStatus);
      setLeads(updatedLeads);
    } catch (error) {
      // Revert on error
      setOptimisticLeads(leads);
      console.error('Failed to move lead:', error);
      alert('Erro ao mover lead. Tente novamente.');
    } finally {
      setDraggedLeadId(null);
    }
  }, [draggedLeadId, leads, setOptimisticLeads]);

  const leadsByStatus = COLUMNS.reduce((acc, col) => {
    acc[col.key] = optimisticLeads.filter(l => l.status === col.key);
    return acc;
  }, {} as Record<LeadStatus, Lead[]>);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 px-2 -mx-2 min-h-[550px]">
      {COLUMNS.map((col) => (
        <Column
          key={col.key}
          status={col.key}
          label={col.label}
          leads={leadsByStatus[col.key]}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onDragStart={handleDragStart}
        />
      ))}
    </div>
  );
}