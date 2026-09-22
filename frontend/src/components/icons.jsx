const common = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" };

export function GaugeIcon(props) {
  return (
    <svg {...common} {...props}>
      <path d="M4 15a8 8 0 1 1 16 0" />
      <path d="M12 15l3.5-4.5" />
      <path d="M12 15h.01" />
    </svg>
  );
}

export function LayersIcon(props) {
  return (
    <svg {...common} {...props}>
      <path d="M12 3l8 4.5-8 4.5-8-4.5L12 3z" />
      <path d="M4 12.5l8 4.5 8-4.5" />
      <path d="M4 17l8 4.5L20 17" />
    </svg>
  );
}

export function TrendIcon(props) {
  return (
    <svg {...common} {...props}>
      <path d="M3 17l5-5 4 4 8-9" />
      <circle cx="20" cy="7" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function FlaskIcon(props) {
  return (
    <svg {...common} {...props}>
      <path d="M9 3h6" />
      <path d="M10 3v6l-5.5 9.5A1 1 0 0 0 5.4 20h13.2a1 1 0 0 0 .9-1.5L14 9V3" />
      <path d="M7.5 15h9" />
    </svg>
  );
}

export function ClockIcon(props) {
  return (
    <svg {...common} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function MapIcon(props) {
  return (
    <svg {...common} {...props}>
      <path d="M4 5.5l5-1.5 6 2 5-1.5v14l-5 1.5-6-2-5 1.5z" />
      <path d="M9 4v14M15 6v14" />
    </svg>
  );
}

export function InfoIcon(props) {
  return (
    <svg {...common} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5" />
      <path d="M12 8h.01" />
    </svg>
  );
}

export function CompassIcon(props) {
  return (
    <svg {...common} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M14.5 9.5l-2 5-3 1.5 2-5z" />
    </svg>
  );
}
