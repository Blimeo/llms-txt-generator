import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  serverExternalPackages: ['@google-cloud/tasks'],
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Externalize Google Cloud packages for server-side rendering
      config.externals.push('@google-cloud/tasks');
    }
    return config;
  },
};

export default nextConfig;
