import React from "react";
import { AbsoluteFill } from "remotion";
import { C, fontFamily } from "./tema";
import { Icono } from "./iconos";

// Portadas fijas (imagen 1080x1920). Lo importante va en el centro: Instagram recorta la grilla.
export type PropsPortada = {
  tipo: "vs" | "cero" | "secretos";
  capitulo?: number;
  total?: number;
  tema?: string; // tema del capítulo
  icono?: string; // ícono del nicho (serie secretos)
  nicho?: string; // frase al público, ej. "¿Alquilás un depto?"
  grande?: string; // texto gigante opcional en lugar del ícono, ej. "1%"
};

const Puntos: React.FC = () => {
  const p = [];
  for (let i = 0; i < 9; i++) for (let j = 0; j < 16; j++)
    p.push(<div key={`${i}-${j}`} style={{ position: "absolute", left: i * 130 + 40, top: j * 130 + 20, width: 6, height: 6, borderRadius: 3, background: "#2A2A2A" }} />);
  return <>{p}</>;
};

const Marca: React.FC = () => (
  <div style={{ position: "absolute", bottom: 90, left: 0, right: 0, textAlign: "center", color: C.gris, fontWeight: 700, fontSize: 34, letterSpacing: 2 }}>
    @ramacontable · ramacontable.com.ar
  </div>
);

const Cinta: React.FC<{ texto: string; fondo?: string; color?: string; giro?: number; tam?: number }> = ({ texto, fondo = C.crema, color = C.negro, giro = -3, tam = 52 }) => (
  <div style={{ display: "inline-block", background: fondo, color, fontWeight: 800, fontSize: tam, padding: "12px 30px", borderRadius: 10, rotate: `${giro}deg`, boxShadow: "10px 12px 0 rgba(0,0,0,0.4)", textTransform: "uppercase", whiteSpace: "nowrap" }}>
    {texto}
  </div>
);

// ---------------------------------------------------------------- 1. VS
const PortadaVS: React.FC = () => (
  <AbsoluteFill style={{ background: C.negro }}>
    <Puntos />
    {/* mitad derecha más clara, cortada en diagonal */}
    <div style={{ position: "absolute", top: -200, bottom: -200, left: 560, width: 900, background: C.negro2, rotate: "8deg" }} />
    <div style={{ position: "absolute", top: 230, left: 0, right: 0, textAlign: "center" }}>
      <Cinta texto="¿Cuál te conviene?" fondo={C.amarillo} giro={-2} tam={60} />
    </div>
    {/* íconos arriba, VS al medio, nombres abajo */}
    <div style={{ position: "absolute", top: 560, left: 70, width: 400, display: "flex", justifyContent: "center" }}>
      <Icono nombre="billetera" tam={300} />
    </div>
    <div style={{ position: "absolute", top: 560, right: 70, width: 400, display: "flex", justifyContent: "center" }}>
      <Icono nombre="calculadora" tam={300} />
    </div>
    <div style={{ position: "absolute", top: 600, left: 450, width: 180, height: 180, borderRadius: 90, background: C.amarillo, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 0 14px #141414, 0 20px 50px rgba(0,0,0,0.6)" }}>
      <span style={{ color: C.negro, fontWeight: 800, fontSize: 88, letterSpacing: -3 }}>VS</span>
    </div>
    <div style={{ position: "absolute", top: 920, left: 50, width: 440, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
      <div style={{ color: C.crema, fontWeight: 800, fontSize: 56, textAlign: "center", lineHeight: 1.05 }}>MONOTRIBUTO</div>
      <div style={{ color: C.gris, fontWeight: 600, fontSize: 36, textAlign: "center" }}>una cuota fija</div>
    </div>
    <div style={{ position: "absolute", top: 920, right: 50, width: 440, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
      <div style={{ color: C.crema, fontWeight: 800, fontSize: 52, textAlign: "center", lineHeight: 1.05 }}>RESPONSABLE INSCRIPTO</div>
      <div style={{ color: C.gris, fontWeight: 600, fontSize: 36, textAlign: "center" }}>IVA + Ganancias</div>
    </div>
    <div style={{ position: "absolute", top: 1380, left: 0, right: 0, textAlign: "center", color: C.crema, fontWeight: 700, fontSize: 50, padding: "0 100px" }}>
      La diferencia, explicada fácil
    </div>
    <Marca />
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 2. Monotributo de cero (escalera)
const PortadaCero: React.FC<PropsPortada> = ({ capitulo = 1, total = 5, tema = "" }) => (
  <AbsoluteFill style={{ background: C.negro }}>
    <Puntos />
    <div style={{ position: "absolute", top: 210, left: 90, right: 90 }}>
      <div style={{ color: C.gris, fontWeight: 700, fontSize: 38, letterSpacing: 6 }}>TODO SOBRE EL MONOTRIBUTO</div>
      <div style={{ color: C.crema, fontWeight: 800, fontSize: 124, lineHeight: 0.95, marginTop: 20, letterSpacing: -3, whiteSpace: "nowrap" }}>MONOTRIBUTO</div>
      <div style={{ display: "inline-block", position: "relative", marginTop: 18 }}>
        <div style={{ position: "absolute", left: -14, right: -14, top: 26, bottom: 6, background: C.amarillo, borderRadius: 12, rotate: "-1.5deg" }} />
        <span style={{ position: "relative", color: C.negro, fontWeight: 800, fontSize: 130 }}>de cero</span>
      </div>
    </div>
    {/* escalera: un escalón por capítulo, el actual resaltado */}
    <div style={{ position: "absolute", left: 90, right: 90, top: 820, height: 520, display: "flex", alignItems: "flex-end", gap: 18 }}>
      {Array.from({ length: total }).map((_, i) => {
        const n = i + 1;
        const actual = n === capitulo;
        const hecho = n < capitulo;
        return (
          <div key={i} style={{ flex: 1, height: 120 + i * 95, borderRadius: 14, background: actual ? C.amarillo : hecho ? "#4A4A3A" : C.negro2, border: `4px solid ${actual ? C.amarillo : C.grisOscuro}`, display: "flex", alignItems: "flex-start", justifyContent: "center", paddingTop: 18, position: "relative" }}>
            <span style={{ fontWeight: 800, fontSize: 60, color: actual ? C.negro : hecho ? C.crema : C.gris }}>{n}</span>
            {actual ? (
              <div style={{ position: "absolute", top: -190 }}>
                <Icono nombre="factura" tam={170} />
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
    <div style={{ position: "absolute", top: 1400, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 28 }}>
      <Cinta texto={`Cap. ${capitulo} de ${total}`} fondo={C.amarillo} giro={-2} tam={50} />
      <div style={{ color: C.crema, fontWeight: 800, fontSize: 64, textAlign: "center", padding: "0 90px", lineHeight: 1.1 }}>{tema}</div>
    </div>
    <Marca />
  </AbsoluteFill>
);

// ---------------------------------------------------------------- 3. Secretos del monotributo (un nicho por capítulo)
const PortadaSecretos: React.FC<PropsPortada> = ({ capitulo = 1, total = 5, icono = "lupa", nicho = "", grande, tema = "" }) => (
  <AbsoluteFill style={{ background: C.negro }}>
    <Puntos />
    <div style={{ position: "absolute", top: 200, left: 90, right: 90 }}>
      <div style={{ color: C.gris, fontWeight: 700, fontSize: 38, letterSpacing: 6 }}>LO QUE CASI NADIE TE CUENTA</div>
      <div style={{ color: C.crema, fontWeight: 800, fontSize: 132, lineHeight: 0.98, marginTop: 18 }}>SECRETOS</div>
      <div style={{ color: C.amarillo, fontWeight: 800, fontSize: 92, lineHeight: 1 }}>del monotributo</div>
    </div>
    {/* sello */}
    <div style={{ position: "absolute", top: 560, right: 60, width: 200, height: 200, borderRadius: 100, border: `10px solid ${C.amarillo}`, display: "flex", alignItems: "center", justifyContent: "center", rotate: "14deg" }}>
      <span style={{ color: C.amarillo, fontWeight: 800, fontSize: 36, textAlign: "center", lineHeight: 1 }}>¿SABÍAS?</span>
    </div>
    {/* nicho: ícono grande o texto gigante, con la lupa encima */}
    <div style={{ position: "absolute", top: 700, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div style={{ position: "relative", width: 560, height: 560, borderRadius: 280, background: "rgba(255,212,0,0.08)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {grande ? (
          <span style={{ color: C.amarillo, fontWeight: 800, fontSize: 280, letterSpacing: -10 }}>{grande}</span>
        ) : (
          <Icono nombre={icono} tam={380} />
        )}
        <div style={{ position: "absolute", right: -30, bottom: -20, rotate: "-8deg" }}>
          <Icono nombre="lupa" tam={230} />
        </div>
      </div>
    </div>
    <div style={{ position: "absolute", top: 1330, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
      <Cinta texto={nicho} fondo={C.amarillo} giro={-2} tam={58} />
      {tema ? <div style={{ color: C.crema, fontWeight: 700, fontSize: 46, textAlign: "center", padding: "0 100px" }}>{tema}</div> : null}
      <div style={{ color: C.gris, fontWeight: 700, fontSize: 32, letterSpacing: 4 }}>CAP. {capitulo} DE {total}</div>
    </div>
    <Marca />
  </AbsoluteFill>
);

export const Portada: React.FC<PropsPortada> = (p) => (
  <AbsoluteFill style={{ fontFamily }}>
    {p.tipo === "vs" ? <PortadaVS /> : p.tipo === "cero" ? <PortadaCero {...p} /> : <PortadaSecretos {...p} />}
  </AbsoluteFill>
);
