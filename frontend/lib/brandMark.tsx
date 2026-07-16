import { ImageResponse } from "next/og";

/**
 * Shared artwork for every generated raster icon (apple-touch + PWA maskable), so the
 * favicon, home-screen icon and installed-app icon all match the Figma brand mark.
 *
 * The white paper-plane lives on a transparent 100x100 canvas; raster icons paint it
 * over a full-bleed teal square and let the OS apply its own rounded mask.
 */
export const BRAND_TEAL = "#0f8f8f";

const PLANE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g fill="#ffffff"><circle cx="88" cy="14" r="7"/><path d="M78 24 L10 30 L40 52 Z" opacity="0.82"/><path d="M78 24 L40 52 L34 78 Z"/></g></svg>`;
const PLANE_DATA_URI = `data:image/svg+xml;utf8,${encodeURIComponent(PLANE_SVG)}`;

/**
 * Full-bleed teal square with the plane inside the maskable safe zone (~60% centred).
 * Used for the apple-touch icon (iOS rounds it) and the PWA maskable icons.
 */
export function maskableIcon(size: number) {
  const inner = Math.round(size * 0.6);
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: BRAND_TEAL,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img width={inner} height={inner} src={PLANE_DATA_URI} alt="" />
      </div>
    ),
    { width: size, height: size },
  );
}
