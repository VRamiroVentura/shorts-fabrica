import React from "react";
import { C } from "./tema";

// Íconos propios, de línea crema con detalles amarillos. viewBox 0 0 200 200.
// Para sumar uno nuevo: agregalo a ICONOS con su nombre.
const L = { fill: "none", stroke: C.crema, strokeWidth: 8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

const ICONOS: Record<string, React.ReactNode> = {
  factura: (
    <>
      <path d="M50 20 H150 V180 L135 168 L120 180 L105 168 L90 180 L75 168 L60 180 L50 172 Z" {...L} />
      <rect x="66" y="40" width="44" height="12" rx="3" fill={C.amarillo} />
      <line x1="66" y1="76" x2="134" y2="76" {...L} strokeWidth={6} />
      <line x1="66" y1="98" x2="134" y2="98" {...L} strokeWidth={6} />
      <line x1="66" y1="120" x2="110" y2="120" {...L} strokeWidth={6} />
      <text x="134" y="150" textAnchor="end" fontSize="26" fontWeight="800" fill={C.amarillo}>$</text>
    </>
  ),
  moneda: (
    <>
      <circle cx="100" cy="100" r="70" fill={C.amarillo} />
      <circle cx="100" cy="100" r="54" fill="none" stroke={C.negro} strokeWidth="6" />
      <text x="100" y="124" textAnchor="middle" fontSize="70" fontWeight="800" fill={C.negro}>$</text>
    </>
  ),
  caja_fuerte: (
    <>
      <rect x="30" y="30" width="140" height="140" rx="18" {...L} />
      <circle cx="100" cy="100" r="40" fill={C.amarillo} />
      <circle cx="100" cy="100" r="10" fill={C.negro} />
      <line x1="100" y1="100" x2="100" y2="68" stroke={C.negro} strokeWidth="7" strokeLinecap="round" />
      <line x1="100" y1="100" x2="128" y2="116" stroke={C.negro} strokeWidth="7" strokeLinecap="round" />
      <line x1="100" y1="100" x2="72" y2="116" stroke={C.negro} strokeWidth="7" strokeLinecap="round" />
    </>
  ),
  calendario: (
    <>
      <rect x="30" y="44" width="140" height="126" rx="14" {...L} />
      <rect x="30" y="44" width="140" height="34" rx="14" fill={C.amarillo} />
      <line x1="68" y1="28" x2="68" y2="56" {...L} />
      <line x1="132" y1="28" x2="132" y2="56" {...L} />
      {[0, 1, 2].map((f) => [0, 1, 2, 3].map((c) => (
        <rect key={`${f}${c}`} x={50 + c * 27} y={96 + f * 24} width="16" height="12" rx="3" fill={f === 1 && c === 2 ? C.amarillo : C.crema} />
      )))}
    </>
  ),
  recibo_sueldo: (
    <>
      <rect x="44" y="20" width="112" height="160" rx="10" {...L} />
      <circle cx="78" cy="56" r="14" fill={C.amarillo} />
      <line x1="100" y1="52" x2="136" y2="52" {...L} strokeWidth={6} />
      <line x1="62" y1="92" x2="138" y2="92" {...L} strokeWidth={6} />
      <line x1="62" y1="114" x2="138" y2="114" {...L} strokeWidth={6} />
      <rect x="62" y="138" width="76" height="20" rx="4" fill={C.amarillo} />
    </>
  ),
  persona: (
    <>
      <circle cx="100" cy="68" r="32" {...L} />
      <path d="M40 172 Q40 116 100 116 Q160 116 160 172" {...L} />
      <rect x="84" y="130" width="32" height="10" rx="5" fill={C.amarillo} />
    </>
  ),
  casa: (
    <>
      <path d="M30 96 L100 36 L170 96" {...L} />
      <path d="M50 84 V170 H150 V84" {...L} />
      <rect x="84" y="118" width="32" height="52" rx="4" fill={C.amarillo} />
    </>
  ),
  calculadora: (
    <>
      <rect x="46" y="20" width="108" height="160" rx="14" {...L} />
      <rect x="62" y="38" width="76" height="34" rx="6" fill={C.amarillo} />
      {[0, 1, 2].map((f) => [0, 1, 2].map((c) => (
        <circle key={`${f}${c}`} cx={74 + c * 26} cy={100 + f * 26} r="8" fill={C.crema} />
      )))}
    </>
  ),
  lupa: (
    <>
      <circle cx="86" cy="86" r="46" {...L} />
      <circle cx="86" cy="86" r="30" fill={C.amarillo} opacity="0.85" />
      <line x1="120" y1="120" x2="166" y2="166" {...L} strokeWidth={14} />
    </>
  ),
  billetera: (
    <>
      <rect x="26" y="56" width="148" height="104" rx="14" {...L} />
      <path d="M40 56 L136 30 L148 56" {...L} />
      <rect x="120" y="92" width="54" height="34" rx="8" fill={C.amarillo} />
      <circle cx="138" cy="109" r="6" fill={C.negro} />
    </>
  ),
  alerta: (
    <>
      <path d="M100 26 L176 164 H24 Z" fill={C.amarillo} stroke={C.amarillo} strokeWidth="8" strokeLinejoin="round" />
      <line x1="100" y1="76" x2="100" y2="118" stroke={C.negro} strokeWidth="12" strokeLinecap="round" />
      <circle cx="100" cy="142" r="8" fill={C.negro} />
    </>
  ),
  check: (
    <>
      <circle cx="100" cy="100" r="72" fill={C.amarillo} />
      <path d="M66 102 L90 126 L136 78" fill="none" stroke={C.negro} strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  grafico: (
    <>
      <line x1="34" y1="166" x2="170" y2="166" {...L} />
      <rect x="50" y="110" width="26" height="50" rx="4" fill={C.crema} />
      <rect x="88" y="80" width="26" height="80" rx="4" fill={C.crema} />
      <rect x="126" y="44" width="26" height="116" rx="4" fill={C.amarillo} />
    </>
  ),
};

export const nombresIconos = Object.keys(ICONOS);

export const Icono: React.FC<{ nombre: string; tam?: number; style?: React.CSSProperties }> = ({ nombre, tam = 260, style }) => (
  <svg width={tam} height={tam} viewBox="0 0 200 200" style={style}>
    {ICONOS[nombre] || ICONOS.factura}
  </svg>
);
