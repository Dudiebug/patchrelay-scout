# PatchRelay Scout

A small, read-only opportunity scout for finding legitimate public paid software work.

It searches public GitHub issues for explicit bounty/reward language, rejects unsafe work and copied reward claims that lack a verified payout source, then ranks the remainder by estimated hourly value.

## Run

```bash
PYTHONPATH=src python3 -m money_maker scan
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Development

```bash
git clone https://github.com/Dudiebug/patchrelay-scout.git
cd patchrelay-scout
PYTHONPATH=src python3 -m money_maker scan
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The scan uses only unauthenticated `GET` requests to GitHub's public API. It does not clone repositories, create accounts, send messages, make purchases, submit work, or handle credentials. Reports are written locally under `artifacts/` and are excluded from version control.

## GitHub Action

```yaml
steps:
  - uses: Dudiebug/patchrelay-scout@v1
    with:
      query: "(bounty OR reward) state:open"
      output: patchrelay-opportunities.json
```

The action writes a JSON report into the workflow workspace. It is intentionally read-only and does not claim, message, or submit work.

## MCP verification service

The repository also includes a dependency-free MCP server for agents that need to assess one public listing at a time before spending budget or starting work. It exposes `verify_public_bounty` over standard input/output and returns explicit reward evidence, safety flags, and payout-source warnings.

```bash
PYTHONPATH=src python3 -m money_maker.mcp
```

It is a self-hostable building block for a paid verification endpoint; the local server itself never signs payments, accesses wallets, or contacts listing authors.

## HTTP service

For a hosted deployment, the same verifier exposes `GET /health` and `POST /verify` with the MCP tool's JSON fields. The Docker image uses no runtime dependencies beyond Python.

The machine-readable contract is in [`openapi.yaml`](openapi.yaml), ready for API gateways and agent clients.

```bash
docker build -t patchrelay-verify .
docker run --rm -p 8080:8080 patchrelay-verify
curl http://127.0.0.1:8080/health
```

An x402-compatible payment gateway can sit in front of `POST /verify`; the service itself is deliberately payment-rail neutral.

## Revenue boundary

This project finds and ranks opportunities; it does not claim that a listing is revenue. An explicit reward amount is not payment proof, and upstream payout terms must be verified before claiming work.
