/**
 * WhatsApp & Audio Outreach Dispatch Service
 * Evolution API & XTTS v2 Orchestration
 */

export class OutreachService {
  static async dispatchWhatsApp(evoUrl, evoKey, instance, phone, message) {
    const cleanPhone = phone.replace(/\D/g, '');
    if (evoUrl && evoKey) {
      try {
        const res = await fetch(evoUrl + '/message/sendText/' + instance, {
          method: 'POST',
          headers: { 'apikey': evoKey, 'Content-Type': 'application/json' },
          body: JSON.stringify({ number: cleanPhone, text: message })
        });
        if (res.ok) return { success: true, mode: 'api' };
      } catch (err) {
        console.warn('Evolution API indisponível, chaveando para fallback web:', err);
      }
    }
    const waLink = 'https://wa.me/' + cleanPhone + '?text=' + encodeURIComponent(message);
    window.open(waLink, '_blank');
    return { success: true, mode: 'web_direct', link: waLink };
  }
}
