# Project Explorer submission

| Field | Value |
| --- | --- |
| Contribution type | Builder → Projects |
| Project name | AccessProof |
| Suggested primary tag | Oracles |
| Suggested secondary topics | Real-World Data, Dispute Resolution |
| One-liner | Verify whether a transit station had a usable step-free route to a specific platform at a specific time. |
| Frontend | https://accessproof.tinymule33.chatgpt.site/ |
| GitHub | https://github.com/amzar1st/AccessProof-Transit-accessibility-dispute-resolution |
| Contract | https://explorer-studio.genlayer.com/address/0x4444dff24e88b06F19bc864574384C74638dE4Ed |
| Studio | https://studio.genlayer.com/?import-contract=0x4444dff24e88b06F19bc864574384C74638dE4Ed |
| Evidence | https://github.com/amzar1st/AccessProof-Transit-accessibility-dispute-resolution/blob/main/docs/LIVE_VERIFICATION.md |

## Description

AccessProof verifies whether a station had a usable step-free route from a named or alternate entrance to the requested platform during a historical window. GenLayer validators independently fetch commit-pinned publisher archives, verify SHA-256, and evaluate station routes against outage and service coverage under a locked policy. The contract records ACCESSIBLE, BLOCKED, or INCONCLUSIVE and preserves linked decisions when new evidence changes a review. The live Studionet demo uses a fictional station. An outage blocks the main entrance, and a map challenge establishes a usable west entrance to the northbound platform. The public dashboard reads finalized cases, tracks transaction outcomes, prepares writes for Studio's built-in account, and provides a separate MTA live outage lookup.
