import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { C, fontFamily } from "./tema";
import { Barrido, CabeceraSerie, Checklist, Cierre, Etiquetas, Banda, Gancho, Portada, TituloEscrito } from "./piezas";

// Un explicativo se arma con una lista de escenas. Cada escena: { tipo, segundos, ...datos de la pieza }.
// Tipos: portada, titulo, barrido, checklist, etiquetas, banda, cierre, gancho.
// compacto: las piezas van más chicas y arriba (para mezclarlas con los videos comunes, que llevan los
// subtítulos grandes en el medio). marca: false cuando el video ya pone @ramacontable por su cuenta.
export type EscenaAnim = { tipo: string; segundos: number; [k: string]: any };
export type PropsExplicativo = {
  serie?: { nombre: string; capitulo: number; total: number } | null;
  escenas: EscenaAnim[];
  compacto?: boolean;
  marca?: boolean;
};

export const FPS = 30;
export const duracionTotal = (p: PropsExplicativo) =>
  Math.max(1, p.escenas.reduce((a, e) => a + Math.round((e.segundos || 3) * FPS), 0));

const Fondo: React.FC = () => {
  const frame = useCurrentFrame();
  const puntos = [];
  for (let i = 0; i < 9; i++) {
    for (let j = 0; j < 16; j++) {
      const x = i * 130 + 40 + Math.sin((frame + j * 9) / 40) * 6;
      const y = ((j * 130 + frame * 0.6) % 2080) - 80;
      puntos.push(<div key={`${i}-${j}`} style={{ position: "absolute", left: x, top: y, width: 6, height: 6, borderRadius: 3, background: "#2A2A2A" }} />);
    }
  }
  return (
    <AbsoluteFill style={{ background: C.negro }}>
      {puntos}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(255,212,0,0.07), transparent 60%)" }} />
    </AbsoluteFill>
  );
};

// En modo compacto cada pieza se achica y sube lo justo para dejar libre la zona de los subtítulos (y≈1100-1250).
const COMPACTO: Record<string, [number, number]> = {
  gancho: [1.0, -420], titulo: [0.9, -330], banda: [0.8, -220], checklist: [0.68, -230], etiquetas: [0.8, -330],
};

const Pieza: React.FC<{ e: EscenaAnim; dur: number; serie?: PropsExplicativo["serie"] }> = ({ e, dur, serie }) => {
  switch (e.tipo) {
    case "portada":
      return <Portada dur={dur} serie={serie?.nombre || e.serie || ""} capitulo={serie?.capitulo || e.capitulo || 1} titulo={e.titulo || ""} icono={e.icono} cinta={e.cinta} />;
    case "titulo":
      return <TituloEscrito dur={dur} texto={e.texto || ""} icono={e.icono} cinta={e.cinta} />;
    case "barrido":
      return <Barrido dur={dur} texto={e.texto || ""} />;
    case "checklist":
      return <Checklist dur={dur} titulo={e.titulo || ""} items={e.items || []} activo={e.activo ?? 0} icono={e.icono} />;
    case "etiquetas":
      return <Etiquetas dur={dur} palabra={e.palabra || ""} cintas={e.cintas || []} icono_orbita={e.icono_orbita} />;
    case "banda":
      return <Banda dur={dur} numero={e.numero || 1} texto={e.texto || ""} icono={e.icono} detalle={e.detalle} />;
    case "gancho":
      return <Gancho dur={dur} numero={Number(e.numero) || 0} decimales={e.decimales || 0} prefijo={e.prefijo} sufijo={e.sufijo} arriba={e.arriba} abajo={e.abajo} contar={e.contar !== false} icono={e.icono} />;
    case "cierre":
      return <Cierre dur={dur} texto={e.texto || ""} web={e.web} proximo={e.proximo} />;
    default:
      return null;
  }
};

export const Explicativo: React.FC<PropsExplicativo> = (props) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  let desde = 0;
  return (
    <AbsoluteFill style={{ fontFamily, overflow: "hidden" }}>
      <Fondo />
      {props.escenas.map((e, i) => {
        const dur = Math.round((e.segundos || 3) * FPS);
        const seq = (
          <Sequence key={i} from={desde} durationInFrames={dur}>
            {props.compacto ? (
              <AbsoluteFill style={{ scale: String((COMPACTO[e.tipo] || [0.78, -330])[0]), translate: `0px ${(COMPACTO[e.tipo] || [0.78, -330])[1]}px` }}>
                <Pieza e={e} dur={dur} serie={props.serie} />
              </AbsoluteFill>
            ) : (
              <Pieza e={e} dur={dur} serie={props.serie} />
            )}
          </Sequence>
        );
        desde += dur;
        return seq;
      })}
      {props.serie ? (
        <CabeceraSerie nombre={props.serie.nombre} capitulo={props.serie.capitulo} total={props.serie.total} progreso={frame / Math.max(1, durationInFrames - 1)} />
      ) : null}
      {props.marca === false ? null : (
        <div style={{ position: "absolute", bottom: 60, right: 80, color: C.gris, fontWeight: 600, fontSize: 30 }}>@ramacontable</div>
      )}
    </AbsoluteFill>
  );
};
