import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Poppins";

const { fontFamily } = loadFont("normal", { weights: ["400", "600", "700", "800"], subsets: ["latin"] });

// Colores de @ramacontable
const NEGRO = "#141414";
const NEGRO_2 = "#1F1F1F";
const AMARILLO = "#FFD400";
const CREMA = "#F6F0E2";
const GRIS = "#8C8C8C";

const SUAVE = Easing.bezier(0.16, 1, 0.3, 1);
const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const pesos = (n: number) => "$ " + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");

type Props = { precio: number; producto: string };

// --- piezas -----------------------------------------------------------------

const Fondo: React.FC<{ frame: number }> = ({ frame }) => {
  // puntitos que se mueven lento todo el tiempo: el video nunca queda quieto
  const puntos = [];
  for (let i = 0; i < 9; i++) {
    for (let j = 0; j < 16; j++) {
      const x = i * 130 + 40 + Math.sin((frame + j * 9) / 40) * 6;
      const y = ((j * 130 + frame * 0.6) % 2080) - 80;
      puntos.push(
        <div
          key={`${i}-${j}`}
          style={{ position: "absolute", left: x, top: y, width: 6, height: 6, borderRadius: 3, background: "#2A2A2A" }}
        />
      );
    }
  }
  return (
    <AbsoluteFill style={{ background: NEGRO }}>
      {puntos}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, rgba(255,212,0,0.07), transparent 60%)" }} />
    </AbsoluteFill>
  );
};

const Vaso: React.FC<{ color?: string }> = ({ color = CREMA }) => (
  <svg width="210" height="250" viewBox="0 0 210 250">
    <path d="M30 40 L180 40 L160 235 Q158 245 148 245 L62 245 Q52 245 50 235 Z" fill="none" stroke={color} strokeWidth="7" strokeLinejoin="round" />
    <rect x="18" y="26" width="174" height="20" rx="8" fill="none" stroke={color} strokeWidth="7" />
    <path d="M41 105 L169 105 L162 175 L48 175 Z" fill={AMARILLO} opacity="0.9" />
    <circle cx="105" cy="140" r="22" fill="none" stroke={NEGRO} strokeWidth="6" />
    <path d="M97 140 Q105 124 113 140 Q105 156 97 140 Z" fill={NEGRO} />
    <line x1="150" y1="0" x2="128" y2="60" stroke={color} strokeWidth="7" strokeLinecap="round" />
  </svg>
);

const Etiqueta: React.FC<{ texto: string; lleno?: boolean; style?: React.CSSProperties }> = ({ texto, lleno, style }) => (
  <div
    style={{
      fontFamily,
      fontWeight: 800,
      fontSize: 58,
      padding: "10px 30px",
      border: `5px solid ${lleno ? AMARILLO : CREMA}`,
      background: lleno ? AMARILLO : "transparent",
      color: lleno ? NEGRO : CREMA,
      borderRadius: 12,
      whiteSpace: "nowrap",
      ...style,
    }}
  >
    {texto}
  </div>
);

// --- escena -----------------------------------------------------------------

export const Promo: React.FC<Props> = ({ precio }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = (desde: number, damping = 12, mass = 0.8) =>
    spring({ frame: frame - desde, fps, config: { damping, mass, stiffness: 120 } });

  const segunda = precio * 0.5;
  const total = precio + segunda;
  const sinPromo = precio * 2;
  const ahorro = Math.round((1 - total / sinPromo) * 100);

  // salida: toda la escena se va a la izquierda y asoma el paso 2
  const salida = interpolate(frame, [205, 235], [0, 1], { ...CLAMP, easing: Easing.bezier(0.7, 0, 0.84, 0) });

  // los productos suben y se achican para dejarle lugar al ticket
  const reacomodo = interpolate(frame, [104, 128], [0, 1], { ...CLAMP, easing: SUAVE });

  const titulo = "La 2.ª al";
  const marcador = interpolate(frame, [18, 34], [0, 1], { ...CLAMP, easing: SUAVE });

  const sticker = sp(70, 9, 0.6);
  const cambio = interpolate(frame, [86, 98], [0, 1], { ...CLAMP, easing: SUAVE });
  const ticket = sp(112, 16);
  const contador = interpolate(frame, [150, 175], [precio, total], { ...CLAMP, easing: SUAVE });
  const tachado = interpolate(frame, [178, 190], [0, 100], { ...CLAMP, easing: SUAVE });
  const badge = sp(184, 8, 0.5);
  const latido = 1 + Math.max(0, Math.sin((frame - 195) / 5)) * 0.04 * (frame > 195 ? 1 : 0);

  return (
    <AbsoluteFill style={{ fontFamily, overflow: "hidden" }}>
      <Fondo frame={frame} />

      {/* cabecera: paso y puntitos */}
      <div style={{ position: "absolute", top: 140, left: 90, right: 90, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ color: AMARILLO, fontWeight: 700, fontSize: 34, letterSpacing: 4 }}>
          PASO {salida > 0.5 ? 2 : 1} DE 4
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          {[0, 1, 2, 3].map((k) => {
            const activo = k === 0 ? 1 - salida : k === 1 ? salida : 0;
            return (
              <div
                key={k}
                style={{
                  height: 18,
                  width: 18 + 40 * activo,
                  borderRadius: 9,
                  background: activo > 0.5 ? AMARILLO : "#3A3A3A",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* escena del paso 1 */}
      <AbsoluteFill style={{ translate: `${-1080 * salida}px 0px`, opacity: 1 - salida * 0.6 }}>
        {/* título: entra letra por letra y el "50 %" se pinta con marcador */}
        <div style={{ position: "absolute", top: 230, left: 90, display: "flex", alignItems: "baseline", gap: 24 }}>
          <div style={{ display: "flex", color: CREMA, fontWeight: 800, fontSize: 110 }}>
            {titulo.split("").map((c, i) => (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  whiteSpace: "pre",
                  opacity: interpolate(frame, [i * 1.2, i * 1.2 + 8], [0, 1], CLAMP),
                  translate: `0px ${interpolate(frame, [i * 1.2, i * 1.2 + 12], [60, 0], { ...CLAMP, easing: SUAVE })}px`,
                }}
              >
                {c}
              </span>
            ))}
          </div>
          <div style={{ position: "relative", fontWeight: 800, fontSize: 110 }}>
            <div style={{ position: "absolute", left: -10, top: 18, bottom: 8, width: `calc(${marcador * 100}% + 20px)`, background: AMARILLO, borderRadius: 8 }} />
            <span style={{ position: "relative", color: marcador > 0.4 ? NEGRO : CREMA }}>50 %</span>
          </div>
        </div>

        {/* productos con precios */}
        <div
          style={{
            position: "absolute",
            top: 470,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            gap: 120,
            translate: `0px ${-60 * reacomodo}px`,
            scale: String(1 - 0.2 * reacomodo),
          }}
        >
          {[0, 1].map((k) => {
            const entra = sp(30 + k * 8, 11);
            const flota = Math.sin((frame + k * 20) / 16) * 6;
            const sacudon = k === 1 ? Math.sin(frame * 1.7) * 8 * Math.max(0, 1 - Math.abs(frame - 76) / 8) : 0;
            const tag = sp(52 + k * 6, 10, 0.6);
            return (
              <div key={k} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40 }}>
                <div style={{ translate: `${(1 - entra) * 900 + sacudon}px ${flota}px`, opacity: Math.min(1, entra * 1.5) }}>
                  <Vaso />
                </div>
                <div style={{ position: "relative", height: 100, width: 330, display: "flex", justifyContent: "center", scale: String(tag) }}>
                  {k === 0 ? (
                    <Etiqueta texto={pesos(precio)} />
                  ) : (
                    <>
                      <div style={{ position: "absolute", translate: `0px ${70 * cambio}px`, opacity: 1 - cambio }}>
                        <Etiqueta texto={pesos(precio)} />
                      </div>
                      <div style={{ position: "absolute", translate: `0px ${-70 * (1 - cambio)}px`, opacity: cambio }}>
                        <Etiqueta texto={pesos(segunda)} lleno />
                      </div>
                    </>
                  )}
                </div>
              </div>
            );
          })}
          {/* sticker −50 % que se pega con rebote */}
          <div
            style={{
              position: "absolute",
              left: 650,
              top: 30,
              background: AMARILLO,
              color: NEGRO,
              fontWeight: 800,
              fontSize: 64,
              padding: "8px 26px",
              borderRadius: 10,
              boxShadow: "0 18px 30px rgba(0,0,0,0.45)",
              scale: String(interpolate(sticker, [0, 1], [2.4, 1])),
              rotate: `${interpolate(sticker, [0, 1], [-25, -8])}deg`,
              opacity: frame >= 70 ? Math.min(1, sticker * 3) : 0,
            }}
          >
            −50 %
          </div>
        </div>

        {/* ticket que sube y se arma línea por línea */}
        <div
          style={{
            position: "absolute",
            left: 110,
            right: 110,
            top: 980,
            translate: `0px ${(1 - ticket) * 1100}px`,
            filter: "drop-shadow(0 30px 40px rgba(0,0,0,0.5))",
          }}
        >
          <div style={{ background: CREMA, padding: "44px 56px 40px", color: NEGRO }}>
            <div style={{ textAlign: "center", letterSpacing: 6, fontSize: 28, fontWeight: 600, color: GRIS, marginBottom: 26 }}>
              TICKET · EJEMPLO
            </div>
            {[
              ["1.ª unidad", pesos(precio), 128],
              ["2.ª al 50 %", pesos(segunda), 138],
            ].map(([a, b, desde]) => (
              <div
                key={String(a)}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 44,
                  marginBottom: 14,
                  opacity: interpolate(frame, [Number(desde), Number(desde) + 8], [0, 1], CLAMP),
                  translate: `${interpolate(frame, [Number(desde), Number(desde) + 12], [-60, 0], { ...CLAMP, easing: SUAVE })}px 0px`,
                }}
              >
                <span style={{ fontWeight: 400 }}>{a}</span>
                <span style={{ fontWeight: 700 }}>{b}</span>
              </div>
            ))}
            <div style={{ height: 4, margin: "22px 0", background: `repeating-linear-gradient(90deg, ${GRIS} 0 16px, transparent 16px 28px)`, width: `${interpolate(frame, [144, 158], [0, 100], CLAMP)}%` }} />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", opacity: interpolate(frame, [148, 156], [0, 1], CLAMP) }}>
              <span style={{ fontSize: 48, fontWeight: 700 }}>TOTAL</span>
              <span style={{ fontSize: 96, fontWeight: 800 }}>{pesos(contador)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 40, color: GRIS, marginTop: 8, opacity: interpolate(frame, [176, 184], [0, 1], CLAMP) }}>
              <span>sin promo</span>
              <span style={{ position: "relative" }}>
                {pesos(sinPromo)}
                <span style={{ position: "absolute", left: 0, top: "52%", height: 4, width: `${tachado}%`, background: GRIS }} />
              </span>
            </div>
          </div>
          {/* borde cortado del ticket */}
          <div style={{ height: 26, background: `linear-gradient(-45deg, transparent 13px, ${CREMA} 0), linear-gradient(45deg, transparent 13px, ${CREMA} 0)`, backgroundSize: "26px 26px", backgroundRepeat: "repeat-x" }} />
          {/* badge de ahorro */}
          <div
            style={{
              position: "absolute",
              right: -40,
              top: -60,
              background: NEGRO_2,
              border: `5px solid ${AMARILLO}`,
              color: AMARILLO,
              fontWeight: 800,
              fontSize: 46,
              padding: "14px 26px",
              borderRadius: 60,
              scale: String(badge * latido),
              rotate: "6deg",
            }}
          >
            Ahorrás {ahorro} %
          </div>
        </div>

        {/* subtítulo con el número resaltado */}
        <div
          style={{
            position: "absolute",
            bottom: 170,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            gap: 18,
            fontSize: 64,
            fontWeight: 800,
            opacity: interpolate(frame, [160, 168], [0, 1], CLAMP),
            translate: `0px ${interpolate(frame, [160, 172], [30, 0], { ...CLAMP, easing: SUAVE })}px`,
          }}
        >
          <span style={{ color: CREMA }}>y pagás</span>
          <span style={{ background: AMARILLO, color: NEGRO, padding: "0 16px", borderRadius: 8 }}>{pesos(total)}</span>
        </div>
      </AbsoluteFill>

      {/* asoma el paso 2 */}
      <AbsoluteFill style={{ translate: `${1080 * (1 - salida)}px 0px` }}>
        <div style={{ position: "absolute", top: 230, left: 90, color: CREMA, fontWeight: 800, fontSize: 110 }}>
          El{" "}
          <span style={{ background: AMARILLO, color: NEGRO, padding: "0 14px", borderRadius: 8 }}>3x2</span>
        </div>
      </AbsoluteFill>

      <div style={{ position: "absolute", bottom: 60, right: 80, color: GRIS, fontWeight: 600, fontSize: 30 }}>@ramacontable</div>
    </AbsoluteFill>
  );
};
