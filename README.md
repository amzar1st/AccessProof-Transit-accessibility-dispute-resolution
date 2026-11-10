# AccessProof

AccessProof records whether the published evidence establishes a usable step-free route to a transit platform during a specified historical window. An outage at a named entrance can block that route while a different entrance still serves the requested direction.

- [Public dashboard](https://accessproof.tinymule33.chatgpt.site/)
- [Studionet contract](https://explorer-studio.genlayer.com/address/0x4444dff24e88b06F19bc864574384C74638dE4Ed)
- [Live verification and receipts](docs/LIVE_VERIFICATION.md)
- [Project Explorer fields](docs/PROJECT_EXPLORER.md)
- [Evidence policy and security](docs/EVIDENCE_POLICY.md)

## Workflow

1. Open a case with station, entrance scope, platform or direction, UTC time window, and an evidence commitment. The entrance scope can be a specific entrance or `any`.
2. Run the initial review. GenLayer validators independently retrieve the exact publisher snapshot, verify SHA-256, and compare the normalized route and asset verdicts via strict equivalence.
3. Submit one material challenge during the 15-minute window. The validators recheck both evidence files and preserve both decisions in a linked hash chain.
4. Finalize after a successful challenge or after the challenge window expires. Read finalized case state from the dashboard. Submit writes from Studio using its built-in account.

Harbor Square is a fictional station. Its first archive records the main elevator outage but has an incomplete map. The challenge supplies a complete map identifying a usable west route to the northbound platform. The dashboard separately retrieves the MTA's real-time elevator feed as operator context. The contract's synthetic deployment does not use this feed to adjudicate historical cases.

## Local development

Use Node.js 22+ and Python 3.11+.

```sh
npm ci
npm test
npm run build
python -m http.server 8080 --directory dist
node tests/verify-live.mjs
```

The live check compares deployed source bytes, validates the deployed schema and checks finalized state and receipts. The Python suite uses an SDK stub for branch and failure coverage. The Studio demo exercises the real consensus path on chain 61999.
