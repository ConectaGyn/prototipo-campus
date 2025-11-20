export interface SafeLocation {
  id: string;
  name: string;
  type: string;
  address: string;
  coords: { lat: number; lon: number };
  icon: 'health' | 'fire' | 'support' | 'security';
}

export const SAFE_LOCATIONS: SafeLocation[] = [
  {
    id: 'hugo',
    name: 'Hospital de Urgências (HUGO)',
    type: 'Emergência Médica',
    address: 'Av. 31 de Março, St. Pedro Ludovico',
    coords: { lat: -16.7081, lon: -49.2644 },
    icon: 'health',
  },
  {
    id: 'bombeiros',
    name: 'Quartel do Corpo de Bombeiros',
    type: 'Defesa Civil / Bombeiros',
    address: 'Av. C-107, Jardim América',
    coords: { lat: -16.7192, lon: -49.2855 },
    icon: 'fire',
  },
  {
    id: 'santa-casa',
    name: 'Santa Casa de Misericórdia',
    type: 'Hospital',
    address: 'Rua Campinas, Vila Americano do Brasil',
    coords: { lat: -16.6742, lon: -49.2663 },
    icon: 'health',
  },
  {
    id: 'flamboyant',
    name: 'Flamboyant Shopping',
    type: 'Ponto de Apoio / Abrigo',
    address: 'Av. Dep. Jamel Cecílio, Jd. Goiânia',
    coords: { lat: -16.7085, lon: -49.2354 },
    icon: 'support',
  },
  {
    id: 'goiania-shopping',
    name: 'Goiânia Shopping',
    type: 'Ponto de Apoio / Abrigo',
    address: 'Av. T-10, Setor Bueno',
    coords: { lat: -16.7092, lon: -49.2842 },
    icon: 'support',
  },
  {
    id: 'pm-batalhao',
    name: 'Batalhão da Polícia Militar',
    type: 'Segurança',
    address: 'Rua T-29, Setor Bueno',
    coords: { lat: -16.7018, lon: -49.2781 },
    icon: 'security',
  },
];
