# ClimaGyn (prototipo-campus)

Projeto web para monitoramento climatico e sensores urbanos, com mapa interativo, alertas de risco e foco em acessibilidade.

## Visao geral
O app combina dados da OpenWeatherMap com leituras de sensores locais para indicar riscos (chuva intensa, vento forte, calor) e apoiar decisoes em tempo real. O layout se adapta a mobile e desktop, com widgets de acessibilidade e leitura por voz.

## Funcionalidades
- Geolocalizacao do usuario com fallback para Goiania.
- Alertas de risco (baixo/moderado/alto) com audio e TTS.
- Mapa interativo (Mapbox) com sensores e clima por clique.
- Carrossel de sensores e indicadores de risco.
- Aba de seguranca com orientacoes e rotas (quando aplicavel).
- Tema claro/escuro com persistencia no localStorage.
- Widgets de acessibilidade (VLibras e EqualWeb).

## Stack
- React 18 + TypeScript
- Vite 6
- Tailwind CSS via CDN (frontend/index.html)
- Mapbox GL JS (mapa)
- Node.js (API local de sensores)

## Requisitos
- Node.js 18+ (recomendado)
- Conta e token do Mapbox
- Chave da OpenWeatherMap

## Como rodar localmente
1) Instale dependencias:
   `npm install`

2) Configure o arquivo `.env.local` (exemplo):

```bash
VITE_WEATHER_API_KEY=coloque_sua_chave_da_openweathermap
VITE_MAPBOX_TOKEN=coloque_seu_token_do_mapbox
```

3) Inicie a API local de sensores (em um terminal):
   `npm run server`

4) Inicie o frontend (em outro terminal):
   `npm run dev`

Acesse: `http://localhost:3000`

## Variaveis de ambiente
Frontend:
- `VITE_WEATHER_API_KEY` (obrigatoria): chave da OpenWeatherMap.
- `VITE_MAPBOX_TOKEN` (obrigatoria): token de acesso do Mapbox.

Backend (backend/sensorServer.js):
- `SENSOR_ENDPOINT` (opcional): URL do endpoint CSV dos sensores.
- `SENSOR_FETCH_INTERVAL_MS` (opcional): intervalo de coleta em ms (padrao 10000).
- `SENSOR_API_PORT` (opcional): porta da API local (padrao 5174).

## Scripts
- `npm run dev`: inicia o frontend (Vite) em modo desenvolvimento.
- `npm run build`: build de producao.
- `npm run preview`: preview do build.
- `npm run server`: inicia a API local de sensores.

## Fluxo de dados
1) O frontend solicita geolocalizacao do navegador.
2) Se permitido, busca clima atual e previsao na OpenWeatherMap; se negado, usa Goiania.
3) O servidor local busca um CSV remoto, normaliza os dados e expõe em `/api/sensors/latest`.
4) O frontend consulta `/api/sensors/latest` a cada 10s (proxy do Vite para `http://localhost:5174`).
5) O nivel de risco global combina o clima (vento/chuva/umidade) e os alertas por sensor.

## Mapa (Mapbox)
- O mapa usa Mapbox GL JS carregado via script em `frontend/index.html`.
- O token e lido de `VITE_MAPBOX_TOKEN`.
- Clique em qualquer ponto do mapa para obter clima em tempo real daquele local.
- Marcadores:
  - Sensores: verde (normal), amarelo (moderado), vermelho (alto).
  - Usuario: azul.
  - Rotas: linha ciano quando aplicavel.

## Regras de risco (resumo)
- Risco alto: vento > 60 km/h ou chuva 1h > 5 mm.
- Risco moderado: vento > 50 km/h, umidade > 95% ou prob. chuva > 90%.
- Sensores usam limites proprios em `services/sensorService.ts`.

## API local de sensores
Endpoints:
- `GET /api/sensors/latest`: retorna leituras normalizadas e ultimo update.
- `GET /healthz`: health check simples.

Formato de resposta:
```json
{
  "sensors": [
    {
      "sensorId": "...",
      "location": "...",
      "temp": 28.5,
      "humidity": 64,
      "wind_speed": 12,
      "level": 0.3,
      "timestamp": "2025-01-01T12:00:00.000Z"
    }
  ],
  "updatedAt": "...",
  "error": null
}
```

## Estrutura do projeto

Frontend (`frontend/`):
- `frontend/App.tsx`: orquestracao de dados, layout principal e logica de risco.
- `frontend/components/`: UI (cards, mapa, abas, carrossel, etc.).
- `frontend/services/`: integracoes externas (OpenWeatherMap e API de sensores).
- `frontend/hooks/`: estado de tema e TTS.
- `frontend/utils/`: funcoes auxiliares (geo, som, locais seguros).
- `frontend/index.html`: scripts externos (Mapbox, VLibras, EqualWeb) e Tailwind CDN.
- `frontend/index.tsx`: bootstrap do React.
- `frontend/types.ts`: tipos compartilhados do frontend.

Backend (`backend/`):
- `backend/sensorServer.js`: API local que busca CSV remoto, normaliza e expoe em `/api/sensors/latest`.
## Acessibilidade
- TTS (SpeechSynthesis) para leitura de alertas.
- VLibras e EqualWeb carregados via scripts no `frontend/index.html`.
- Alto contraste em alertas criticos e suporte a tema escuro.

## Observacoes
- Sem a API local (`npm run server`), o mapa funciona, mas sem dados reais de sensores.
- As chaves de API no frontend ficam visiveis no build. Use restricoes no painel do provedor.

## Troubleshooting
- "Chave de API do OpenWeatherMap nao configurada": defina `VITE_WEATHER_API_KEY` em `.env.local`.
- Mapa em branco: confirme `VITE_MAPBOX_TOKEN` e se o script do Mapbox carregou.
- Erro 404 em `/api/sensors/latest`: inicie `npm run server`.
- Sem permissao de localizacao: o app usa Goiania como fallback.

## Build e deploy
1) `npm run build`
2) `npm run preview` para validar o build localmente.

Se quiser, posso gerar um `docs/` com diagramas, fluxo de dados detalhado e notas de operacao.