/** @type {import('next').NextConfig} */
const rawBackend =
  process.env.API_URL ||
  process.env.BACKEND_URL ||
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

const normalizedBackend = rawBackend.replace(/\/api\/v1\/?$/, "");

const nextConfig = {
  env: {
    // Expose API_URL without requiring PUBLIC prefix in Vercel
    API_URL: rawBackend,
    NEXT_PUBLIC_API_URL: rawBackend,
  },
  webpack: (config, { dev }) => {
    if (!dev) {
      config.cache = false;
    }
    return config;
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${normalizedBackend}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
