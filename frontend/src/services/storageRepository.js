/**
 * Data Storage & State Repository
 * Isolates LocalStorage & REST Backend Synchronizer
 */

import { CONFIG } from '../core/config.js';

export class StorageRepository {
  static getLeads() {
    try {
      const raw = localStorage.getItem(CONFIG.STORAGE_KEYS.LEADS);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  static saveLeads(leads) {
    try {
      localStorage.setItem(CONFIG.STORAGE_KEYS.LEADS, JSON.stringify(leads));
    } catch (e) {
      console.error('Falha ao persistir leads no storage:', e);
    }
  }

  static getCampaigns() {
    try {
      const raw = localStorage.getItem(CONFIG.STORAGE_KEYS.CAMPAIGNS);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  static saveCampaigns(campaigns) {
    try {
      localStorage.setItem(CONFIG.STORAGE_KEYS.CAMPAIGNS, JSON.stringify(campaigns));
    } catch (e) {
      console.error('Falha ao persistir campanhas:', e);
    }
  }
}
