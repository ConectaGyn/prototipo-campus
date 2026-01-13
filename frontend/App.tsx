import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { WeatherData, RiskAlert, SensorData, CurrentWeather } from './types.ts';
import { getWeatherData, getLocationName } from '@services/weather';
import { getMapPoints } from './services/map.service';

import Header from './components/Header.tsx';
import WeatherCard from './components/WeatherCard.tsx';
import AlertCard from './components/AlertCard.tsx';
import LoadingSpinner from './components/LoadingSpinner.tsx';
import SensorCarousel from './components/SensorCarousel.tsx';
import Tabs from './components/Tabs.tsx';
import MapComponent from './components/MapComponent.tsx';
import SafetyInfo from './components/SafetyInfo.tsx';

import {
  CheckCircleIcon,
  AlertTriangleIcon,
  MenuIcon,
  XIcon,
  WeatherIcon,
  Volume2Icon,
  VolumeXIcon,
  RefreshCwIcon,
  EyeIcon,
  EyeOffIcon,
  MapPinIcon,
} from './components/Icons.tsx';

import { useTheme } from './hooks/useTheme.ts';
import ThemeToggle from './components/ThemeToggle.tsx';
import { ChevronLeftIcon } from './components/Icons.tsx';

const GOIANIA_COORDS = {
  lat: -16.6869,
  lon: -49.2648,
};

const App: React.FC = () => {
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [displayedCurrentWeather, setDisplayedCurrentWeather] =
    useState<CurrentWeather | null>(null);

  const [mapSensors, setMapSensors] = useState<SensorData[]>([]);

  const [currentCoords, setCurrentCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [locationName, setLocationName] = useState('');
  const [riskAlert, setRiskAlert] = useState<RiskAlert | null>(null);

  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState(0);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showMobileDetails, setShowMobileDetails] = useState(true);

  const [isSoundEnabled, setIsSoundEnabled] = useState<boolean>(() => {
    const stored = localStorage.getItem('soundEnabled');
    return stored === null ? true : stored === 'true';
  });

  const isFetchingRef = useRef(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    localStorage.setItem('soundEnabled', String(isSoundEnabled));
  }, [isSoundEnabled]);

  const toggleSound = () => setIsSoundEnabled(prev => !prev);

  const fetchWeatherAndLocation = useCallback(
    async (lat: number, lon: number, locationError: string | null) => {
      try {
        const [weather, locName] = await Promise.all([
          getWeatherData(lat, lon),
          getLocationName(lat, lon),
        ]);

        setWeatherData(weather);
        setDisplayedCurrentWeather(weather.current);
        setCurrentCoords({ lat, lon });
        setLocationName(locName);

        if (locationError) setError(locationError);
        else setError(null);
      } catch (err) {
        setError('Erro ao buscar dados climáticos.');
        setWeatherData(null);
        setDisplayedCurrentWeather(null);
      }
    },
    []
  );

  const updateUserLocationData = useCallback(async (initial = false) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    if (initial) {
      setLoading(true);
      setError(null);
    }
    setIsRefreshing(true);

    const finalize = () => {
      setLoading(false);
      setIsRefreshing(false);
      isFetchingRef.current = false;
    };

    const fetchByCoords = async (lat: number, lon: number, err: string | null = null) => {
      await fetchWeatherAndLocation(lat, lon, err);
      finalize();
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => fetchByCoords(pos.coords.latitude, pos.coords.longitude),
        () =>
          fetchByCoords(
            GOIANIA_COORDS.lat,
            GOIANIA_COORDS.lon,
            'Não foi possível obter sua localização. Exibindo Goiânia.'
          ),
        { enableHighAccuracy: true, timeout: 7000 }
      );
    } else {
      fetchByCoords(
        GOIANIA_COORDS.lat,
        GOIANIA_COORDS.lon,
        'Geolocalização não suportada.'
      );
    }
  }, [fetchWeatherAndLocation]);

  useEffect(() => {
    if (!displayedCurrentWeather) return;

    const fetchCriticalPoints = async () => {
      try {const response = await getMapPoints();

        const converted: SensorData[] = response.pontos.map(item => ({
          id: item.ponto.id,
          location: item.ponto.nome,
          coords: {
            lat: item.ponto.localizacao.latitude,
            lon: item.ponto.localizacao.longitude,
          },

          temp: displayedCurrentWeather.temp,
          humidity: displayedCurrentWeather.humidity,
          wind_speed: displayedCurrentWeather.wind_speed,
          feels_like: displayedCurrentWeather.feels_like,
          pressure: displayedCurrentWeather.pressure,
          rain: displayedCurrentWeather.rain ?? null,

    
          alert: item.risco_atual
            ? {
                level: item.risco_atual.nivel,
                message: `Risco ${item.risco_atual.nivel} identificado.`,
                color: item.risco_atual.cor,
              }
            : undefined,
        }));
         
        console.log('Pontos críticos recebidos:', response.pontos);
        console.log('Sensores convertidos:', converted);

        setMapSensors(converted);

        const high = converted.filter(s => s.alert?.level === 'Alto');
        const moderate = converted.filter(s => s.alert?.level === 'Moderado');

        if (high.length || moderate.length) {
          setRiskAlert({
            level: high.length ? 'Alto' : 'Moderado',
            message: high.length
              ? `Risco Alto em ${high.map(s => s.location).join(', ')}`
              : `Risco Moderado em ${moderate.map(s => s.location).join(', ')}`,
            color: high.length ? 'bg-red-500' : 'bg-yellow-500',
            icon: <AlertTriangleIcon className="w-8 h-8 text-white" />,
          });
        } else {
          setRiskAlert(null);
        }
      } catch (err) {
        console.error('Erro ao buscar pontos críticos:', err);
      }
    };

    fetchCriticalPoints();
  }, [displayedCurrentWeather]);

  useEffect(() => {
    updateUserLocationData(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      updateUserLocationData(false);
    }, 300000);
    return () => clearInterval(interval);
  }, [updateUserLocationData]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error && !weatherData) {
    return <div className="p-6 text-red-600">{error}</div>;
  }

  const tabs = weatherData && displayedCurrentWeather ? [
    {
      label: 'Monitoramento',
      content: (
        <div className="flex flex-col gap-4 px-3 pb-6 max-w-screen-2xl mx-auto">
          {riskAlert && (
            <div className="max-w-3xl">
              <AlertCard alert={riskAlert} soundEnabled={isSoundEnabled} />
            </div>
        )}
        <div className="w-full">
          <MapComponent
            sensors={mapSensors}
            userLocation={currentCoords}
            className="h-[60vh] md:h-[65vh]"
          />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
          <div className="lg:col-span-2">
            <SensorCarousel sensors={mapSensors} />
          </div>
          <div className="lg:col-span-1">
            <WeatherCard current={displayedCurrentWeather} />
          </div>

    </div>
  </div>
)

    },
    {
      label: 'Segurança',
      content: <SafetyInfo userCoords={currentCoords} sensors={mapSensors} />
    }
  ] : [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 px-3 sm:px-4 lg:px-6">
      <Header
        onRefresh={() => updateUserLocationData(true)}
        locationName={locationName}
        isRefreshing={isRefreshing}
        theme={theme}
        toggleTheme={toggleTheme}
        isSoundEnabled={isSoundEnabled}
        toggleSound={toggleSound}
      />
      <div className="mt-4">
        <Tabs tabs={tabs} />
      </div>
    </div>
  );
};

export default App;