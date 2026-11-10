# Evidence policy

A deployment locks one publisher GitHub repository and a synthetic label in its constructor. Sources must be commit-pinned HTTPS URLs under that repository and provide exact-byte SHA-256 commitments. The trust boundary is the publisher's authority to attest maps and asset states. Hashing proves which bytes were used. Publisher accuracy, capture completeness, and physical usability still depend on how the publisher gathered the evidence.

## Archive format

The JSON object has exactly five keys:

| Field | Meaning |
| --- | --- |
| `station` | Stable lowercase station identifier |
| `from`, `to` | UTC coverage bounds. They must contain the entire claim interval. |
| `maps` | Array of platform-specific maps, each with `platform`, `complete`, and `routes` |
| `status` | Array of asset-state attestations using `asset` and `state` (`up` or `out`) |

A route is a publisher-attested continuous step-free path from its `entrance` to the stated platform, with all required dependencies in `assets`. An asset may represent an elevator, entrance closure, or service availability. `up` or `out` must describe the full archive coverage interval. A publisher should omit mixed or unsupported asset states. A complete map attests that it lists every route for that platform. An explicitly complete empty map establishes that the requested scope had no step-free route.

Complete maps supersede partial sketches. Differing complete maps yield `INCONCLUSIVE`. Conflicting asset attestations are treated as unknown. An affirmative verdict requires a route whose every dependency is confirmed usable. A blocked verdict requires a complete applicable map whose routes all have confirmed closures, or a complete map showing no applicable route. Other cases are inconclusive. Estimated reopen times and silence in the MTA feed are insufficient to establish that an asset was operational.

## Controls and limits

- One initial snapshot, one material challenge, a maximum 24-hour historical claim, and 16 KB per fetched snapshot. Attachments have bounded map, route, asset, and status counts.
- Exact host and repository allowlist, full commit ID, simple paths, mandatory SHA-256, duplicate-key rejection, strict schema, and plain text rendering. The adjudicator uses structured data and contains no LLM prompt.
- A challenge with invalid evidence or no change to the route assessment leaves the case untouched. A transient failure to retrieve the previously verified initial evidence also leaves the case untouched.
- Reviews and application finalization are permissionless. Each account's case reference is unique. Do not place a rider's name or other personal information in evidence or a case reference.
- Simultaneous partial outages are conservatively inconclusive unless the published data establishes a result under the full-window policy. Historical accessibility reflects the specified platform and equipment scope. It cannot certify boarding gaps, crowding, or individual mobility requirements.
- The public deployment pins the project's synthetic archive. An operator pilot would need a separate deployment bound to the operator's own publication repository and a verified historical capture process combining maps, equipment uptime and service alerts. A live outage list alone cannot provide that history.
