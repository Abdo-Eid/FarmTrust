/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    transpilePackages: ["@react-pdf/renderer"],
    turbopack: {
        root: __dirname,
    },
};

module.exports = nextConfig;
