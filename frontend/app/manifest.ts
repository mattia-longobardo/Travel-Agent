import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Travel Agent",
    short_name: "Travel Agent",
    description: "AI travel planning console",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0f8f8f",
    icons: [
      { src: "/icons/192", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/512", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icons/512", sizes: "512x512", type: "image/png", purpose: "any" },
    ],
  };
}
