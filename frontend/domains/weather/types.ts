// domains/weather/types.ts

export interface WeatherDescription {
  id: number;
  main: string;
  description: string;
  icon: string;
}

export interface CurrentWeather {
  dt: number;
  temp: number;
  feels_like: number;
  humidity: number;
  pressure: number;
  wind_speed: number; // in km/h
  wind_deg: number;
  rain?: { '1h': number };
  weather: WeatherDescription[];
}

export interface DailyForecast {
  dt: number;
  temp: {
    min: number;
    max: number;
  };
  pop: number;
  weather: WeatherDescription[];
}

export interface HourlyForecast {
  dt: number;
  temp: number;
  pop: number;
  weather: WeatherDescription[];
}

export interface WeatherData {
  current: CurrentWeather;
  daily: DailyForecast[];
  hourly: HourlyForecast[];
}
