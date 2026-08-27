/**
 * Mining & Qualification Service
 * Multi-Engine (OSM Overpass, Nominatim, Receita Federal CNPJ, Instagram)
 */

export class MiningService {
  static normalizePhone(rawPhone) {
    if (!rawPhone) return null;
    let cleaned = rawPhone.replace(/\D/g, '');
    if (cleaned.startsWith('0')) cleaned = cleaned.substring(1);
    if (cleaned.length === 10 || cleaned.length === 11) cleaned = '55' + cleaned;
    if (cleaned.length === 13 && cleaned.startsWith('55') && cleaned.charAt(4) === '9') {
      return '+' + cleaned;
    }
    return null;
  }

  static async searchOverpass(lat, lon) {
    const query = '[out:json][timeout:25];(node["amenity"~"restaurant|fast_food|cafe|bar|pub"](around:4000,' + lat + ',' + lon + ');node["shop"~"bakery|deli|pastry|supermarket|convenience"](around:4000,' + lat + ',' + lon + ');node["craft"~"caterer"](around:4000,' + lat + ',' + lon + '););out body 35;';
    const res = await fetch('https://overpass-api.de/api/interpreter', { method: 'POST', body: query });
    if (!res.ok) throw new Error('Overpass API indisponível.');
    return await res.json();
  }

  static async fetchCNPJ(cnpj) {
    const clean = cnpj.replace(/\D/g, '').trim();
    if (clean.length !== 14) throw new Error('CNPJ deve conter 14 dígitos numéricos.');
    const res = await fetch('https://brasilapi.com.br/api/cnpj/v1/' + clean);
    if (!res.ok) throw new Error('CNPJ não localizado na Receita Federal.');
    return await res.json();
  }
}
