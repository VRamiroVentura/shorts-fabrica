import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, CLAMP, ENTRA_RAPIDO, SUAVE, fontFamily } from "./tema";
import { Icono } from "./iconos";

// ---------------------------------------------------------------- ayudas
const useResorte = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (desde: number, damping = 12, mass = 0.7) =>
    spring({ frame: frame - desde, fps, config: { damping, mass, stiffness: 140 } });
};

// salida común de cada escena: se achica un poco y se va en los últimos 8 cuadros
const salida = (frame: number, dur: number) => interpolate(frame, [dur - 8, dur], [0, 1], { ...CLAMP, easing: ENTRA_RAPIDO });

const Escena: React.FC<{ dur: number; children: React.ReactNode }> = ({ dur, children }) => {
  const frame = useCurrentFrame();
  const s = salida(frame, dur);
  return <AbsoluteFill style={{ fontFamily, opacity: 1 - s, scale: String(1 - 0.06 * s) }}>{children}</AbsoluteFill>;
};

// Etiqueta inclinada tipo cinta que aparece con rebote
export const Cinta: React.FC<{ texto: string; desde: number; giro?: number; fondo?: string; color?: string; tam?: number; style?: React.CSSProperties }> = ({
  texto, desde, giro = -3, fondo = C.crema, color = C.negro, tam = 46, style,
}) => {
  const r = useResorte()(desde, 10, 0.6);
  return (
    <div
      style={{
        display: "inline-block",
        background: fondo,
        color,
        fontWeight: 800,
        fontSize: tam,
        letterSpacing: 1,
        padding: "10px 26px",
        borderRadius: 8,
        boxShadow: "8px 10px 0 rgba(0,0,0,0.35)",
        rotate: `${giro + (1 - r) * -14}deg`,
        scale: String(r),
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {texto}
    </div>
  );
};

// ---------------------------------------------------------------- cabecera de serie (fija todo el video)
export const CabeceraSerie: React.FC<{ nombre: string; capitulo: number; total: number; progreso: number }> = ({ nombre, capitulo, total, progreso }) => {
  const frame = useCurrentFrame();
  const entra = interpolate(frame, [0, 14], [0, 1], { ...CLAMP, easing: SUAVE });
  return (
    <div style={{ position: "absolute", top: 120, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 18, fontFamily, opacity: entra, translate: `0px ${(1 - entra) * -40}px` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14, background: C.negro2, border: `3px solid ${C.grisOscuro}`, borderRadius: 40, padding: "10px 26px" }}>
        <span style={{ background: C.amarillo, color: C.negro, fontWeight: 800, fontSize: 28, padding: "2px 14px", borderRadius: 20 }}>CAP. {capitulo}/{total}</span>
        <span style={{ color: C.crema, fontWeight: 700, fontSize: 30, letterSpacing: 2, textTransform: "uppercase" }}>{nombre}</span>
      </div>
      <div style={{ width: 360, height: 8, borderRadius: 4, background: C.grisOscuro, overflow: "hidden" }}>
        <div style={{ width: `${progreso * 100}%`, height: "100%", background: C.amarillo }} />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- portada del capítulo
export const Portada: React.FC<{ dur: number; serie: string; capitulo: number; titulo: string; icono?: string; cinta?: string }> = ({ dur, serie, capitulo, titulo, icono = "factura", cinta }) => {
  const frame = useCurrentFrame();
  const res = useResorte();
  const num = res(4, 9, 0.8);
  const flota = Math.sin(frame / 12) * 10;
  return (
    <Escena dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 30, padding: "0 90px" }}>
        <div style={{ color: C.gris, fontWeight: 700, fontSize: 34, letterSpacing: 6, textTransform: "uppercase", opacity: interpolate(frame, [0, 10], [0, 1], CLAMP) }}>{serie}</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 20, scale: String(num) }}>
          <span style={{ color: C.crema, fontWeight: 800, fontSize: 70 }}>CAPÍTULO</span>
          <span style={{ color: C.negro, background: C.amarillo, fontWeight: 800, fontSize: 150, lineHeight: 1, padding: "0 28px", borderRadius: 16 }}>{capitulo}</span>
        </div>
        <div style={{ translate: `0px ${flota}px`, scale: String(res(12, 11)) }}>
          <Icono nombre={icono} tam={300} />
        </div>
        <div style={{ color: C.crema, fontWeight: 800, fontSize: 84, textAlign: "center", lineHeight: 1.08 }}>
          {titulo.split(" ").map((p, i) => (
            <span key={i} style={{ display: "inline-block", marginRight: 22, opacity: interpolate(frame, [16 + i * 3, 24 + i * 3], [0, 1], CLAMP), translate: `0px ${interpolate(frame, [16 + i * 3, 28 + i * 3], [50, 0], { ...CLAMP, easing: SUAVE })}px` }}>
              {p}
            </span>
          ))}
        </div>
        {cinta ? <Cinta texto={cinta} desde={34} giro={-4} fondo={C.amarillo} /> : null}
      </AbsoluteFill>
    </Escena>
  );
};

// ---------------------------------------------------------------- título que se escribe solo
export const TituloEscrito: React.FC<{ dur: number; texto: string; icono?: string; cinta?: string }> = ({ dur, texto, icono, cinta }) => {
  const frame = useCurrentFrame();
  const res = useResorte();
  const letras = Math.floor(interpolate(frame, [4, 4 + texto.length * 1.6], [0, texto.length], CLAMP));
  const cursor = Math.floor(frame / 8) % 2 === 0;
  return (
    <Escena dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 60, padding: "0 90px" }}>
        <div style={{ color: C.crema, fontWeight: 800, fontSize: 96, textAlign: "center", lineHeight: 1.1, textTransform: "uppercase", minHeight: 220 }}>
          {texto.slice(0, letras)}
          <span style={{ color: C.amarillo, opacity: cursor ? 1 : 0 }}>|</span>
        </div>
        {icono ? (
          <div style={{ scale: String(res(10 + texto.length * 1.6 * 0.5, 10)), rotate: `${Math.sin(frame / 15) * 4}deg` }}>
            <Icono nombre={icono} tam={320} />
          </div>
        ) : null}
        {cinta ? <Cinta texto={cinta} desde={Math.round(10 + texto.length * 1.6)} giro={3} /> : null}
      </AbsoluteFill>
    </Escena>
  );
};

// ---------------------------------------------------------------- barrido diagonal con texto grande
export const Barrido: React.FC<{ dur: number; texto: string }> = ({ dur, texto }) => {
  const frame = useCurrentFrame();
  const entra = interpolate(frame, [0, 10], [0, 1], { ...CLAMP, easing: SUAVE });
  const sale = interpolate(frame, [dur - 10, dur], [0, 1], { ...CLAMP, easing: ENTRA_RAPIDO });
  const pos = -130 + entra * 130 + sale * 130; // de -130% a 0% y después a 130%
  const texto_escala = interpolate(frame, [4, 16], [1.6, 1], { ...CLAMP, easing: SUAVE });
  return (
    <AbsoluteFill style={{ fontFamily, overflow: "hidden" }}>
      <div style={{ position: "absolute", top: -400, bottom: -400, left: `${pos}%`, width: "100%", background: C.amarillo, rotate: "12deg", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ rotate: "-12deg", color: C.negro, fontWeight: 800, fontSize: 170, textAlign: "center", lineHeight: 1, scale: String(texto_escala), textTransform: "uppercase", padding: "0 80px" }}>{texto}</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- checklist con contador (1 de 4, 2 de 4…)
export const Checklist: React.FC<{ dur: number; titulo: string; items: string[]; activo?: number; icono?: string }> = ({ dur, titulo, items, activo = 0, icono = "caja_fuerte" }) => {
  const frame = useCurrentFrame();
  const res = useResorte();
  const giro = interpolate(frame, [10, 40], [0, 360], { ...CLAMP, easing: SUAVE });
  return (
    <Escena dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 330, gap: 40 }}>
        <div style={{ color: C.crema, fontWeight: 800, fontSize: 72, textAlign: "center", padding: "0 90px", textTransform: "uppercase", opacity: interpolate(frame, [0, 10], [0, 1], CLAMP) }}>{titulo}</div>
        <div style={{ display: "flex", gap: 26 }}>
          {items.map((_, i) => {
            const encendido = i <= activo && frame > 16 + i * 6;
            return (
              <div key={i} style={{ width: 70, height: 70, borderRadius: 35, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 36, border: `5px solid ${encendido ? C.amarillo : C.grisOscuro}`, background: encendido ? C.amarillo : "transparent", color: encendido ? C.negro : C.gris, scale: String(res(8 + i * 4, 9)) }}>
                {i + 1}
              </div>
            );
          })}
        </div>
        <div style={{ rotate: `${giro}deg`, scale: String(res(4, 12)) }}>
          <Icono nombre={icono} tam={380} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18, alignItems: "center" }}>
          {items.map((t, i) => (
            <div key={i} style={{ fontSize: 46, fontWeight: i === activo ? 800 : 600, color: i === activo ? C.amarillo : i < activo ? C.gris : C.crema, opacity: interpolate(frame, [30 + i * 5, 38 + i * 5], [0, 1], CLAMP), translate: `${interpolate(frame, [30 + i * 5, 42 + i * 5], [-80, 0], { ...CLAMP, easing: SUAVE })}px 0px` }}>
              {i + 1}. {t}
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </Escena>
  );
};

// ---------------------------------------------------------------- palabra central con íconos que orbitan y cintas
export const Etiquetas: React.FC<{ dur: number; palabra: string; cintas?: string[]; icono_orbita?: string }> = ({ dur, palabra, cintas = [], icono_orbita = "moneda" }) => {
  const frame = useCurrentFrame();
  const res = useResorte();
  const r = res(2, 10);
  const n = 6;
  return (
    <Escena dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative", width: 760, height: 760, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ position: "absolute", width: 620, height: 620, borderRadius: 310, background: "rgba(255,212,0,0.08)", scale: String(r) }} />
          {Array.from({ length: n }).map((_, i) => {
            const a = (i / n) * Math.PI * 2 + frame / 30;
            const radio = 300 * r;
            return (
              <div key={i} style={{ position: "absolute", left: 380 + Math.cos(a) * radio - 55, top: 380 + Math.sin(a) * radio * 0.55 - 55, scale: String(0.6 + 0.4 * (Math.sin(a) + 1) / 2) }}>
                <Icono nombre={icono_orbita} tam={110} />
              </div>
            );
          })}
          <div style={{ background: C.crema, color: C.negro, fontWeight: 800, fontSize: 120, padding: "16px 56px", borderRadius: 18, boxShadow: `14px 16px 0 ${C.amarillo}`, scale: String(r), rotate: `${(1 - r) * 10}deg`, textTransform: "uppercase" }}>{palabra}</div>
        </div>
        <div style={{ position: "absolute", top: 1240, display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
          {cintas.map((t, i) => (
            <Cinta key={i} texto={t} desde={14 + i * 10} giro={i % 2 ? 3 : -3} fondo={i === 0 ? C.amarillo : C.crema} />
          ))}
        </div>
      </AbsoluteFill>
    </Escena>
  );
};

// ---------------------------------------------------------------- banda numerada con ícono que sube
export const Banda: React.FC<{ dur: number; numero: number; texto: string; icono?: string; detalle?: string }> = ({ dur, numero, texto, icono = "factura", detalle }) => {
  const frame = useCurrentFrame();
  const res = useResorte();
  const banda = interpolate(frame, [0, 12], [0, 1], { ...CLAMP, easing: SUAVE });
  const sube = res(10, 13);
  return (
    <Escena dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 360, gap: 60 }}>
        <div style={{ display: "flex", alignItems: "stretch", translate: `${(1 - banda) * -1100}px 0px`, boxShadow: "10px 12px 0 rgba(0,0,0,0.35)" }}>
          <div style={{ background: C.amarillo, color: C.negro, fontWeight: 800, fontSize: 84, padding: "4px 30px" }}>{numero}</div>
          <div style={{ background: C.crema, color: C.negro, fontWeight: 800, fontSize: 64, padding: "14px 34px", textTransform: "uppercase", whiteSpace: "nowrap" }}>{texto}</div>
        </div>
        <div style={{ translate: `0px ${(1 - sube) * 900 + Math.sin(frame / 14) * 8}px`, rotate: `${Math.sin(frame / 20) * 3}deg` }}>
          <Icono nombre={icono} tam={460} />
        </div>
        {detalle ? (
          <div style={{ color: C.crema, fontSize: 48, fontWeight: 600, textAlign: "center", padding: "0 110px", opacity: interpolate(frame, [22, 32], [0, 1], CLAMP) }}>{detalle}</div>
        ) : null}
      </AbsoluteFill>
    </Escena>
  );
};

// ---------------------------------------------------------------- cierre: manda al portal y anuncia el próximo
export const Cierre: React.FC<{ dur: number; texto: string; web?: string; proximo?: string }> = ({ dur, texto, web = "ramacontable.com.ar", proximo }) => {
  const frame = useCurrentFrame();
  const res = useResorte();
  const latido = 1 + Math.max(0, Math.sin(frame / 6)) * 0.03 * (frame > 24 ? 1 : 0);
  return (
    <Escena dur={dur}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 46, padding: "0 90px" }}>
        <div style={{ color: C.crema, fontWeight: 800, fontSize: 72, textAlign: "center", lineHeight: 1.15, opacity: interpolate(frame, [0, 10], [0, 1], CLAMP) }}>{texto}</div>
        <div style={{ background: C.amarillo, color: C.negro, fontWeight: 800, fontSize: 64, padding: "18px 44px", borderRadius: 60, scale: String(res(8, 9) * latido) }}>{web}</div>
        {proximo ? (
          <div style={{ marginTop: 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 16, opacity: interpolate(frame, [20, 30], [0, 1], CLAMP) }}>
            <span style={{ color: C.gris, fontWeight: 700, fontSize: 34, letterSpacing: 4 }}>EN EL PRÓXIMO CAPÍTULO</span>
            <Cinta texto={proximo} desde={24} giro={-2} />
          </div>
        ) : null}
      </AbsoluteFill>
    </Escena>
  );
};
