import React from "react";
import { Composition } from "remotion";
import { Promo } from "./Promo";
import { Explicativo, FPS, duracionTotal, PropsExplicativo } from "./Explicativo";
import muestra from "../muestras/capitulo.json";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Promo"
      component={Promo}
      durationInFrames={8 * 30}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ precio: 4000, producto: "yogur" }}
    />
    <Composition
      id="Explicativo"
      component={Explicativo}
      durationInFrames={duracionTotal(muestra as PropsExplicativo)}
      fps={FPS}
      width={1080}
      height={1920}
      defaultProps={muestra as PropsExplicativo}
      calculateMetadata={({ props }) => ({ durationInFrames: duracionTotal(props as PropsExplicativo) })}
    />
  </>
);
