# Crowd Signal

Crowd Signal is an AI-assisted market crowd simulation system for intraday sentiment mapping.

Instead of generating a single deterministic prediction, the system models how multiple trading personas react to a catalyst (earnings, headlines, social momentum) over a short time horizon and returns a probabilistic crowd-state summary.

## What It Does

- Simulates trader personas such as retail, whales, and algos.
- Applies weighted peer influence over iterative ticks.
- Adds catalyst gravity to represent persistent narrative pressure.
- Produces aggregate stance, probability-up/down, and persona-level confidence.
- Exposes a FastAPI simulation endpoint used by a Next.js frontend.

## Core Idea

Markets often move because of crowd behavior before fundamentals fully settle.

Crowd Signal is designed as a decision-support layer:
- Assistive, not automated.
- Probabilistic, not certain.
- Explainable by design.

## Architecture

- Backend API: FastAPI in `api/`
- Simulation engine: persona dynamics in `engine/sim/`
- Data connectors: market/news/social connectors in `engine/data/`
- Frontend: Next.js app in `web/`

## API Quick Start

Main endpoint:
- `POST /api/v1/simulate`

Example payload:

```json
{
  "ticker": "NVDA",
  "catalyst": "Earnings beat by 20%",
  "horizon_minutes": 120
}
```

Example response shape:

```json
{
  "ticker": "NVDA",
  "aggregate_stance": 0.32,
  "probability_up": 0.61,
  "probability_down": 0.24,
  "persona_breakdown": {
    "retail_bull": { "stance": 0.48, "confidence": 0.72 },
    "retail_bear": { "stance": -0.18, "confidence": 0.59 },
    "whale": { "stance": 0.35, "confidence": 0.68 },
    "algo": { "stance": 0.22, "confidence": 0.64 }
  }
}
```

## Local Development

### Backend

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 3001
```

### Frontend

```bash
cd web
corepack pnpm install
corepack pnpm run dev
```

## License and Usage Rights

This project is intentionally **not open source**.

- Copyright (c) 2026 Crowd Signal Team.
- All rights reserved.
- No permission is granted to use, copy, modify, distribute, sublicense, or sell this software without prior written authorization.

See [LICENSE](LICENSE) for full terms.

## Important Disclaimer

Crowd Signal provides probabilistic analysis for research and decision support only.
It is not financial advice, not investment solicitation, and not an execution system.
