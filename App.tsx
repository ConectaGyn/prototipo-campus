
import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { WeatherData, RiskAlert, SensorData, CurrentWeather, BackendSensorReading } from './types.ts';
import { getWeatherData, getLocationName } from './services/weatherService.ts';
import { calculateSensorRisk, sensorLocations } from './services/sensorService.ts';
import { fetchLatestSensors } from './services/sensorApi.ts';
import { calculateDistance } from './utils/geoUtils.ts';
import Header from './components/Header.tsx';
import WeatherCard from './components/WeatherCard.tsx';
import AlertCard from './components/AlertCard.tsx';
import LoadingSpinner from './components/LoadingSpinner.tsx';
import SensorCarousel from './components/SensorCarousel.tsx';
import Tabs from './components/Tabs.tsx';
import MapComponent from './components/MapComponent.tsx';
import SafetyInfo from './components/SafetyInfo.tsx';
import { CheckCircleIcon, AlertTriangleIcon, MenuIcon, XIcon, WeatherIcon, Volume2Icon, VolumeXIcon, RefreshCwIcon, EyeIcon, EyeOffIcon, MapPinIcon } from './components/Icons.tsx';
import { useTheme } from './hooks/useTheme.ts';

// Import necessario para o componente ThemeToggle dentro do App
import ThemeToggle from './components/ThemeToggle.tsx';
// Import ChevronLeftIcon
import { ChevronLeftIcon } from './components/Icons.tsx';

const GOIANIA_COORDS = {
  lat: -16.6869,
  lon: -49.2648,
};

const SETOR_UNIVERSITARIO_COORDS = {
  lat: -16.6792,
  lon: -49.2538,
};

const offsetCoords = (base: { lat: number; lon: number }, seed: number) => {
  const hash = Math.sin(seed * 9973) * 10000;
  const jitterLat = ((hash % 1) - 0.5) * 0.006;
  const jitterLon = (((hash * 1.3) % 1) - 0.5) * 0.006;
  return {
    lat: base.lat + jitterLat,
    lon: base.lon + jitterLon,
  };
};

const App: React.FC = () => {
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [displayedCurrentWeather, setDisplayedCurrentWeather] = useState<CurrentWeather | null>(null);

  const [sensorData, setSensorData] = useState<SensorData[]>([]);
  const [currentCoords, setCurrentCoords] = useState<{ lat: number, lon: number } | null>(null);
  const [backendReadings, setBackendReadings] = useState<BackendSensorReading[] | null>(null);
  const [riskAlert, setRiskAlert] = useState<RiskAlert | null>(null);
  const [userWeatherReport, setUserWeatherReport] = useState<string | null>(null);
  const [userReportNotice, setUserReportNotice] = useState<string | null>(null);
  const [showUserReportMobile, setShowUserReportMobile] = useState(true);
  const [isMapModalOpen, setIsMapModalOpen] = useState(false);
  const [locationName, setLocationName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState(0); // Controle manual de abas para gerenciar layout mobile/desktop
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showMobileDetails, setShowMobileDetails] = useState(true); // Controle de visibilidade dos overlays mobile

  const [isSoundEnabled, setIsSoundEnabled] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('soundEnabled');
      return stored === null ? true : stored === 'true';
    }
    return true;
  });

  const isFetchingRef = useRef(false);
  const reportResetTimeout = useRef<number | null>(null);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    localStorage.setItem('soundEnabled', String(isSoundEnabled));
  }, [isSoundEnabled]);

  const toggleSound = useCallback(() => {
    setIsSoundEnabled(prev => !prev);
  }, []);

  const openMapModal = useCallback(() => setIsMapModalOpen(true), []);
  const closeMapModal = useCallback(() => setIsMapModalOpen(false), []);

  const handleUserReport = useCallback((choice: string) => {
    if (reportResetTimeout.current) {
      clearTimeout(reportResetTimeout.current);
    }
    setUserWeatherReport(choice);
    setUserReportNotice(`Aviso registrado: ${choice}. Obrigado pelo retorno.`);
    reportResetTimeout.current = window.setTimeout(() => {
      setUserWeatherReport(null);
      setUserReportNotice(null);
    }, 2000);
  }, []);

  const calculateRiskLevel = useCallback((current: CurrentWeather, hourly: any[]): RiskAlert => {
    const windKmh = current.wind_speed;
    const humidity = current.humidity;
    const pop = hourly[0]?.pop ?? 0;
    const rain1h = current.rain?.['1h'] ?? 0;
    const highReasons = [];
    if (windKmh > 60) highReasons.push(`vento ${Math.round(windKmh)} km/h (>60)`);
    if (rain1h > 5) highReasons.push(`chuva 1h ${rain1h.toFixed(1)} mm (>5)`);
    const moderateReasons = [];
    if (windKmh > 50) moderateReasons.push(`vento ${Math.round(windKmh)} km/h (>50)`);
    if (humidity > 95) moderateReasons.push(`umidade ${Math.round(humidity)}% (>95)`);
    if (pop > 0.9) moderateReasons.push(`prob. chuva ${Math.round(pop * 100)}% (>90%)`);

    if (windKmh > 60 || rain1h > 5) {
      return {
        level: 'Alto',
        message: `Risco de ventos muito fortes ou chuva intensa. Motivos: ${highReasons.join("; ")}.`,
        color: 'bg-red-500 border-red-700',
        icon: <AlertTriangleIcon className="w-8 h-8 text-white" />,
      };
    }
    if (windKmh > 50 || humidity > 95 || pop > 0.9) {
      return {
        level: 'Moderado',
        message: `Ventos fortes, alta umidade ou alta probabilidade de chuva. Motivos: ${moderateReasons.join("; ")}.`,
        color: 'bg-yellow-500 border-yellow-700',
        icon: <AlertTriangleIcon className="w-8 h-8 text-white" />,
      };
    }
    return {
      level: 'Baixo',
      message: 'Condições climaticas estáveis. Sem riscos iminentes.',
      color: 'bg-green-600 border-green-800',
      icon: <CheckCircleIcon className="w-8 h-8 text-white" />,
    };
  }, []);

  const formatLocationList = (sensors: SensorData[]) => {
    const names = sensors.map(s => s.location);
    if (names.length === 0) return '';
    if (names.length === 1) return names[0];
    const last = names.pop();
    return `${names.join(', ')} e ${last}`;
  };

  useEffect(() => {
    if (!weatherData || !displayedCurrentWeather) return;

    const apiRisk = calculateRiskLevel(displayedCurrentWeather, weatherData.hourly);

    const highRiskSensors = sensorData.filter(s => s.alert?.level === 'Alto');
    const moderateRiskSensors = sensorData.filter(s => s.alert?.level === 'Moderado');

    if (highRiskSensors.length > 0 || moderateRiskSensors.length > 0) {
      const messages: string[] = [];

      if (highRiskSensors.length > 0) {
        messages.push(`Risco Alto em: ${formatLocationList(highRiskSensors)}`);
      }

      if (moderateRiskSensors.length > 0) {
        messages.push(`Risco Moderado em: ${formatLocationList(moderateRiskSensors)}`);
      }

      const combinedMessage = messages.join('. ');

      const globalLevel = highRiskSensors.length > 0 ? 'Alto' : 'Moderado';
      const color = globalLevel === 'Alto' ? 'bg-red-500 border-red-700' : 'bg-yellow-500 border-yellow-700';

      setRiskAlert({
        level: globalLevel,
        message: combinedMessage,
        color: color,
        icon: <AlertTriangleIcon className="w-8 h-8 text-white" />,
      });
    } else {
      setRiskAlert(apiRisk);
    }
  }, [weatherData, displayedCurrentWeather, sensorData, calculateRiskLevel]);

  const buildSensorsFromBackend = useCallback((
    readings: BackendSensorReading[] | null,
    userCoords: { lat: number; lon: number } | null
  ) => {
    if (!readings || readings.length === 0) return [];

    const locationsById = new Map(sensorLocations.map(location => [location.id, location]));
    const locationsByName = new Map(sensorLocations.map(location => [location.name, location]));

    const sensors = readings.map((reading, index) => {
      const temp = reading.temp;
      const humidity = reading.humidity;
      const wind_speed = reading.wind_speed ?? 0;

      if (temp === null || temp === undefined || humidity === null || humidity === undefined) {
        return null;
      }

      const matchedLocation = (reading.sensorId ? locationsById.get(reading.sensorId) : null)
        || (reading.location ? locationsByName.get(reading.location) : null);

      const coords = matchedLocation?.coords || offsetCoords(SETOR_UNIVERSITARIO_COORDS, index + 1);

      const calculatedAlert = calculateSensorRisk({ temp, humidity, wind_speed });
      const alert = calculatedAlert.level === 'Nenhum' ? undefined : calculatedAlert;

      return {
        id: matchedLocation?.id || reading.sensorId || `sensor-${index}`,
        location: matchedLocation?.name || reading.location || 'Sensor real (Setor Universitario)',
        coords,
        temp,
        humidity,
        wind_speed,
        level: reading.level ?? null,
        timestamp: reading.timestamp ?? null,
        ...(alert && { alert }),
      };
    }).filter(Boolean) as SensorData[];

    if (!userCoords) return sensors;

    return sensors.sort((a, b) => {
      const distA = calculateDistance(userCoords.lat, userCoords.lon, a.coords.lat, a.coords.lon);
      const distB = calculateDistance(userCoords.lat, userCoords.lon, b.coords.lat, b.coords.lon);
      return distA - distB;
    });
  }, []);

  const fetchWeatherAndLocation = useCallback(async (lat: number, lon: number, locationError: string | null) => {
    try {
      const [fetchedWeatherData, fetchedLocationName] = await Promise.all([
        getWeatherData(lat, lon),
        getLocationName(lat, lon),
      ]);

      setWeatherData(fetchedWeatherData);
      setDisplayedCurrentWeather(fetchedWeatherData.current);

      const initialSensors = buildSensorsFromBackend(
        backendReadings,
        { lat, lon }
      );
      setSensorData(initialSensors);

      setCurrentCoords({ lat, lon });
      setLocationName(fetchedLocationName);

      if (!locationError) setError(null);
      else setError(locationError);

    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : 'Um erro inesperado ocorreu.';
      setError(message);
      setWeatherData(null);
      setDisplayedCurrentWeather(null);
      setSensorData([]);
      setCurrentCoords(null);
    }
  }, [buildSensorsFromBackend, backendReadings]);

  const updateUserLocationData = useCallback(async (isInitialOrManual: boolean) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    if (isInitialOrManual) {
      setLoading(true);
      setError(null);
      setLocationName('');
    }
    setIsRefreshing(true);

    const onFetchComplete = () => {
      if (isInitialOrManual) setLoading(false);
      setIsRefreshing(false);
      isFetchingRef.current = false;
    };

    const fetchByCoords = async (lat: number, lon: number, err: string | null = null) => {
      await fetchWeatherAndLocation(lat, lon, err);
      onFetchComplete();
    };

    if (navigator.geolocation) {
      let resolved = false;
      const fallbackTimer = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          fetchByCoords(GOIANIA_COORDS.lat, GOIANIA_COORDS.lon, "Nao foi possivel obter sua localizacao (timeout). Mostrando dados para Goiania.");
        }
      }, 8000);

      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (resolved) return;
          resolved = true;
          clearTimeout(fallbackTimer);
          fetchByCoords(position.coords.latitude, position.coords.longitude);
        },
        () => {
          if (resolved) return;
          resolved = true;
          clearTimeout(fallbackTimer);
          fetchByCoords(GOIANIA_COORDS.lat, GOIANIA_COORDS.lon, "Nao foi possivel obter sua localizacao. Mostrando dados para Goiania.");
        },
        { enableHighAccuracy: true, timeout: 7000, maximumAge: 30000 }
      );
    } else {
      fetchByCoords(GOIANIA_COORDS.lat, GOIANIA_COORDS.lon, "Geolocalizacao nao e suportada. Mostrando dados para Goiania.");
    }
  }, [fetchWeatherAndLocation]);

  const handleRefresh = useCallback(() => {
    updateUserLocationData(true);
  }, [updateUserLocationData]);

  useEffect(() => {
    updateUserLocationData(true);
  }, []);

  useEffect(() => {
    const intervalId = setInterval(() => {
      updateUserLocationData(false);
    }, 300000);

    return () => clearInterval(intervalId);
  }, [updateUserLocationData]);

  useEffect(() => {
    const newSensors = buildSensorsFromBackend(
      backendReadings,
      currentCoords
    );
    setSensorData(newSensors);
  }, [backendReadings, currentCoords, buildSensorsFromBackend]);

  useEffect(() => {
    let isActive = true;
    const pollBackend = async () => {
      try {
        const data = await fetchLatestSensors();
        if (!isActive) return;
        if (data.error) {
          setBackendReadings(null);
          return;
        }
        setBackendReadings(Array.isArray(data.sensors) ? data.sensors : []);
      } catch (err) {
        if (!isActive) return;
        setBackendReadings(null);
      }
    };

    pollBackend();
    const intervalId = setInterval(pollBackend, 10000);
    return () => {
      isActive = false;
      clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (reportResetTimeout.current) {
        clearTimeout(reportResetTimeout.current);
      }
    };
  }, []);

  // Conteudo das abas para renderizacao Desktop
  const tabs = weatherData && displayedCurrentWeather ? [
    {
      label: 'Monitoramento',
      content: (
        <div className="space-y-6 lg:space-y-8">
          {riskAlert && <AlertCard alert={riskAlert} soundEnabled={isSoundEnabled} />}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
            <WeatherCard current={displayedCurrentWeather} precipitationProbability={weatherData?.hourly?.[0]?.pop} />
            <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg flex flex-col h-full" aria-labelledby="map-title">
              <div className="flex items-center justify-between mb-4 gap-3">
                <h2 id="map-title" className="text-xl font-semibold text-slate-600 dark:text-slate-300">Mapa de Sensores</h2>
                <button
                  type="button"
                  onClick={() => setIsMapModalOpen(true)}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-semibold text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-900/30 shadow-sm hover:bg-cyan-100 dark:hover:bg-cyan-900/50 transition-colors"
                  aria-label="Abrir mapa em tela cheia"
                >
                  <MapPinIcon className="w-4 h-4" />
                  Abrir
                </button>
              </div>
              <div className="flex-grow min-h-[300px] rounded-lg overflow-hidden relative z-0">
                <MapComponent sensors={sensorData} className="h-full w-full absolute inset-0" userLocation={currentCoords} />
              </div>
            </section>
          </div>
          <section className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-lg" aria-labelledby="user-report-title">
            <div className="flex items-center justify-between gap-4 mb-4">
              <h3 id="user-report-title" className="text-lg font-semibold text-slate-700 dark:text-slate-200">Como está o tempo aí?</h3>
              {userReportNotice && (
                <span className="text-sm text-cyan-700 dark:text-cyan-300">{userReportNotice}</span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                aria-pressed={userWeatherReport === 'Tudo bem'}
                onClick={() => handleUserReport('Tudo bem')}
                className={`p-4 rounded-xl border text-sm font-semibold transition shadow-sm ${userWeatherReport === 'Tudo bem'
                    ? 'bg-green-600 text-white border-green-700'
                    : 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800'
                  }`}
              >
                <span className="inline-flex items-center justify-center gap-2">✅ Tudo bem</span>
              </button>
              <button
                type="button"
                aria-pressed={userWeatherReport === 'Atencao'}
                onClick={() => handleUserReport('Atencao')}
                className={`p-4 rounded-xl border text-sm font-semibold transition shadow-sm ${userWeatherReport === 'Atencao'
                    ? 'bg-amber-500 text-white border-amber-600'
                    : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800'
                  }`}
              >
                <span className="inline-flex items-center justify-center gap-2">⚠️ Atenção</span>
              </button>
              <button
                type="button"
                aria-pressed={userWeatherReport === 'Perigo'}
                onClick={() => handleUserReport('Perigo')}
                className={`p-4 rounded-xl border text-sm font-semibold transition shadow-sm ${userWeatherReport === 'Perigo'
                    ? 'bg-red-600 text-white border-red-700'
                    : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800'
                  }`}
              >
                <span className="inline-flex items-center justify-center gap-2">🚨 Perigo</span>
              </button>
            </div>
          </section>
          <SensorCarousel sensors={sensorData} />
        </div>
      )
    },
    {
      label: 'Segurança',
      content: <SafetyInfo userCoords={currentCoords} sensors={sensorData} />
    },
  ] : [];

  // --- MOBILE UI COMPONENTS ---
  const MobileTopOverlay = () => {
    if (!displayedCurrentWeather || !riskAlert) return null;

    // --- MODO COMPACTO / ESCONDIDO ---
    if (!showMobileDetails) {
      return (
        <div className="absolute top-0 left-0 right-0 z-20 px-3 py-2 pointer-events-none flex flex-col items-center gap-2">
          {/* Floating Compact Pill */}
          <div className="pointer-events-auto flex items-center gap-2 p-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md rounded-full shadow-xl border border-slate-200/50 dark:border-slate-700/50 animate-in slide-in-from-top duration-300">
            <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${riskAlert.level === 'Baixo'
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : riskAlert.level === 'Alto'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 animate-pulse'
                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
              }`}>
              {riskAlert.level === 'Baixo' ? <CheckCircleIcon className="w-3 h-3" /> : <AlertTriangleIcon className="w-3 h-3" />}
              <span>{riskAlert.level === 'Baixo' ? 'Normal' : riskAlert.level}</span>
            </div>
            <div className="w-px h-4 bg-slate-300 dark:bg-slate-600 mx-1"></div>
            <div className="flex items-center gap-1 text-slate-800 dark:text-white text-sm font-bold pr-1">
              <span className="text-xs text-slate-500 dark:text-slate-400 font-normal">Agora:</span>
              {displayedCurrentWeather.temp.toFixed(0)}°C
            </div>
            <button
              onClick={() => setShowMobileDetails(true)}
              className="ml-1 p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-cyan-600 dark:text-cyan-400 transition-colors"
              aria-label="Mostrar detalhes"
            >
              <EyeIcon className="w-4 h-4" />
            </button>
          </div>

          {/* Floating Compact Action Bar (Menu + Configs when simplified) */}
          <div className="pointer-events-auto flex gap-2">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-full shadow-lg backdrop-blur-sm transition-colors bg-amber-100/90 text-amber-600"
              aria-label="Atualizar dados"
            >
              <RefreshCwIcon className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={toggleSound} className="p-2 rounded-full bg-white/90 dark:bg-slate-900/90 shadow-lg backdrop-blur-sm text-slate-500 dark:text-slate-400">
              {isSoundEnabled ? <Volume2Icon className="w-4 h-4" /> : <VolumeXIcon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      );
    }

    // --- MODO EXPANDIDO (PADRAO) ---
    return (
      <div className="absolute top-0 left-0 right-0 z-20 px-3 py-2 pointer-events-none">
        <div className="pointer-events-auto bg-white/90 dark:bg-slate-900/90 backdrop-blur-md rounded-2xl shadow-lg border border-slate-200/50 dark:border-slate-700/50 overflow-hidden">

          {/* Compact Header Row */}
          <div className="flex justify-between items-center p-3 border-b border-slate-100 dark:border-slate-800">
            <h1 className="text-lg font-bold text-slate-800 dark:text-white tracking-tight">ClimaGyn</h1>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setShowMobileDetails(false)}
                className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                aria-label="Ocultar detalhes e ver mapa"
              >
                <EyeOffIcon className="w-4 h-4" />
              </button>
              <div className="w-px h-4 bg-slate-300 dark:bg-slate-600 mx-1"></div>
              <button onClick={toggleSound} className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                {isSoundEnabled ? <Volume2Icon className="w-4 h-4" /> : <VolumeXIcon className="w-4 h-4" />}
              </button>
              <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
              <button onClick={handleRefresh} disabled={isRefreshing} className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                <RefreshCwIcon className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Info Content Row */}
          <div className="p-3 flex justify-between items-center gap-3">

            {/* Weather Left */}
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <WeatherIcon iconCode={displayedCurrentWeather.weather[0].icon} className="w-10 h-10 text-cyan-600 dark:text-cyan-400" />
                <span className="text-[10px] text-slate-500 dark:text-slate-400 capitalize truncate max-w-[70px]">{displayedCurrentWeather.weather[0].description}</span>
              </div>
              <div>
                <div className="text-3xl font-bold text-slate-800 dark:text-white leading-none">
                  {displayedCurrentWeather.temp.toFixed(0)}°C
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Sens: {displayedCurrentWeather.feels_like.toFixed(0)}
                </div>
              </div>
            </div>

            {/* Risk & Details Right */}
            <div className="flex flex-col items-end gap-1.5 min-w-[110px]">
              <div className={`px-2 py-1 rounded-full text-xs font-bold border flex items-center gap-1 ${riskAlert.level === 'Baixo'
                  ? 'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800'
                  : riskAlert.level === 'Alto'
                    ? 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800 animate-pulse'
                    : 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800'
                }`}>
                {riskAlert.level === 'Baixo' ? <CheckCircleIcon className="w-3 h-3" /> : <AlertTriangleIcon className="w-3 h-3" />}
                {riskAlert.level === 'Baixo' ? 'Normal' : `Risco ${riskAlert.level}`}
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-600 dark:text-slate-300">
                <div className="flex flex-col items-end">
                  <span className="font-bold">{Math.round(displayedCurrentWeather.wind_speed)} km/h</span>
                  <span className="text-[10px] opacity-70">Vento</span>
                </div>
                <div className="w-px h-6 bg-slate-200 dark:bg-slate-700"></div>
                <div className="flex flex-col items-end">
                  <span className="font-bold">{displayedCurrentWeather.humidity}%</span>
                  <span className="text-[10px] opacity-70">Umid</span>
                </div>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-100 dark:border-slate-800 px-3 pb-3">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Como está o tempo aí?</span>
              <button
                className="text-xs text-cyan-700 dark:text-cyan-300 font-semibold"
                onClick={() => setShowUserReportMobile(prev => !prev)}
              >
                {showUserReportMobile ? 'Esconder' : 'Mostrar'}
              </button>
            </div>
            {userReportNotice && (
              <div className="mb-2 text-xs text-cyan-700 dark:text-cyan-300">{userReportNotice}</div>
            )}
            {showUserReportMobile && (
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  aria-pressed={userWeatherReport === 'Tudo bem'}
                  onClick={() => handleUserReport('Tudo bem')}
                  className={`p-2 rounded-lg border text-xs font-semibold transition ${userWeatherReport === 'Tudo bem'
                      ? 'bg-green-600 text-white border-green-700'
                      : 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800'
                    }`}
                >
                  <span className="inline-flex items-center justify-center gap-1.5">✅ Tudo bem</span>
                </button>
                <button
                  type="button"
                  aria-pressed={userWeatherReport === 'Atencao'}
                  onClick={() => handleUserReport('Atencao')}
                  className={`p-2 rounded-lg border text-xs font-semibold transition ${userWeatherReport === 'Atencao'
                      ? 'bg-amber-500 text-white border-amber-600'
                      : 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800'
                    }`}
                >
                  <span className="inline-flex items-center justify-center gap-1.5">⚠️ Atenção</span>
                </button>
                <button
                  type="button"
                  aria-pressed={userWeatherReport === 'Perigo'}
                  onClick={() => handleUserReport('Perigo')}
                  className={`p-2 rounded-lg border text-xs font-semibold transition ${userWeatherReport === 'Perigo'
                      ? 'bg-red-600 text-white border-red-700'
                      : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800'
                    }`}
                >
                  <span className="inline-flex items-center justify-center gap-1.5">🚨 Perigo</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const MobileBottomOverlay = () => {
    // Se estiver no modo compacto, esconde o carrossel para dar visao total do mapa
    if (!showMobileDetails) return null;

    return (
      <div className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none flex flex-col justify-end">
        <div className="bg-gradient-to-t from-white/95 via-white/90 to-transparent dark:from-slate-900/95 dark:via-slate-900/90 pt-12 pb-4 px-4 pointer-events-auto animate-in slide-in-from-bottom duration-300">
          <SensorCarousel sensors={sensorData} />
        </div>
      </div>
    );
  };

  const MobileNavButton = () => (
    <button
      onClick={() => setIsMobileMenuOpen(true)}
      className="absolute bottom-6 right-6 z-30 p-4 rounded-full bg-cyan-600 text-white shadow-xl shadow-cyan-600/40 hover:bg-cyan-700 focus:outline-none focus:ring-4 focus:ring-cyan-300 transition-transform active:scale-95 md:hidden"
      aria-label="Abrir menu"
    >
      <MenuIcon className="w-6 h-6" />
    </button>
  );

  const MobileMenuModal = () => (
    isMobileMenuOpen ? (
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-end justify-center md:hidden animate-in fade-in duration-200">
        <div className="bg-white dark:bg-slate-800 w-full rounded-t-2xl p-6 space-y-4 animate-in slide-in-from-bottom duration-300">
          <div className="flex justify-between items-center mb-4 border-b border-slate-100 dark:border-slate-700 pb-2">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white">Navegacao</h3>
            <button onClick={() => setIsMobileMenuOpen(false)} className="p-2 text-slate-500"><XIcon className="w-6 h-6" /></button>
          </div>

          <button
            onClick={() => { setActiveTab(0); setIsMobileMenuOpen(false); }}
            className={`w-full p-4 rounded-xl flex items-center gap-3 font-bold text-lg ${activeTab === 0 ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400' : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}
          >
            <span></span> Monitoramento (Mapa)
          </button>
          <button
            onClick={() => { setActiveTab(1); setIsMobileMenuOpen(false); }}
            className={`w-full p-4 rounded-xl flex items-center gap-3 font-bold text-lg ${activeTab === 1 ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400' : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}
          >
            <span>[!]</span> Segurança e Emergência
          </button>
        </div>
      </div>
    ) : null
  );

  // Renderizacao Principal
  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900"><LoadingSpinner /></div>;
  if (error && !weatherData) return <div className="min-h-screen p-6 flex items-center justify-center text-red-600 bg-slate-50 dark:bg-slate-900">{error}</div>;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 font-sans text-slate-700 dark:text-gray-200 transition-colors duration-300 overflow-x-hidden md:overflow-auto">

      {/* --- MOBILE LAYOUT (MAP FIRST) --- */}
      <div className="md:hidden min-h-screen w-full relative">
        {activeTab === 0 && (
          <>
            <div className="absolute inset-0 z-0">
              <MapComponent sensors={sensorData} className="h-full w-full" userLocation={currentCoords} />
            </div>
            <MobileTopOverlay />
            <MobileBottomOverlay />
          </>
        )}

        {/* Telas que nao sao Mapa no Mobile renderizam como paginas normais com scroll */}
        {activeTab !== 0 && (
          <div className="min-h-screen overflow-y-auto bg-gray-50 dark:bg-slate-900 p-4 pt-6">
            <div className="flex justify-between items-center mb-6">
              <button onClick={() => setActiveTab(0)} className="flex items-center gap-2 text-cyan-600 font-bold">
                <ChevronLeftIcon className="w-5 h-5" /> Voltar ao Mapa
              </button>
              <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
            </div>
            {activeTab === 1 && tabs[1]?.content}
            <div className="h-24"></div> {/* Espaco para o botao flutuante nao cobrir conteudo */}
          </div>
        )}

        <MobileNavButton />
        <MobileMenuModal />
      </div>

      {/* --- DESKTOP LAYOUT (STANDARD DASHBOARD) --- */}
      <div className="hidden md:block max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <Header
          onRefresh={handleRefresh}
          locationName={locationName}
          isRefreshing={isRefreshing}
          theme={theme}
          toggleTheme={toggleTheme}
          isSoundEnabled={isSoundEnabled}
          toggleSound={toggleSound}
        />
        {weatherData && riskAlert && (
          <Tabs tabs={tabs} /> // O Tabs original controla seu proprio estado interno, mas aqui vamos deixar ele renderizar livremente
        )}
        <footer className="text-center mt-12 text-slate-600 dark:text-slate-500 text-sm">
          <p>Dados climaticos fornecidos por <a href="https://openweathermap.org/" target="_blank" rel="noopener noreferrer" className="underline hover:text-cyan-500 dark:hover:text-cyan-400">OpenWeatherMap</a>.</p>
        </footer>
      </div>

      {isMapModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center px-4 py-6">
          <div className="relative bg-white dark:bg-slate-900 w-full h-full md:h-[80vh] md:w-[90vw] max-w-6xl rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="p-4 md:p-6 h-full flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400 dark:text-slate-500">Monitoramento</p>
                  <h3 className="text-xl font-bold text-slate-800 dark:text-white">Mapa de pontos monitorados</h3>
                </div>
                <div className="flex items-center gap-2">
                  <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-800 shadow-sm">
                      • Sensores
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-200 dark:border-blue-800 shadow-sm">
                      • Voce
                    </span>
                  </div>
                  <button
                    onClick={closeMapModal}
                    className="ml-3 flex items-center justify-center w-8 h-8 rounded-full bg-slate-800/85 text-white border border-slate-600 shadow-sm hover:bg-slate-700 transition focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900"
                    aria-label="Fechar mapa"
                  >
                    <XIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
              <div className="relative flex-1 min-h-[320px] rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700">
                <MapComponent sensors={sensorData} className="absolute inset-0" userLocation={currentCoords} />
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;


