// frontend/next.config.ts
import type { NextConfig } from "next";
const backend = process.env.BACKEND_URL ?? "http://travel-backend:8000";
const nextConfig: NextConfig = {
  devIndicators: false,
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
export default nextConfig;
