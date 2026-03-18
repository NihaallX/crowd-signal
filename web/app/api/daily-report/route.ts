export async function GET() {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8000"

  try {
    const res = await fetch(`${backend}/api/v1/daily-report`, { cache: "no-store" })
    const data = await res.json()
    return Response.json(data, { status: res.status })
  } catch {
    return Response.json({ status: "error", message: "Failed to fetch daily report" }, { status: 502 })
  }
}
