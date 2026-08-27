'use client';

import { useState, useEffect, useCallback } from 'react';
import { Lead, LeadStatus, LeadCreate, ScrapingResponse } from '@/types';
import { leadApi, campaignApi } from '@/lib/api';

interface UseLeadsOptions {
  campaignId: string;
  initialLeads?: Lead[];
  initialStatus?: LeadStatus;
}

export function useLeads({ campaignId, initialLeads = [], initialStatus }: UseLeadsOptions) {
  const [leads, setLeads] = useState<Lead[]>(initialLeads);
  const [loading, setLoading] = useState(!initialLeads.length);
  const [error, setError] = useState<string | null>(null);

  const fetchLeads = useCallback(async (status?: LeadStatus) => {
    try {
      setLoading(true);
      setError(null);
      const data = await leadApi.list(campaignId, status);
      setLeads(data);
    } catch (err: any) {
      setError(err.message);
      console.error('Failed to fetch leads:', err);
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    if (!initialLeads.length) {
      fetchLeads(initialStatus);
    }
  }, [fetchLeads, initialLeads.length, initialStatus]);

  const moveLead = useCallback(async (leadId: string, newStatus: LeadStatus) => {
    // Optimistic update
    const previousLeads = [...leads];
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status: newStatus } : l));

    try {
      await leadApi.move(leadId, newStatus);
    } catch (err: any) {
      setLeads(previousLeads);
      setError(err.message);
      throw err;
    }
  }, [leads]);

  const createLead = useCallback(async (data: LeadCreate) => {
    try {
      const lead = await leadApi.create(data);
      setLeads(prev => [lead, ...prev]);
      return lead;
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }, []);

  const updateLead = useCallback(async (leadId: string, data: Partial<Lead>) => {
    const previousLeads = [...leads];
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, ...data } : l));

    try {
      await leadApi.update(leadId, data);
    } catch (err: any) {
      setLeads(previousLeads);
      setError(err.message);
      throw err;
    }
  }, [leads]);

  const triggerOutreach = useCallback(async (
    leadId: string,
    iaResponse: { text_message: string; needs_audio: boolean; audio_text?: string; intent: string },
    leadContext: { business_name: string; preview_url?: string; niche?: string; ai_rules?: Record<string, any> }
  ) => {
    try {
      const result = await leadApi.triggerOutreach(leadId, { ia_response: iaResponse, lead_context: leadContext });
      
      // Update lead status to APRESENTADO
      setLeads(prev => prev.map(l => 
        l.id === leadId ? { ...l, status: 'APRESENTADO' as LeadStatus, calls_count: 1 } : l
      ));
      
      return result;
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }, []);

  const scrape = useCallback(async (
    location: { latitude: number; longitude: number; radius_meters: number },
    categories: string[] = ['restaurant', 'store', 'health', 'beauty'],
    maxResults = 100
  ): Promise<ScrapingResponse> => {
    try {
      setLoading(true);
      setError(null);
      const result = await campaignApi.scrape(campaignId, { campaign_id: campaignId, location, categories, max_results: maxResults });
      // Refresh leads after scraping
      await fetchLeads();
      return result;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [campaignId, fetchLeads]);

  const analyzeRepo = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await campaignApi.analyzeRepo(campaignId);
      return result;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  const getLeadsByStatus = useCallback((status: LeadStatus) => {
    return leads.filter(l => l.status === status);
  }, [leads]);

  const getKanbanStats = useCallback(() => {
    const stats: Record<LeadStatus, number> = {
      NOVO: 0,
      APRESENTADO: 0,
      NEGOCIACAO: 0,
      FECHADO: 0,
      REJEITADO: 0,
    };
    leads.forEach(l => stats[l.status]++);
    return stats;
  }, [leads]);

  return {
    leads,
    loading,
    error,
    fetchLeads,
    moveLead,
    createLead,
    updateLead,
    triggerOutreach,
    scrape,
    analyzeRepo,
    getLeadsByStatus,
    getKanbanStats,
  };
}

export function useLead(leadId: string) {
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLead = async () => {
      try {
        setLoading(true);
        const data = await leadApi.get(leadId);
        setLead(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (leadId) fetchLead();
  }, [leadId]);

  return { lead, loading, error, refetch: () => leadApi.get(leadId).then(setLead) };
}

export function useCampaignLeads(campaignId: string) {
  return useLeads({ campaignId });
}