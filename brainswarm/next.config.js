/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Helps dev server proxy WS to FastAPI in local dev
    return [{ source: "/dashboard/ws", destination: "http://localhost:8001/dashboard/ws" }];
  },
};

module.exports = nextConfig;