"use client";
import { useEffect, useState } from "react";

const QUERY = "(max-width: 1023px)";

/**
 * True quando il viewport è sotto i 1024px, lo stesso breakpoint a cui compare la
 * sidebar desktop. Parte sempre `false` (SSR e primo
 * render client) e si aggiorna dopo il mount: così il markup idratato combacia
 * con quello del server e non c'è hydration mismatch. Il desktop renderizza
 * per un frame anche su mobile, poi avviene lo switch.
 */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const update = () => setIsMobile(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, []);

  return isMobile;
}
