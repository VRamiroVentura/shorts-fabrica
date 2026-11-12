import React from "react";
import { Composition } from "remotion";
import { Promo } from "./Promo";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Promo"
    component={Promo}
    durationInFrames={8 * 30}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ precio: 4000, producto: "yogur" }}
  />
);
