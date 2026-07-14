# Runtime config injection for Vercel.
# After setting MARKETLENS_API_BASE in the Vercel project environment,
# run:  npm run inject-config   (or let vercel.json buildCommand do it)
# Or paste your Railway/Render/Fly URL below and deploy.

window.MARKETLENS_API_BASE = window.MARKETLENS_API_BASE || "";
