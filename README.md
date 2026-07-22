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

## Revenue boundary

This project finds and ranks opportunities; it does not claim that a listing is revenue. An explicit reward amount is not payment proof, and upstream payout terms must be verified before claiming work.
