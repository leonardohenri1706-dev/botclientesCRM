'use client';

import { useState, useEffect, useRef } from 'react';
import { MapPin, Search, Loader2, AlertCircle, CheckCircle, XCircle, Settings, Maximize2, Minimize2 } from 'lucide-react';

interface ScrapingMapProps {
  campaignId: string;
  onScrapeComplete?: (result: any) => void;
}

interface Location {
  latitude: number;
  longitude: number;
  radius_meters: number;
}

export function ScrapingMap({ campaignId, onScrapeComplete }: ScrapingMapProps) {
  const [location, setLocation] = useState<Location>({
    latitude: -23.5505,
    longitude: -46.6333,
    radius_meters: 1000,
  });
  const [categories, setCategories] = useState<string[]>(['restaurant', 'store', 'health', 'beauty']);
  const [maxResults, setMaxResults] = useState(100);
  const [isScraping, setIsScraping] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const circleRef = useRef<any>(null);
  const markerRef = useRef<any>(null);

  const AVAILABLE_CATEGORIES = [
    { value: 'restaurant', label: 'Restaurantes', icon: '🍽️' },
    { value: 'store', label: 'Lojas/Comércio', icon: '🏪' },
    { value: 'health', label: 'Saúde/Clínicas', icon: '🏥' },
    { value: 'beauty', label: 'Beleza/Estética', icon: '💇' },
    { value: 'gym', label: 'Academias', icon: '🏋️' },
    { value: 'automotive', label: 'Automotivo', icon: '🚗' },
    { value: 'education', label: 'Educação', icon: '🎓' },
    { value: 'professional_services', label: 'Serviços Profissionais', icon: '💼' },
  ];

  // Load Google Maps API dynamically
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const loadGoogleMaps = async () => {
      const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
      if (!apiKey) {
        console.warn('Google Maps API key not configured');
        return;
      }

      if ((window as any).google?.maps) {
        initMap();
        return;
      }

      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = initMap;
      document.head.appendChild(script);
    };

    loadGoogleMaps();

    return () => {
      if (mapInstance.current) {
        mapInstance.current = null;
      }
    };
  }, []);

  const initMap = () => {
    if (!mapRef.current || mapInstance.current) return;

    const { google } = window as any;
    
    mapInstance.current = new google.maps.Map(mapRef.current, {
      center: { lat: location.latitude, lng: location.longitude },
      zoom: 14,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
      styles: [
        { elementType: 'geometry', stylers: [{ color: '#18181b' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#18181b' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#71717a' }] },
        { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#27272a' }] },
        { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#3f3f46' }] },
        { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#a1a1aa' }] },
        { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0d1b2a' }] },
        { featureType: 'water', elementType: 'labels.text.fill', stylers: [{ color: '#71717a' }] },
        { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#27272a' }] },
        { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#71717a' }] },
      ],
    });

    // Add marker for center
    markerRef.current = new google.maps.Marker({
      position: { lat: location.latitude, lng: location.longitude },
      map: mapInstance.current,
      draggable: true,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#a855f7',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2,
      },
    });

    // Add circle for radius
    circleRef.current = new google.maps.Circle({
      strokeColor: '#a855f7',
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: '#a855f7',
      fillOpacity: 0.1,
      map: mapInstance.current,
      center: { lat: location.latitude, lng: location.longitude },
      radius: location.radius_meters,
      editable: true,
      draggable: true,
    });

    // Update state on marker drag
    google.maps.event.addListener(markerRef.current, 'dragend', (event: any) => {
      const pos = event.latLng.toJSON();
      setLocation(prev => ({ ...prev, latitude: pos.lat, longitude: pos.lng }));
      circleRef.current.setCenter(pos);
    });

    // Update state on circle radius change
    google.maps.event.addListener(circleRef.current, 'radius_changed', () => {
      setLocation(prev => ({ ...prev, radius_meters: Math.round(circleRef.current.getRadius()) }));
    });

    google.maps.event.addListener(circleRef.current, 'center_changed', () => {
      const center = circleRef.current.getCenter();
      if (center) {
        const pos = center.toJSON();
        setLocation(prev => ({ ...prev, latitude: pos.lat, longitude: pos.lng }));
        markerRef.current.setPosition(pos);
      }
    });
  };

  const handleSearchLocation = async (query: string) => {
    if (!query.trim()) return;
    
    try {
      const response = await fetch(
        `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(query)}&key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}`
      );
      const data = await response.json();
      
      if (data.results.length > 0) {
        const { lat, lng } = data.results[0].geometry.location;
        setLocation(prev => ({ ...prev, latitude: lat, longitude: lng }));
        
        if (mapInstance.current) {
          mapInstance.current.setCenter({ lat, lng });
          markerRef.current.setPosition({ lat, lng });
          circleRef.current.setCenter({ lat, lng });
        }
      }
    } catch (err) {
      console.error('Geocoding error:', err);
    }
  };

  const handleScrape = async () => {
    setIsScraping(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch(`/api/campaigns/${campaignId}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign_id: campaignId,
          location,
          categories,
          max_results: maxResults,
        }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Erro ao executar scraping');
      }

      setResults(data);
      onScrapeComplete?.(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsScraping(false);
    }
  };

  const toggleCategory = (category: string) => {
    setCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  return (
    <div className="bg-zinc-900/60 border border-zinc-700 rounded-2xl overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-zinc-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MapPin className="text-violet-400" size={20} />
          <h3 className="font-semibold text-zinc-100">Área de Mineração</h3>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
          aria-label={expanded ? 'Minimizar' : 'Expandir'}
        >
          {expanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
        </button>
      </div>

      {!expanded ? (
        <div className="p-4 text-center text-zinc-500">
          <MapPin size={32} className="mx-auto mb-2 opacity-30" />
          <p>Clique para expandir e configurar área de busca</p>
        </div>
      ) : (
        <div className="flex-1 flex flex-col p-4 overflow-hidden">
          <div className="flex-1 relative min-h-[300px] rounded-xl overflow-hidden border border-zinc-700 mb-4">
            <div ref={mapRef} className="w-full h-full" />
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Localização</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Buscar endereço ou bairro..."
                  className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-zinc-100 placeholder-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchLocation((e.target as HTMLInputElement).value)}
                />
                <button
                  onClick={() => handleSearchLocation((document.querySelector('input[placeholder*="Buscar"]') as HTMLInputElement)?.value || '')}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-medium transition-colors"
                >
                  <Search size={16} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Raio: {location.radius_meters.toLocaleString('pt-BR')}m
                </label>
                <input
                  type="range"
                  min="100"
                  max="50000"
                  step="100"
                  value={location.radius_meters}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    setLocation(prev => ({ ...prev, radius_meters: val }));
                    circleRef.current?.setRadius(val);
                  }}
                  className="w-full h-2 bg-zinc-700 rounded-lg appearance-none accent-violet-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Max Resultados: {maxResults}
                </label>
                <input
                  type="range"
                  min="10"
                  max="500"
                  step="10"
                  value={maxResults}
                  onChange={(e) => setMaxResults(parseInt(e.target.value))}
                  className="w-full h-2 bg-zinc-700 rounded-lg appearance-none accent-violet-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Categorias</label>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_CATEGORIES.map((cat) => (
                  <button
                    key={cat.value}
                    onClick={() => toggleCategory(cat.value)}
                    className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      categories.includes(cat.value)
                        ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/25'
                        : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                    }`}
                  >
                    <span>{cat.icon}</span>
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-rose-950 border border-rose-800 rounded-lg text-rose-400">
                <AlertCircle size={16} />
                <span className="text-sm">{error}</span>
              </div>
            )}

            {results && (
              <div className="flex items-center gap-2 p-3 bg-emerald-950 border border-emerald-800 rounded-lg text-emerald-400">
                <CheckCircle size={16} />
                <span className="text-sm">
                  Encontrados: <strong>{results.total_found}</strong> | 
                  Qualificados: <strong>{results.qualified_leads?.length || 0}</strong> | 
                  Filtrados: <strong>{results.filtered_count}</strong>
                </span>
              </div>
            )}

            <button
              onClick={handleScrape}
              disabled={isScraping || categories.length === 0}
              className="w-full py-3 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              {isScraping ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Minerando...
                </>
              ) : (
                <>
                  <Settings size={18} />
                  Iniciar Mineração
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}