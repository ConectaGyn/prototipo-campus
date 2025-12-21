import http from 'http';
import { URL } from 'url';

const SENSOR_ENDPOINT = process.env.SENSOR_ENDPOINT
  || 'https://script.google.com/macros/s/AKfycbx2V97T9d-zr6QDsLa-brN5mLXYmpjP85dDDbzpq7EFXt-k_oqSb5S-X_0ytARcEWQ0Pw/exec';
const SENSOR_FETCH_INTERVAL_MS = Number(process.env.SENSOR_FETCH_INTERVAL_MS || 10000);
const SERVER_PORT = Number(process.env.SENSOR_API_PORT || 5174);

let latestReadings = [];
let lastUpdated = null;
let lastError = null;

const stripParensSuffix = (value) => value.replace(/\s*\(.*\)\s*$/, '').trim();

const parseBrazilianDate = (value) => {
  const match = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
  if (!match) return null;
  const [, day, month, year, hour = '0', minute = '0', second = '0'] = match;
  const utcMs = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour) + 3,
    Number(minute),
    Number(second)
  );
  return new Date(utcMs).toISOString();
};

const parseTimestamp = (value) => {
  if (value === null || value === undefined) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  const cleaned = stripParensSuffix(raw);
  const brIso = parseBrazilianDate(cleaned);
  if (brIso) return brIso;
  const parsed = Date.parse(cleaned);
  if (!Number.isNaN(parsed)) {
    return new Date(parsed).toISOString();
  }
  return null;
};

const parseNumber = (value) => {
  if (value === null || value === undefined) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  const normalized = raw.replace('%', '').replace(/\s+/g, '').replace(',', '.');
  const num = Number(normalized);
  return Number.isFinite(num) ? num : null;
};

const parseCsv = (text) => {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];

    if (char === '"') {
      if (inQuotes && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (!inQuotes && (char === ',' || char === '\n' || char === '\r')) {
      if (char === '\r' && text[i + 1] === '\n') {
        i += 1;
      }
      row.push(field);
      field = '';
      if (char === '\n' || char === '\r') {
        rows.push(row);
        row = [];
      }
      continue;
    }

    field += char;
  }

  row.push(field);
  rows.push(row);

  return rows.filter((r) => r.some((cell) => cell && cell.trim() !== ''));
};

const toKeyedObject = (headers, row) => {
  const obj = {};
  headers.forEach((header, index) => {
    obj[header] = row[index] ?? '';
  });
  return obj;
};

const normalizeRow = (row) => {
  const lowered = {};
  Object.entries(row).forEach(([key, value]) => {
    lowered[key.trim().toLowerCase()] = value;
  });

  const pick = (names) => {
    for (const name of names) {
      if (lowered[name] !== undefined) return lowered[name];
    }
    return null;
  };

  const timestampCandidates = [
    pick(['timestamp', 'time', 'datetime', 'data', 'date']),
    pick(['temperature', 'temp', 'temperatura']),
    pick(['distance', 'level', 'nivel']),
  ];

  let timestamp = null;
  for (const candidate of timestampCandidates) {
    timestamp = parseTimestamp(candidate);
    if (timestamp) break;
  }

  const sensorId = pick(['sensorid', 'sensor_id', 'deviceid', 'device_id', 'id']);
  const location = pick(['location', 'local', 'sensor', 'name']);

  const temperature = parseNumber(pick(['temperature', 'temp', 'temperatura']));
  const humidity = parseNumber(pick(['humidity', 'umidade']));
  const windSpeed = parseNumber(pick(['windspeed', 'wind_speed', 'vento', 'wind']));
  const level = parseNumber(pick(['level', 'nivel', 'distance']));

  return {
    sensorId: sensorId ? String(sensorId).trim() : null,
    location: location ? String(location).trim() : null,
    temp: temperature,
    humidity,
    wind_speed: windSpeed,
    level,
    timestamp,
  };
};

const latestByKey = (rows) => {
  const map = new Map();
  rows.forEach((row, index) => {
    const key = row.sensorId || row.location || 'default';
    const tsValue = row.timestamp ? Date.parse(row.timestamp) : null;
    const score = Number.isFinite(tsValue) ? tsValue : index;
    const existing = map.get(key);
    if (!existing || score >= existing.score) {
      map.set(key, { score, row });
    }
  });
  return Array.from(map.values()).map((entry) => entry.row);
};

const fetchSensorCsv = async () => {
  const url = new URL(SENSOR_ENDPOINT);
  if (!url.searchParams.has('format')) {
    url.searchParams.set('format', 'csv');
  }

  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Sensor endpoint error: ${response.status} ${body}`);
  }
  const text = await response.text();
  if (text.trim() === 'OK') {
    throw new Error("Endpoint retornou 'OK' (modo incorreto).");
  }

  return text;
};

const pollSensors = async () => {
  try {
    const csvText = await fetchSensorCsv();
    const rows = parseCsv(csvText);
    if (rows.length === 0) {
      throw new Error('CSV vazio.');
    }
    const headers = rows[0].map((header) => header.trim());
    const dataRows = rows.slice(1);
    const normalized = dataRows.map((row) => normalizeRow(toKeyedObject(headers, row)));
    latestReadings = latestByKey(normalized);
    lastUpdated = new Date().toISOString();
    lastError = null;
  } catch (error) {
    lastError = error instanceof Error ? error.message : String(error);
  }
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);

  if (url.pathname === '/api/sensors/latest') {
    const payload = {
      sensors: latestReadings,
      updatedAt: lastUpdated,
      error: lastError,
    };
    const json = JSON.stringify(payload);
    res.writeHead(200, {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-store',
    });
    res.end(json);
    return;
  }

  if (url.pathname === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

pollSensors();
setInterval(pollSensors, SENSOR_FETCH_INTERVAL_MS);

server.listen(SERVER_PORT, () => {
  console.log(`Sensor API listening on http://localhost:${SERVER_PORT}`);
});
