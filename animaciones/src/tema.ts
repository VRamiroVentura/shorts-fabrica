import { Easing } from "remotion";
import { loadFont } from "@remotion/google-fonts/Poppins";

export const { fontFamily } = loadFont("normal", { weights: ["400", "600", "700", "800"], subsets: ["latin"] });

// Colores de @ramacontable
export const C = {
  negro: "#141414",
  negro2: "#1F1F1F",
  amarillo: "#FFD400",
  crema: "#F6F0E2",
  gris: "#8C8C8C",
  grisOscuro: "#3A3A3A",
};

export const SUAVE = Easing.bezier(0.16, 1, 0.3, 1);
export const ENTRA_RAPIDO = Easing.bezier(0.7, 0, 0.84, 0);
export const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
