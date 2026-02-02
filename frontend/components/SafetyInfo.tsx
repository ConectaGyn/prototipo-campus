
import React, { useMemo } from 'react';
import { PhoneIcon, ShieldAlertIcon, FlameIcon, ActivityIcon, SunIcon, CloudRainIcon, MapPinIcon, BuildingIcon, ChevronRightIcon, AlertTriangleIcon } from './Icons.tsx';
import SpeakButton from './SpeakButton.tsx';
import { calculateDistance, checkRouteRisk } from '@utils/geoUtils';
import type { SensorData } from '../types.ts';
import { SAFE_LOCATIONS, type SafeLocation } from '@utils/safeLocations';

interface SafetyInfoProps {
  userCoords: { lat: number; lon: number } | null;
  sensors?: SensorData[];
}

const EmergencyCard: React.FC<{ number: string; label: string; icon: React.ReactNode; color: string }> = ({ number, label, icon, color }) => (
  <a 
    href={`tel:${number}`} 
    className={`flex flex-col items-center justify-center p-6 rounded-xl border-2 shadow-md transition-transform hover:scale-105 focus:outline-none focus:ring-4 ${color} bg-white dark:bg-slate-800`}
    aria-label={`Ligar para ${label}, número ${number}`}
  >
    <div className="mb-3 p-3 rounded-full bg-opacity-10 bg-current">
      {icon}
    </div>
    <span className="text-3xl font-bold mb-1 text-slate-800 dark:text-white">{number}</span>
    <span className="text-sm font-semibold uppercase tracking-wide opacity-80 text-slate-600 dark:text-slate-300">{label}</span>
  </a>
);

const SafePlaceCard: React.FC<{ 
    name: string; 
    type: string; 
    address: string; 
    icon: React.ReactNode; 
    userCoords: { lat: number; lon: number } | null;
    distance?: number;
    hasRouteRisk?: boolean;
}> = ({ name, type, address, icon, userCoords, distance, hasRouteRisk }) => {
  
  // Monta a URL do Google Maps para rotas
  const getMapUrl = () => {
    const destination = encodeURIComponent(`${address}, Goiânia - GO`);
    let url = `https://www.google.com/maps/dir/?api=1&destination=${destination}`;
    
    if (userCoords) {
      url += `&origin=${userCoords.lat},${userCoords.lon}`;
    }
    
    return url;
  };

  return (
    <a 
      href={getMapUrl()}
      target="_blank"
      rel="noopener noreferrer"
      className={`group flex items-start gap-4 p-4 rounded-lg border transition-all cursor-pointer relative ${
        hasRouteRisk 
          ? 'border-orange-400 bg-orange-50 dark:bg-orange-900/10 dark:border-orange-700/50'
          : 'border-slate-100 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-700/70'
      }`}
      title={hasRouteRisk ? "Atenção: Rota cruza área de risco" : "Clique para abrir a rota no mapa"}
    >
      <div className={`p-2 rounded-lg shrink-0 group-hover:scale-110 transition-transform ${hasRouteRisk ? 'bg-orange-100 text-orange-600' : 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400'}`}>
        {icon}
      </div>
      <div className="flex-grow min-w-0">
        <div className="flex justify-between items-start">
          <h4 className="font-bold text-slate-800 dark:text-slate-200 truncate group-hover:text-cyan-700 dark:group-hover:text-cyan-400 transition-colors pr-6">{name}</h4>
          <ChevronRightIcon className="w-5 h-5 text-slate-400 group-hover:text-cyan-500 opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0 absolute top-4 right-4" />
        </div>
        <div className="flex flex-wrap gap-2 justify-between items-center mb-1">
            <p className="text-xs font-semibold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider">{type}</p>
            <div className="flex gap-2">
                {hasRouteRisk && (
                    <span className="flex items-center gap-1 text-xs font-bold text-orange-600 bg-orange-100 px-2 py-0.5 rounded-full border border-orange-200">
                        <AlertTriangleIcon className="w-3 h-3" />
                        Rota de Risco
                    </span>
                )}
                {distance !== undefined && (
                    <span className="text-xs font-bold text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-700 px-2 py-0.5 rounded-full shadow-sm border border-slate-200 dark:border-slate-600">
                        {distance < 1 ? `${Math.round(distance * 1000)} m` : `${distance.toFixed(1)} km`}
                    </span>
                )}
            </div>
        </div>
        <div className="flex items-start gap-1 text-sm text-slate-600 dark:text-slate-400">
          <MapPinIcon className="w-4 h-4 mt-0.5 shrink-0 opacity-70" />
          <span className="underline decoration-dotted decoration-slate-400 hover:decoration-cyan-500 line-clamp-2">{address}</span>
        </div>
        {hasRouteRisk && (
            <p className="mt-2 text-xs text-orange-700 dark:text-orange-400 font-medium">
                ⚠️ O trajeto direto passa próximo a áreas de Risco Alto. Verifique o mapa.
            </p>
        )}
      </div>
    </a>
  );
};


const getIconForLocation = (icon: SafeLocation['icon']) => {
  switch (icon) {
    case 'fire':
      return <FlameIcon className="w-6 h-6" />;
    case 'support':
      return <BuildingIcon className="w-6 h-6" />;
    case 'security':
      return <ShieldAlertIcon className="w-6 h-6" />;
    case 'health':
    default:
      return <ActivityIcon className="w-6 h-6" />;
  }
};

const SafetyInfo: React.FC<SafetyInfoProps> = ({ userCoords, sensors = [] }) => {
  const generalAdvice = "Em caso de emergência, mantenha a calma e ligue imediatamente para os serviços especializados.";
  
  

  // Identifica sensores de risco Alto
  const highRiskSensors = useMemo(() => 
    sensors.filter(
      s => s.alert?.level === 'Alto' || s.alert?.level === 'Muito Alto'
    ),
  [sensors]);

  // Ordena e Processa os locais
  const processedLocations = useMemo(() => {
    if (!userCoords) return SAFE_LOCATIONS.map(p => ({ ...p, icon: getIconForLocation(p.icon), distance: undefined, hasRouteRisk: false }));

    return SAFE_LOCATIONS
        .map(place => {
            const distance = calculateDistance(userCoords.lat, userCoords.lon, place.coords.lat, place.coords.lon);
            
            // Verifica se a rota cruza algum sensor de risco alto (limite de 2km)
            let hasRouteRisk = false;
            for (const sensor of highRiskSensors) {
                if (checkRouteRisk(userCoords, place.coords, sensor.coords, 2.0)) {
                    hasRouteRisk = true;
                    break;
                }
            }
            
            return { ...place, icon: getIconForLocation(place.icon), distance, hasRouteRisk };
        })
        .sort((a, b) => {
            // Prioridade 1: Rotas Seguras (sem risco)
            if (a.hasRouteRisk !== b.hasRouteRisk) {
                return a.hasRouteRisk ? 1 : -1; // Se A tem risco, vai pro final
            }
            // Prioridade 2: Distância
            return a.distance - b.distance;
        });
  }, [userCoords, highRiskSensors]);

  return (
    <div className="space-y-8">
      
      {/* Seção de Telefones de Emergência */}
      <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg" aria-labelledby="emergency-title">
        <div className="flex justify-between items-start mb-6">
          <h2 id="emergency-title" className="text-2xl font-bold text-red-600 dark:text-red-400 flex items-center gap-2">
            <PhoneIcon className="w-7 h-7" />
            Telefones de Emergência
          </h2>
          <SpeakButton text="Telefones de emergência: Bombeiros 1 9 3. Defesa Civil 1 9 9. Samu 1 9 2. Polícia Militar 1 9 0." label="Ouvir números de emergência" />
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <EmergencyCard 
            number="193" 
            label="Bombeiros" 
            icon={<FlameIcon className="w-8 h-8 text-red-600" />} 
            color="border-red-500 hover:border-red-600 focus:ring-red-200"
          />
          <EmergencyCard 
            number="199" 
            label="Defesa Civil" 
            icon={<ShieldAlertIcon className="w-8 h-8 text-orange-500" />} 
            color="border-orange-500 hover:border-orange-600 focus:ring-orange-200"
          />
          <EmergencyCard 
            number="192" 
            label="SAMU" 
            icon={<ActivityIcon className="w-8 h-8 text-red-500" />} 
            color="border-red-400 hover:border-red-500 focus:ring-red-100"
          />
          <EmergencyCard 
            number="190" 
            label="Polícia Militar" 
            icon={<ShieldAlertIcon className="w-8 h-8 text-blue-600" />} 
            color="border-blue-500 hover:border-blue-600 focus:ring-blue-200"
          />
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-8">
          {/* Seção de Recomendações */}
          <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg h-full" aria-labelledby="guidelines-title">
            <div className="flex justify-between items-center mb-6">
              <h2 id="guidelines-title" className="text-xl font-semibold text-slate-600 dark:text-slate-300">Recomendações de Segurança</h2>
            </div>

            <div className="space-y-6">
              {/* Card Chuvas */}
              <div className="bg-slate-50 dark:bg-slate-700/30 p-5 rounded-lg border border-slate-200 dark:border-slate-700/50">
                <h3 className="text-lg font-bold text-cyan-700 dark:text-cyan-400 mb-4 flex items-center gap-2">
                  <CloudRainIcon className="w-6 h-6" />
                  Chuvas Fortes e Vendavais
                </h3>
                <ul className="space-y-3 text-slate-700 dark:text-slate-300 list-disc list-inside marker:text-cyan-500 text-sm">
                  <li>Não se abrigue debaixo de árvores.</li>
                  <li>Evite estacionar veículos próximos a torres e placas.</li>
                  <li>Se possível, desligue aparelhos elétricos.</li>
                  <li>Nunca atravesse ruas alagadas.</li>
                </ul>
              </div>

              {/* Card Calor */}
              <div className="bg-slate-50 dark:bg-slate-700/30 p-5 rounded-lg border border-slate-200 dark:border-slate-700/50">
                <h3 className="text-lg font-bold text-orange-600 dark:text-orange-400 mb-4 flex items-center gap-2">
                  <SunIcon className="w-6 h-6" />
                  Calor Extremo e Baixa Umidade
                </h3>
                <ul className="space-y-3 text-slate-700 dark:text-slate-300 list-disc list-inside marker:text-orange-500 text-sm">
                  <li>Beba bastante água, mesmo sem sentir sede.</li>
                  <li>Evite exercícios ao ar livre entre 10h e 16h.</li>
                  <li>Use protetor solar e umidifique ambientes.</li>
                  <li>Evite queimadas.</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Seção de Locais Seguros */}
          <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg h-full" aria-labelledby="safe-places-title">
             <div className="flex justify-between items-center mb-6">
              <h2 id="safe-places-title" className="text-xl font-semibold text-slate-600 dark:text-slate-300 flex items-center gap-2">
                  <ShieldAlertIcon className="w-6 h-6 text-cyan-600 dark:text-cyan-400" />
                  Pontos de Apoio Mais Próximos
              </h2>
              <SpeakButton text="Lista de locais seguros, priorizando rotas que evitam áreas de risco." label="Ouvir lista de locais seguros" />
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {processedLocations.map((place, idx) => (
                    <SafePlaceCard 
                        key={idx}
                        name={place.name}
                        type={place.type}
                        address={place.address}
                        icon={place.icon}
                        userCoords={userCoords}
                        distance={place.distance}
                        hasRouteRisk={place.hasRouteRisk}
                    />
                ))}
            </div>
            <p className="mt-6 text-xs text-slate-500 dark:text-slate-400">
                * A priorização considera apenas riscos já calculados no mapa.
            </p>
          </section>
      </div>
      
      <div className="text-center text-sm text-slate-500 dark:text-slate-400 italic">
        {generalAdvice}
      </div>
    </div>
  );
};

export default SafetyInfo;
