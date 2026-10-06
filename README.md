# MADs — Mule Account Detection System

## TECHFORGE 2026 Submission

- **Team ID / Name:** T-23 — MADs
- **Team Members:** Anag Sharma
- **Problem Statement:** Mule Account Detection System
- **Selected Domain:** FinTech / Financial Crime Intelligence
- **Project Title:** MADs
- **Repository:** [github.com/anagsharma8755-a11y/T-23-MADs](https://github.com/anagsharma8755-a11y/T-23-MADs)

**Short description:** MADs is an explainable fraud-investigation platform that converts real transaction and blockchain records into searchable account networks, deterministic risk scores, and auditable investigation evidence. It combines bank-transaction analysis with a typed Elliptic++ Bitcoin graph while keeping source labels separate from automated findings and analyst decisions. Investigators can trace neighborhoods, review detector evidence, save decisions, and export reports from one responsive workspace.

## Project Overview

MADs (Mule Account Detection System) is a working fraud-investigation application that turns transaction CSVs into explainable account networks, reproducible risk scores, and persistent analyst decisions. The repository includes internet-sourced IBM AML and PaySim research CSV adapters; no frontend finding or graph is backed by a mock JSON fixture.

## Key Features

- Real IBM AML, PaySim, and official Elliptic++ ingestion workflows with schema validation and source provenance.
- Explainable fan-in/fan-out, circular-flow, pass-through, shared-attribute, and connected-path investigation signals.
- Interactive React Flow account and wallet/transaction graphs with bounded neighborhood expansion.
- Capability-gated blockchain detectors that never invent timestamps, edge amounts, balances, IPs, devices, or KYC data.
- Persistent analyst decisions, evidence reports, CSV/JSON exports, settings versioning, and immutable audit history.
- Automatic full CSV analysis after import, with atomic rejection and row-level reasons when validation fails.
- Clickable real-data metrics that open paginated source transactions or every flagged account's detector explanation.
- Strict versioned detector and severity thresholds with server-enforced ranges and preserved historical settings.
- A consolidated printable report covering every flagged account, supporting evidence, analyst status, and detailed-report links.
- Supervisor authentication, workspace isolation, CSRF protection, idempotent imports, and responsive 3D motion with reduced-motion support.
- Push-to-talk or typed investigation assistant with deterministic command fallback, bounded authorized tools, evidence links, request cancellation, and explicit decision confirmation.

## Figma and 3D interface

The live dashboard reference is available in [MADs — 3D Investigation Console](https://www.figma.com/design/1EYlBBhLDSgbSDFBws5pOT?node-id=1-2). The production UI uses a spatial navy/teal/amber system with an orbital risk globe, perspective grid, floating telemetry, depth-stacked metric cards, volumetric panels, and animated graph surfaces. Motion automatically collapses under `prefers-reduced-motion`.

## Setup & Installation Instructions

Prerequisites: Python 3.11+ and Node 20+.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./muletrace.db"
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.cli bootstrap --email supervisor@muletrace.local --password "DemoPass!123"
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in, or create a new workspace at `/signup`. Unknown routes render the animated MADs 404 page. API docs are at http://localhost:8000/docs.

### ElevenLabs voice narration and transcription

Typed assistant commands work without any AI credential. To enable microphone transcription, keep the API key on the backend and set:

```env
SPEECH_PROVIDER=openai
SPEECH_API_KEY=replace-with-a-server-side-key
SPEECH_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
```

The assistant opens after login and narrates a concise product tour. With `SPEECH_PROVIDER=elevenlabs`, the backend uses ElevenLabs Scribe for push-to-talk transcription and ElevenLabs text-to-speech for replies. MADs limits recording duration and size, does not retain raw audio, and never exposes the API key to Vite. Microphone access is still requested only after pressing the push-to-talk control; the welcome narration never activates the microphone.

Copy the ElevenLabs settings from `.env.example` into `backend/.env`, set `ELEVENLABS_API_KEY`, and restart the API. `ELEVENLABS_VOICE_ID`, `ELEVENLABS_TTS_MODEL`, and `ELEVENLABS_STT_MODEL` can be changed without rebuilding the frontend. If the key is absent, the UI remains usable with typed commands and the browser's local speech voice.

## Dataset / API Information

### Internet-sourced CSV datasets

The active local demo uses `samples/ibm-aml-transactions.csv`: a deterministic 15,000-row, network-rich slice of IBM's public AML benchmark. It contains 5,177 source-labelled laundering transactions plus connected ordinary transactions. MADs ignores the labels during rule detection; they are preserved separately in `samples/ibm-aml-source-labels.csv` for provenance. The prepared dataset produces real circular and pass-through graph findings with the default rules.

Regenerate the CSV files directly from their public sources:

```bash
python scripts/prepare_ibm_aml.py --rows 15000
python scripts/prepare_paysim.py --rows 15000
```

The scripts download CSV archives, adapt them to MADs' CSV contract, and never use JSON as the investigation dataset. See `samples/IBM_AML_SOURCE.md` and `samples/PAYSIM_SOURCE.md` for attribution and limitations. Both are synthetic research benchmarks because identifiable bank transaction data is not publicly shareable.

### Elliptic++ historical Bitcoin data

MADs also supports the official [Elliptic++ repository](https://github.com/git-disl/EllipticPlusPlus) as a separate blockchain domain. Download or clone the source outside the Git repository (the recommended local location is the ignored `.external/EllipticPlusPlus` directory), then import a reproducible bounded subset:

```powershell
cd backend
.venv\Scripts\python -m app.cli import-elliptic `
  --source-dir "..\.external\EllipticPlusPlus" `
  --email supervisor@muletrace.local `
  --max-transactions 500 `
  --name "Elliptic++ Official — 500 Transaction Demo"
```

The supervisor upload workflow under **Data & uploads → Elliptic++ Blockchain Dataset** accepts these eight official CSVs: `wallets_features.csv`, `wallets_classes.csv`, `AddrAddr_edgelist.csv`, `AddrTx_edgelist.csv`, `TxAddr_edgelist.csv`, `txs_features.csv`, `txs_classes.csv`, and `txs_edgelist.csv`. Imports stream the files, verify exact schemas and references, calculate SHA-256 checksums, and are idempotent for an identical source manifest and subset rule.

The laptop subset is label-blind: it selects the first requested transaction feature records in official file order, retains every official address→transaction and transaction→address relationship incident to those transaction nodes, and retains address→address and transaction→transaction relationships only when both endpoints are selected. It never fabricates pairwise wallet transfers or allocates node-level BTC aggregates to edges. Wallet addresses and transaction IDs remain distinct types. The UI prominently identifies all results as a bounded subset.

Elliptic++ supplies ordinal time steps 1–49, not exact timestamps. MADs does not convert them into calendar dates. Structural fan-in/fan-out and connected-path detectors are enabled. Rapid forwarding, forwarded-value ratios, and shared device/IP/KYC detection remain disabled because the necessary source fields are absent. Reference labels use the authors' verified mapping—1 illicit, 2 licit, 3 unknown—and remain separate from automated scores and analyst decisions. Unknown is never treated as licit. Evaluation joins known labels only after scoring and reports its sample and subset scope; no model or accuracy result is invented.

Attribution: V. Bellei et al., “The Shape of Money Laundering: Subgraph Representation Learning on the Blockchain with the Elliptic2 Dataset,” KDD 2023, [DOI 10.1145/3580305.3599803](https://doi.org/10.1145/3580305.3599803). Review the repository and dataset's current access/citation terms before use. The code repository's license must not be assumed to grant unrestricted redistribution of the downloaded data; raw CSVs and bounded source extracts are intentionally excluded from Git.

### PostgreSQL + Neo4j / Docker

Copy `.env.example` to `.env`, replace `SECRET_KEY` and `NEO4J_PASSWORD`, then run `docker compose up --build`. This starts PostgreSQL for durable application records and Neo4j for the dataset-scoped account/transfer network. Bootstrap the first supervisor with:

```powershell
docker compose exec api python -m app.cli bootstrap --email supervisor@example.com --password "replace-this-password"
```

The local build includes workspace sign-up for the hackathon flow. Supervisors can also create users through the protected API.

Neo4j stores `(Account)-[:TRANSFER]->(Account)` relationships and powers one- and two-hop expansion. PostgreSQL remains the source of truth, while Pandas validates and normalizes CSV imports and NetworkX runs the explainable detectors. If Neo4j is disabled or temporarily unavailable, the API falls back to a bounded SQL expansion so an 18-hour demo remains usable.

## Technology Stack

- React + Vite + Tailwind CSS for the interface
- React Flow for the interactive network and Recharts for risk/pattern charts
- FastAPI + Pandas + NetworkX for ingestion and deterministic detection
- PostgreSQL + SQLAlchemy for users, datasets, findings, reviews, and audit history
- Neo4j for account relationships and graph neighborhood queries
- Vercel Functions for the same-origin React/FastAPI deployment and Supabase Postgres for durable production data

The root `vercel.json` builds the Vite frontend and routes `/api/*` to the FastAPI ASGI function. Production uses same-origin requests, secure cookies, a private `mads` Postgres schema, Supabase transaction pooling, and encrypted Vercel environment variables. Never create a `VITE_` variable for `DATABASE_URL`, `SECRET_KEY`, or speech-provider credentials: `VITE_` values are embedded into browser bundles. The legacy `render.yaml` remains available for self-hosted/container deployments.

## Detection method

- Rapid fan-in/fan-out allocates incoming funds FIFO to later outgoing transfers inside one currency/window. Each incoming unit is consumed at most once.
- Circular transfer search is chronological, limited by time, path length, and 50,000 search expansions.
- Pass-through chains are limited to 3–6 accounts and cap each leg by the immediately preceding leg.
- Shared attributes consider only accounts with known recent creation dates, and their contribution is capped at 15.
- Detector contributions use the maximum contribution per detector/account, so overlapping findings cannot inflate scores without limit.

Risk is a review-prioritization score, not a calibrated probability of fraud. Transfer-derived balances cover only imported data. Currencies are never combined.

## Tests and demo files

```powershell
cd backend
.venv\Scripts\pytest
cd ..\frontend
npm run build
cd ..
python scripts/generate_demo.py
```

Tests cover auth/CSRF/roles, workspace isolation, atomic invalid imports, duplicates and leading zeros, currency separation, temporal boundaries, partial forwarding and fund reuse, positive/negative detector behavior, stable capped scores, retry, audit, review persistence, and exports. Elliptic++ tests additionally cover exact schema validation, missing references, atomic failure, repeated-import idempotency, label/score separation, subset graph consistency, detector capability gating, and typed neighborhood expansion.

## API surface

OpenAPI documents `/api/auth/*`, uploads, datasets, summaries, analysis jobs/retry, scores/findings/account evidence, bounded network expansion, decisions, settings, audit, samples, demo load, exports, reports, health, and readiness. List endpoints use bounded pages; score queues support search/filter/sort.

`GET /api/demo/evaluation/{run_id}` reports strict account-level precision/recall, true positives, false positives, and false negatives only for the deterministic synthetic dataset. Ground-truth labels remain outside detector input.

## Screenshots / Demo Information

The primary demo runs at `http://localhost:5173/app` after completing the setup above. The interface includes the overview dashboard, prioritized investigations, bank-network explorer, Elliptic++ wallet/transaction graph, import supervisor, replay lab, audit reports, settings, authentication, and a custom 404 state. The associated editable UI reference is linked in the **Figma and 3D interface** section.

### Three-minute judging flow

1. Sign in as the local supervisor and select the imported **IBM AML · Network Investigation Dataset**.
2. Run analysis and show the persistent progress indicator and evidence-backed totals.
3. Open **Flagged accounts** and select a high-risk account.
4. In **Network investigation**, expand to two hops and point out arrows, risk colors, grouped edges, and exact transfer evidence.
5. Explain the detector calculation and its limitation text; record **Confirmed suspicious** with a note.
6. Refresh to show persistence, then open the printable report and export CSV/JSON.
7. Open **Elliptic++ Bitcoin** to show the real bounded blockchain subset and capability gating, then show **Detection settings** and **Audit history**.

### 60-second voice-assistant demo

1. Open **Elliptic++ Bitcoin** or **Network explorer**, then press **Voice assistant**.
2. Say or type “Show high-risk wallets,” review the editable transcript, and submit it to filter the real investigation queue.
3. Say “Open wallet …” and use the on-screen identifier picker if speech produced an ambiguous partial address.
4. Ask “Why was this wallet flagged?” to show the automated score, reasons, limitations, and clickable evidence references.
5. Ask “Expand this network,” then “Show the supporting transactions” to update the bounded graph and open its evidence panel.
6. Ask “Summarize this investigation” for an evidence-grounded case summary that keeps dataset labels, automated findings, and analyst decisions separate.
7. Say “Confirm suspicious.” MADs opens the exact wallet and proposed decision, but requires a written analyst note and an explicit on-screen confirmation before saving to the audit trail.

## Architecture / Workflow

`CSV files → Pandas validation → PostgreSQL/SQLite storage → NetworkX detectors → Neo4j/SQL neighborhood expansion → FastAPI → React dashboard and evidence reports`

React/Vite calls a FastAPI service with HttpOnly server-side sessions, double-submit CSRF validation, Argon2 password hashing, and workspace-scoped SQLAlchemy queries. React Flow renders the Neo4j-backed account network; Recharts renders real run aggregates. Local analysis uses FastAPI background execution; Vercel completes each bounded analysis inside the function invocation so work is not lost when a serverless instance is frozen.

## Limitations & Future Scope

- SQLite is intended for a single-laptop demo; PostgreSQL and Neo4j are recommended for team or deployed environments.
- Vercel analysis is intentionally bounded by the function duration and request-size limits. Large production imports should use object storage plus a database-claiming worker queue.
- Public research datasets do not contain every field used by production banks. Detectors are disabled when timestamps, edge values, balances, device IDs, IPs, or KYC attributes are unavailable.
- MADs makes no FX conversion, identity conclusion, calibrated fraud-probability claim, or complete account-balance claim.
- Future work includes streaming ingestion, case collaboration, stronger entity resolution, model-assisted prioritization with temporal validation, and production observability.

## Team Members

- **Anag Sharma** — Team T-23
