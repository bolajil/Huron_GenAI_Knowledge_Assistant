/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // API rewrites to FastAPI backend
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
  
  // Image domains
  images: {
    domains: ['localhost', 'api.huronconsultinggroup.com'],
  },
};

module.exports = nextConfig;
