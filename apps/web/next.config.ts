// @ts-check

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow large file uploads for document processing
  experimental: {
    serverActions: {
      bodySizeLimit: "50mb",
    },
  },
};

export default nextConfig;
