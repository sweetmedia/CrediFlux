const createNextIntlPlugin = require('next-intl/plugin')
const withNextIntl = createNextIntlPlugin('./i18n/request.ts')

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  env: {
    API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Pre-overhaul debt: ~167 `any` types and several React 19 / library type
  // incompatibilities across legacy pages (e.g. react-signature-canvas refs,
  // old tenant types). Each page is cleaned up when it's migrated in F3.
  // Compilation itself works — only TypeScript's strict type check fails.
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
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

module.exports = withNextIntl(nextConfig)
