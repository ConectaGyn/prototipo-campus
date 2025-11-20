import type { WeatherData, DailyForecast, HourlyForecast } from '../types.ts';

// A chave de API agora é lida de variáveis de ambiente para maior segurança.
const API_KEY = import.meta.env.VITE_WEATHER_API_KEY;
const API_BASE_URL = 'https://api.openweathermap.org/data/2.5';
const GEO_API_BASE_URL = 'https://api.openweathermap.org/geo/1.0/reverse';
const API_KEY_ERROR_MESSAGE = "Chave de API do OpenWeatherMap não configurada. Defina VITE_WEATHER_API_KEY no arquivo .env.local.";

// A API da OpenWeather retorna a velocidade do vento em m/s. Convertendo para km/h.
const convertWindSpeedToKmh = (speedInMps: number): number => {
  return Math.round(speedInMps * 3.6);
};

export const convertWindDegreesToDirection = (degrees: number): string => {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO'];
  const index = Math.round(degrees / 22.5) % 16;
  return directions[index];
};

// Processa a resposta da API de previsão (5 dias/3 horas) para um formato de previsão diária.
const processForecastData = (forecastData: any): { daily: DailyForecast[], hourly: HourlyForecast[] } => {
  const dailyData: { [key: string]: { temps: number[], weathers: any[], dts: number[], pops: number[] } } = {};

  const hourly: HourlyForecast[] = forecastData.list.slice(0, 8).map((item: any) => ({
    dt: item.dt,
    temp: item.main.temp,
    pop: item.pop,
    weather: item.weather,
  }));

  forecastData.list.forEach((item: any) => {
    const date = new Date(item.dt * 1000).toISOString().split('T')[0];
    if (!dailyData[date]) {
      dailyData[date] = { temps: [], weathers: [], dts: [], pops: [] };
    }
    dailyData[date].temps.push(item.main.temp);
    dailyData[date].weathers.push(item.weather[0]);
    dailyData[date].dts.push(item.dt);
    dailyData[date].pops.push(item.pop);
  });

  // Remove o dia de hoje se houver poucos dados restantes para ele
  const today = new Date().toISOString().split('T')[0];
  if (dailyData[today] && dailyData[today].dts.length < 4) {
    delete dailyData[today];
  }

  const daily: DailyForecast[] = Object.entries(dailyData).slice(0, 5).map(([date, data]) => {
    const maxTemp = Math.max(...data.temps);
    const minTemp = Math.min(...data.temps);
    const maxPop = Math.max(...data.pops);

    // Usa o ícone do tempo mais representativo do dia (geralmente por volta do meio-dia)
    const middayWeather = data.weathers[Math.floor(data.weathers.length / 2)];
    
    // Usa o timestamp do primeiro registro do dia para consistência
    const dt = data.dts[0]; 

    return {
      dt,
      temp: {
        max: maxTemp,
        min: minTemp,
      },
      pop: maxPop,
      weather: [middayWeather],
    };
  });

  return { daily, hourly };
};


export const getWeatherData = async (lat: number, lon: number): Promise<WeatherData> => {
  if (!API_KEY) {
    throw new Error(API_KEY_ERROR_MESSAGE);
  }
    
  const commonParams = `lat=${lat}&lon=${lon}&appid=${API_KEY}&units=metric&lang=pt_br`;
  const currentWeatherUrl = `${API_BASE_URL}/weather?${commonParams}`;
  const forecastUrl = `${API_BASE_URL}/forecast?${commonParams}`;
  
  try {
    const [currentWeatherResponse, forecastResponse] = await Promise.all([
      fetch(currentWeatherUrl),
      fetch(forecastUrl),
    ]);

    if (!currentWeatherResponse.ok) {
        const errorData = await currentWeatherResponse.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${currentWeatherResponse.status}`);
    }
    if (!forecastResponse.ok) {
        const errorData = await forecastResponse.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${forecastResponse.status}`);
    }

    const currentData = await currentWeatherResponse.json();
    const forecastData = await forecastResponse.json();
    
    const { daily, hourly } = processForecastData(forecastData);

    return {
      current: {
        dt: currentData.dt,
        temp: currentData.main.temp,
        feels_like: currentData.main.feels_like,
        humidity: currentData.main.humidity,
        pressure: currentData.main.pressure,
        wind_speed: convertWindSpeedToKmh(currentData.wind.speed),
        wind_deg: currentData.wind.deg,
        rain: currentData.rain,
        weather: currentData.weather,
      },
      daily,
      hourly,
    };

  } catch (error) {
    console.error("Erro ao buscar dados climáticos:", error);
    throw error;
  }
};

export const getLocationName = async (lat: number, lon: number): Promise<string> => {
    if (!API_KEY) {
        throw new Error(API_KEY_ERROR_MESSAGE);
    }
    
    const url = `${GEO_API_BASE_URL}?lat=${lat}&lon=${lon}&limit=1&appid=${API_KEY}`;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: `HTTP error! status: ${response.status}` }));
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.length > 0) {
            const { name, state } = data[0];
            return `${name}, ${state}`;
        }
        return "Localização desconhecida";
    } catch (error) {
        console.error("Erro ao buscar nome da localização:", error);
        throw error;
    }
}
