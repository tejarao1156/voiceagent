/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Remove standalone output for dev mode - it's causing issues with proxy
  // output: 'standalone', // Only use in production
  // Configure for proxy setup
  async rewrites() {
    return [];
  },
};

module.exports = nextConfig;

