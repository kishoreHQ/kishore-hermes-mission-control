/** @type {import('next').NextConfig} */
const path = require("path");

const internalApi = process.env.INTERNAL_API_URL || "http://127.0.0.1:8000";

const nextConfig = {
  transpilePackages: ["@hermes/ui", "@hermes/sdk"],
  outputFileTracingRoot: path.join(__dirname, "../../"),
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${internalApi}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
