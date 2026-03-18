"use client"

import { useEffect, useState } from "react"

const PERSONAS = [
  { name: "RETAIL_BULL", status: "MOMENTUM", value: "+0.58" },
  { name: "RETAIL_BEAR", status: "DEFENSIVE", value: "-0.19" },
  { name: "WHALE", status: "ACCUMULATING", value: "+0.33" },
  { name: "ALGO", status: "TREND_FOLLOW", value: "+0.47" },
]

export function StatusCard() {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setTick((t) => t + 1)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b-2 border-foreground px-4 py-2">
        <span className="text-[10px] tracking-widest text-muted-foreground uppercase">
          persona.cluster_state
        </span>
        <span className="text-[10px] tracking-widest text-muted-foreground">
          {`TICK:${String(tick).padStart(4, "0")}`}
        </span>
      </div>
      <div className="flex-1 flex flex-col p-4 gap-0">
        {/* Table header */}
        <div className="grid grid-cols-3 gap-2 border-b border-border pb-2 mb-2">
          <span className="text-[9px] tracking-[0.15em] uppercase text-muted-foreground">Persona</span>
          <span className="text-[9px] tracking-[0.15em] uppercase text-muted-foreground">Status</span>
          <span className="text-[9px] tracking-[0.15em] uppercase text-muted-foreground text-right">Mean Stance</span>
        </div>
        {PERSONAS.map((persona) => (
          <div
            key={persona.name}
            className="grid grid-cols-3 gap-2 py-2 border-b border-border last:border-none"
          >
            <span className="text-xs font-mono text-foreground">{persona.name}</span>
            <div className="flex items-center gap-2">
              <span
                className="h-1.5 w-1.5"
                style={{
                  backgroundColor: persona.status === "DEFENSIVE" ? "hsl(var(--muted-foreground))" : "#ea580c",
                }}
              />
              <span className="text-xs font-mono text-muted-foreground">{persona.status}</span>
            </div>
            <span className="text-xs font-mono text-foreground text-right">{persona.value}</span>
          </div>
        ))}
        {/* Throughput bar */}
        <div className="mt-auto pt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] tracking-[0.15em] uppercase text-muted-foreground">
              Bullish Cluster Density
            </span>
            <span className="text-[9px] font-mono text-foreground">71%</span>
          </div>
          <div className="h-2 w-full border border-foreground">
            <div className="h-full bg-foreground" style={{ width: "71%" }} />
          </div>
          <div className="mt-3 flex items-center justify-between text-[9px] tracking-[0.15em] uppercase text-muted-foreground">
            <span>Herd Flag</span>
            <span className="font-mono text-foreground">ONCE @ TICK 5+</span>
          </div>
        </div>
      </div>
    </div>
  )
}
