# Estágio de Build
FROM node:20-alpine AS build
WORKDIR /app

# Variáveis para o Vite (somente no build)
ARG VITE_API_BASE_URL
ARG VITE_WEATHER_API_KEY
ARG VITE_MAPBOX_TOKEN

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WEATHER_API_KEY=$VITE_WEATHER_API_KEY
ENV VITE_MAPBOX_TOKEN=$VITE_MAPBOX_TOKEN

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Estágio de Produção (Nginx para servir o estático)
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Configuração para SPA (React Router) funcionar no Nginx
RUN echo 'server { listen 80; location / { root /usr/share/nginx/html; index index.html index.htm; try_files $uri $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
