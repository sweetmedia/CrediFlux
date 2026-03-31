/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  env: {
    API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'http',
        hostname: '10.0.0.93',
        port: '8600',
        pathname: '/media/**',
      },
      {
        protocol: 'http',
        hostname: 'sweetmediabox',
        port: '8600',
        pathname: '/media/**',
      },
      {
        protocol: 'https',
        hostname: '*.trycloudflare.com',
        pathname: '/media/**',
      },
    ],
  },
}

module.exports = nextConfig
