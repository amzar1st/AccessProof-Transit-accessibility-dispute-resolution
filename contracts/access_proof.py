# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import hashlib
import json
import re
from datetime import datetime
from genlayer import *

POLICY = "accessproof-route-v1"
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
HEX = re.compile(r"[0-9a-f]{64}")
REPO = re.compile(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+")
PATH = re.compile(r"[0-9a-f]{40}/[A-Za-z0-9_./-]+\.json")
UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
ROOT = "https://raw.githubusercontent.com/"
CHALLENGE_SECONDS = 900
MAX_BYTES = 16000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def slug(value):
    return isinstance(value, str) and SLUG.fullmatch(value) is not None


def unix(value):
    require(isinstance(value, str) and UTC.fullmatch(value), "Expected UTC YYYY-MM-DDTHH:MM:SSZ")
    return int(datetime.fromisoformat(value[:-1] + "+00:00").timestamp())


def now():
    return int(datetime.fromisoformat(gl.message_raw["datetime"].replace("Z", "+00:00")).timestamp())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def evidence_ref(prefix, url, sha256):
    require(len(url) <= 320 and url.startswith(prefix), "Evidence must use the locked publisher repository")
    suffix = url[len(prefix):]
    require(PATH.fullmatch(suffix) and all(part not in ("", ".", "..") for part in suffix.split("/")), "Use a commit-pinned JSON URL")
    require(HEX.fullmatch(sha256), "Expected lowercase SHA-256")
    return {"url": url, "sha256": sha256}


def normalize(document, claim):
    require(isinstance(document, dict) and set(document) == {"station", "from", "to", "maps", "status"}, "Unexpected evidence schema")
    require(document["station"] == claim["station"], "Station mismatch")
    start, end = unix(document["from"]), unix(document["to"])
    require(start <= unix(claim["from"]) < unix(claim["to"]) <= end, "Archive does not cover entire window")
    require(isinstance(document["maps"], list) and len(document["maps"]) <= 16, "Invalid maps")
    require(isinstance(document["status"], list) and len(document["status"]) <= 96, "Invalid status")
    routes = set()
    complete = set()
    for entry in document["maps"]:
        require(isinstance(entry, dict) and set(entry) == {"platform", "complete", "routes"}, "Invalid map")
        require(slug(entry["platform"]) and type(entry["complete"]) is bool, "Invalid map scope")
        require(isinstance(entry["routes"], list) and len(entry["routes"]) <= 16, "Invalid route count")
        mapped = set()
        for route in entry["routes"]:
            require(isinstance(route, dict) and set(route) == {"entrance", "assets"}, "Invalid route")
            assets = route["assets"]
            require(slug(route["entrance"]) and isinstance(assets, list) and 1 <= len(assets) <= 12, "Invalid route details")
            require(all(slug(asset) for asset in assets) and len(set(assets)) == len(assets), "Invalid route assets")
            if entry["platform"] == claim["platform"] and claim["entrance"] in ("any", route["entrance"]):
                mapped.add((route["entrance"], tuple(sorted(assets))))
        routes.update(mapped)
        if entry["platform"] == claim["platform"] and entry["complete"]:
            complete.add(tuple(sorted(mapped)))
    statuses = set()
    for entry in document["status"]:
        require(isinstance(entry, dict) and set(entry) == {"asset", "state"}, "Invalid asset status")
        require(slug(entry["asset"]) and entry["state"] in ("up", "out"), "Invalid asset state")
        statuses.add((entry["asset"], entry["state"]))
    return routes, complete, statuses


def fetch(ref, claim):
    try:
        response = gl.nondet.web.get(ref["url"])
        if response.status != 200:
            return "HTTP_ERROR", None
        body = response.body
        if not 0 < len(body) <= MAX_BYTES:
            return "SIZE_INVALID", None
        if hashlib.sha256(body).hexdigest() != ref["sha256"]:
            return "HASH_MISMATCH", None
        try:
            return "VERIFIED", normalize(json.loads(body, object_pairs_hook=unique_object), claim)
        except (ValueError, TypeError, KeyError, RecursionError):
            return "INVALID_FOR_CLAIM", None
    except Exception:
        return "FETCH_UNAVAILABLE", None


def evaluate(claim, refs):
    partial, complete, statuses = set(), set(), set()
    evidence = []
    for ref in refs:
        validity, result = fetch(ref, claim)
        evidence.append({**ref, "validity": validity})
        if result is not None:
            routes, coverage, state = result
            partial.update(routes)
            complete.update(coverage)
            statuses.update(state)
    route_results = []
    # A complete map supersedes partial sketches. Conflicting complete maps require review.
    candidates = next(iter(complete)) if len(complete) == 1 else sorted(partial)
    for entrance, assets in candidates:
        states = {}
        for asset in assets:
            up, out = (asset, "up") in statuses, (asset, "out") in statuses
            states[asset] = "UP" if up and not out else "OUT" if out and not up else "UNKNOWN"
        state = "BLOCKED" if "OUT" in states.values() else "USABLE" if all(s == "UP" for s in states.values()) else "UNKNOWN"
        route_results.append({"entrance": entrance, "assets": states, "state": state})

    if len(complete) > 1:
        verdict, reason = "INCONCLUSIVE", "COMPLETE_MAPS_CONFLICT"
    elif any(route["state"] == "USABLE" for route in route_results):
        verdict, reason = "ACCESSIBLE", "VERIFIED_STEP_FREE_ROUTE"
    elif len(complete) == 1 and all(route["state"] == "BLOCKED" for route in route_results):
        verdict, reason = "BLOCKED", "COMPLETE_MAP_HAS_NO_USABLE_ROUTE"
    else:
        verdict, reason = "INCONCLUSIVE", "ROUTE_OR_STATUS_COVERAGE_INCOMPLETE"
    return canonical({"verdict": verdict, "reason": reason, "routes": route_results, "evidence": evidence})


class AccessProof(gl.Contract):
    publisher: str
    synthetic: bool
    cases: TreeMap[str, str]

    def __init__(self, publisher_repository: str, synthetic: bool):
        require(len(publisher_repository) <= 140 and REPO.fullmatch(publisher_repository), "Expected publisher owner/repository")
        require(publisher_repository.split("/")[1] not in (".", ".."), "Invalid publisher repository")
        self.publisher = ROOT + publisher_repository + "/"
        self.synthetic = synthetic

    @gl.public.view
    def get_policy(self) -> str:
        return canonical({"policy": POLICY, "publisher": self.publisher, "synthetic": self.synthetic, "challenge_seconds": CHALLENGE_SECONDS})

    @gl.public.view
    def get_case(self, case_id: str) -> str:
        require(HEX.fullmatch(case_id), "Expected case ID")
        return self.cases.get(case_id, "")

    @gl.public.write
    def open_case(self, station: str, entrance: str, platform: str, start: str, end: str, url: str, sha256: str, reference: str) -> str:
        require(all(slug(x) for x in (station, entrance, platform, reference)), "Expected lowercase IDs")
        start_time, end_time = unix(start), unix(end)
        require(0 < end_time - start_time <= 86400 and end_time <= now(), "Use a past window of at most 24 hours")
        evidence = evidence_ref(self.publisher, url, sha256)
        sender = str(gl.message.sender_address).lower()
        case_id = fingerprint([POLICY, sender, reference])
        require(not self.cases.get(case_id), "Case reference already used by this account")
        claim = {"station": station, "entrance": entrance, "platform": platform, "from": start, "to": end}
        self.cases[case_id] = canonical({
            "id": case_id, "policy": POLICY, "synthetic": self.synthetic, "claimant": sender,
            "reference": reference, "claim": claim, "evidence": [evidence], "phase": "OPEN", "history": [],
        })
        return case_id

    def _case(self, case_id):
        raw = self.get_case(case_id)
        require(raw, "Case not found")
        return json.loads(raw)

    def _review(self, case, reviewer, round_name):
        claim, refs = case["claim"], case["evidence"]
        result = json.loads(gl.eq_principle.strict_eq(lambda: evaluate(claim, refs)))
        result.update({"round": round_name, "reviewer": reviewer, "previous": case["history"][-1]["hash"] if case["history"] else ""})
        result["hash"] = fingerprint([case["id"], case["policy"], claim, result])
        case["history"].append(result)

    @gl.public.write
    def review(self, case_id: str) -> str:
        case = self._case(case_id)
        require(case["phase"] == "OPEN", "Case already reviewed")
        self._review(case, str(gl.message.sender_address).lower(), "INITIAL")
        case["phase"] = "REVIEWED"
        case["challenge_until"] = now() + CHALLENGE_SECONDS
        self.cases[case_id] = canonical(case)
        return case["history"][-1]["hash"]

    @gl.public.write
    def challenge(self, case_id: str, url: str, sha256: str) -> str:
        case = self._case(case_id)
        require(case["phase"] == "REVIEWED" and now() < case["challenge_until"], "Challenge period closed")
        evidence = evidence_ref(self.publisher, url, sha256)
        require(all(evidence["url"] != ref["url"] and evidence["sha256"] != ref["sha256"] for ref in case["evidence"]), "Use new evidence")
        case["evidence"].append(evidence)
        self._review(case, str(gl.message.sender_address).lower(), "CHALLENGE")
        before, after = case["history"]
        require(after["evidence"][-1]["validity"] == "VERIFIED", "Challenge evidence failed verification")
        require(before["evidence"][0]["validity"] != "VERIFIED" or after["evidence"][0]["validity"] == "VERIFIED", "Original evidence temporarily unavailable")
        require(any(before[key] != after[key] for key in ("verdict", "reason", "routes")), "Challenge must change the route assessment")
        case["phase"] = "REVIEWED_AFTER_CHALLENGE"
        self.cases[case_id] = canonical(case)
        return case["history"][-1]["hash"]

    @gl.public.write
    def finalize(self, case_id: str) -> str:
        case = self._case(case_id)
        require(case["phase"] == "REVIEWED_AFTER_CHALLENGE" or (case["phase"] == "REVIEWED" and now() >= case["challenge_until"]), "Case cannot be finalized yet")
        case["phase"] = "FINALIZED"
        self.cases[case_id] = canonical(case)
        return case["history"][-1]["hash"]
