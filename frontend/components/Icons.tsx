
import React from 'react';

interface IconProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
  title?: string;
}

const BaseIcon: React.FC<IconProps & { children: React.ReactNode }> = ({
  className,
  title,
  children,
  ...props
}) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden={!title ? "true" : undefined} // Esconde do leitor de tela se não tiver título
    role={title ? "img" : undefined}
    {...props}
  >
    {title && <title>{title}</title>}
    {children}
  </svg>
);

export const ThermometerIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" />
  </BaseIcon>
);

export const DropletIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" />
  </BaseIcon>
);

export const WindIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
    <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
    <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
  </BaseIcon>
);

export const SunIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2" />
    <path d="M12 20v2" />
    <path d="m4.93 4.93 1.41 1.41" />
    <path d="m17.66 17.66 1.41 1.41" />
    <path d="M2 12h2" />
    <path d="M20 12h2" />
    <path d="m6.34 17.66-1.41 1.41" />
    <path d="m19.07 4.93-1.41 1.41" />
  </BaseIcon>
);

export const GaugeIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="m12 14 4-4" /><path d="M3.34 19a10 10 0 1 1 17.32 0" />
  </BaseIcon>
);

export const CompassIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <circle cx="12" cy="12" r="10" /><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
  </BaseIcon>
);

export const CloudIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
  </BaseIcon>
);

export const CloudRainIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
    <path d="M16 14v6" />
    <path d="M8 14v6" />
    <path d="M12 16v6" />
  </BaseIcon>
);

export const CloudDrizzleIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" /><path d="M8 19v1" /><path d="M8 14v1" /><path d="M16 19v1" /><path d="M16 14v1" /><path d="M12 15v1" /><path d="M12 20v1" />
  </BaseIcon>
);

export const CloudLightningIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M6 16.326A7 7 0 1 1 17.71 8h1.79a4.5 4.5 0 0 1 .5 8.973" /><path d="m13 12-3 5h4l-3 5" />
  </BaseIcon>
);

export const CloudSnowIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" /><path d="M12 12v6" /><path d="m12 18 2-2" /><path d="m12 18-2-2" /><path d="m9 15 2-2" /><path d="m13 15-2-2" />
  </BaseIcon>
);

export const CloudFogIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" /><path d="M2 20h20" /><path d="M6 16h12" />
  </BaseIcon>
);

export const MoonIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
  </BaseIcon>
);


export const RefreshCwIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
    <path d="M3 21v-5h5" />
  </BaseIcon>
);

export const AlertTriangleIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
    <path d="M12 9v4" />
    <path d="M12 17h.01" />
  </BaseIcon>
);

export const CheckCircleIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </BaseIcon>
);

export const ChevronLeftIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="m15 18-6-6 6-6" />
  </BaseIcon>
);

export const ChevronRightIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="m9 18 6-6-6-6" />
  </BaseIcon>
);

export const Volume2Icon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
  </BaseIcon>
);

export const VolumeXIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <line x1="23" y1="9" x2="17" y2="15" />
    <line x1="17" y1="9" x2="23" y2="15" />
  </BaseIcon>
);

export const PlayCircleIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <circle cx="12" cy="12" r="10" />
    <polygon points="10 8 16 12 10 16 10 8" />
  </BaseIcon>
);

export const StopCircleIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <circle cx="12" cy="12" r="10" />
    <rect x="9" y="9" width="6" height="6" />
  </BaseIcon>
);

export const SlidersIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <line x1="4" x2="20" y1="21" y2="21" />
    <line x1="4" x2="20" y1="14" y2="14" />
    <line x1="4" x2="20" y1="7" y2="7" />
    <circle cx="12" cy="14" r="2" />
    <circle cx="12" cy="7" r="2" />
    <circle cx="12" cy="21" r="2" />
  </BaseIcon>
);

export const XIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </BaseIcon>
);

export const ShuffleIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l10.6-12.6c.7-1.1 1.9-1.7 3.3-1.7H22" />
    <path d="m18 2 4 4-4 4" />
    <path d="M2 6h1.9c1.5 0 2.9.9 3.6 2.2" />
    <path d="M22 18h-2.7c-1.3 0-2.5-.6-3.3-1.7L11.6 11" />
    <path d="m18 22 4-4-4-4" />
  </BaseIcon>
);

export const PhoneIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
  </BaseIcon>
);

export const ShieldAlertIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    <path d="M12 8v4" />
    <path d="M12 16h.01" />
  </BaseIcon>
);

export const FlameIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.1.2-2.2.5-3.3.3-1.1 1-2.2 3-3.3.325.075.666.128 1 1.6z" />
  </BaseIcon>
);

export const ActivityIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </BaseIcon>
);

export const MapPinIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
    <circle cx="12" cy="10" r="3" />
  </BaseIcon>
);

export const BuildingIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <rect x="4" y="2" width="16" height="20" rx="2" ry="2" />
    <path d="M9 22v-4h6v4" />
    <path d="M8 6h.01" />
    <path d="M16 6h.01" />
    <path d="M12 6h.01" />
    <path d="M12 10h.01" />
    <path d="M12 14h.01" />
    <path d="M16 10h.01" />
    <path d="M16 14h.01" />
    <path d="M8 10h.01" />
    <path d="M8 14h.01" />
  </BaseIcon>
);

export const MenuIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <line x1="4" x2="20" y1="12" y2="12" />
    <line x1="4" x2="20" y1="6" y2="6" />
    <line x1="4" x2="20" y1="18" y2="18" />
  </BaseIcon>
);

export const ListIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <line x1="8" x2="21" y1="6" y2="6" />
    <line x1="8" x2="21" y1="12" y2="12" />
    <line x1="8" x2="21" y1="18" y2="18" />
    <line x1="3" x2="3.01" y1="6" y2="6" />
    <line x1="3" x2="3.01" y1="12" y2="12" />
    <line x1="3" x2="3.01" y1="18" y2="18" />
  </BaseIcon>
);

export const EyeIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
    <circle cx="12" cy="12" r="3" />
  </BaseIcon>
);

export const EyeOffIcon: React.FC<IconProps> = (props) => (
  <BaseIcon {...props}>
    <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
    <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
    <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
    <line x1="2" x2="22" y1="2" y2="22" />
  </BaseIcon>
);


export const WeatherIcon: React.FC<{ iconCode: string, className?: string, title?: string }> = ({ iconCode, className, title }) => {
  const props = { className, title };
  switch (iconCode) {
    case '01d': return <SunIcon {...props} />;
    case '01n': return <MoonIcon {...props} />;
    case '02d': case '02n': case '03d': case '03n': case '04d': case '04n': return <CloudIcon {...props} />;
    case '09d': case '09n': return <CloudDrizzleIcon {...props} />;
    case '10d': case '10n': return <CloudRainIcon {...props} />;
    case '11d': case '11n': return <CloudLightningIcon {...props} />;
    case '13d': case '13n': return <CloudSnowIcon {...props} />;
    case '50d': case '50n': return <CloudFogIcon {...props} />;
    default: return <SunIcon {...props} />;
  }
};
