# Studionet live verification

Open the [public AccessProof dashboard](https://accessproof.tinymule33.chatgpt.site/) and select **Load the Studionet demo**. The case is fetched directly from the finalized state of the [deployed contract](https://explorer-studio.genlayer.com/address/0x4444dff24e88b06F19bc864574384C74638dE4Ed).

| Step | Finalized receipt | Execution |
| --- | --- | --- |
| Deploy | [0x41e7…2459](https://explorer-studio.genlayer.com/tx/0x41e7d3016e6bcb620c81185ef565cd3f6f162d09c0d8a9059e79f8cc686e2459) | Success |
| Open case | [0xf9e9…1049](https://explorer-studio.genlayer.com/tx/0xf9e99e42ef49403fd67aa7687d8beb2c73cf87ec2ceed2d7d68d3cebfb451049) | Success |
| Initial review | [0xa5c2…9564](https://explorer-studio.genlayer.com/tx/0xa5c2ab430668bf9a47f7d8f3145f8cbcb663a333aa596669f5aa7c371b7a9564) | Success, `INCONCLUSIVE` |
| Challenge and re-review | [0x0576…3999](https://explorer-studio.genlayer.com/tx/0x05761e9e3afbf08ddd2d2e6ff5afc02736cc3cc1764b26d919a911ae2f0c3999) | Success, `ACCESSIBLE` |
| Application finalization | [0x5241…e1c](https://explorer-studio.genlayer.com/tx/0x524137d80ceb891108148ba15e77c25636fe89613967017d89a42602b9d7fe1c) | Success |
| Duplicate finalization | [0xc21d…db95](https://explorer-studio.genlayer.com/tx/0xc21d8792d1e67ebf83496c337a5408b52599d54e18934a34f7e2e05f2767db95) | Failed execution, state preserved |

- Network: Studionet (61999)
- Source SHA-256: `afe5efb61b19b2de63622b01cf4dcd6323523c6d82ddea315236b622e434cfc5`
- Case ID: `49c0c3d6b11559c2302fd3c110b67bb613d3b064c44651c5c4a2aba18a0c3ad4`
- Initial decision SHA-256: `8c091972a30575e551022ee7ce4c6ff2cf3aab41c9b0d072adfaf86844b9ef95`
- Challenge decision SHA-256: `e397248686466604d7cc4be5251664acac6e84575e5e8153e3d3ffc22d9adcb8`

## Reproduce

1. Run `npm ci`, `npm test`, `npm run build` and `node tests/verify-live.mjs`. The live script uses Studionet RPC to compare deployed code bytes with the checked-in contract, check the deployed schema, and assert the case and six receipts.
2. To send a new case, open the dashboard's **Submit a transaction** form and choose a new account-specific case reference. Copy the arguments to `open_case` in [Studio Run and Debug](https://studio.genlayer.com/?import-contract=0x4444dff24e88b06F19bc864574384C74638dE4Ed). Use **Normal (Full Consensus)** and the built-in Studio account.
3. Get the case ID from the successful open-case transaction return value. Call `review`, then `challenge` with the pinned west-map evidence within 15 minutes. Call `finalize` when the challenge is accepted. The demo inputs and receipt hashes are in [frontend configuration](../frontend/config.json).
4. In the dashboard, read the case ID and track each transaction. A finalized receipt reports consensus finality separately from execution. The dashboard signs nothing and forwards writes to Studio.
