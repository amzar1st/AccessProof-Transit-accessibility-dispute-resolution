import copy
import hashlib
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sdk = types.ModuleType("genlayer")
sdk.TreeMap = dict
sdk.gl = types.SimpleNamespace(
    Contract=object,
    public=types.SimpleNamespace(view=lambda fn: fn, write=lambda fn: fn),
    eq_principle=types.SimpleNamespace(strict_eq=lambda fn: fn()),
    message=types.SimpleNamespace(sender_address="0xabc"),
    message_raw={"datetime": "2026-11-10T06:00:00+00:00"},
    nondet=types.SimpleNamespace(web=types.SimpleNamespace()),
)
sys.modules["genlayer"] = sdk
spec = importlib.util.spec_from_file_location("access_proof", ROOT / "contracts" / "access_proof.py")
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)

REPO = "amzar1st/AccessProof-Transit-accessibility-dispute-resolution"
PREFIX = access.ROOT + REPO + "/" + "a" * 40 + "/"
CLAIM = {"station": "harbor-square", "entrance": "any", "platform": "northbound",
         "from": "2026-10-20T08:15:00Z", "to": "2026-10-20T08:45:00Z"}


class AccessProofTest(unittest.TestCase):
    def setUp(self):
        self.fixtures = {}
        self.refs = []
        self.contract = access.AccessProof(REPO, True)
        self.contract.cases = {}
        sdk.gl.message_raw["datetime"] = "2026-11-10T06:00:00+00:00"
        sdk.gl.message.sender_address = "0xabc"
        sdk.gl.nondet.web.get = lambda url: types.SimpleNamespace(status=200, body=self.fixtures[url])
        for name in ("harbor-initial.json", "harbor-west-map.json"):
            self.refs.append(self.add(name, (ROOT / "evidence" / name).read_bytes()))

    def add(self, name, value):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        url = PREFIX + name
        self.fixtures[url] = body
        return {"url": url, "sha256": hashlib.sha256(body).hexdigest()}

    def verdict(self, claim=None, refs=None):
        return json.loads(access.evaluate(CLAIM if claim is None else claim, self.refs if refs is None else refs))

    def open(self, ref="case-1"):
        return self.contract.open_case(CLAIM["station"], CLAIM["entrance"], CLAIM["platform"],
                                       CLAIM["from"], CLAIM["to"], **self.refs[0], reference=ref)

    def test_alternate_route_changes_verdict(self):
        self.assertEqual(self.verdict(refs=self.refs[:1])["verdict"], "INCONCLUSIVE")
        result = self.verdict()
        self.assertEqual(result["verdict"], "ACCESSIBLE")
        self.assertEqual([(r["entrance"], r["state"]) for r in result["routes"]],
                         [("main", "BLOCKED"), ("west", "USABLE")])

    def test_named_entrance_cannot_be_substituted(self):
        self.assertEqual(self.verdict({**CLAIM, "entrance": "main"})["verdict"], "BLOCKED")

    def test_wrong_direction_cannot_be_substituted(self):
        self.assertEqual(self.verdict({**CLAIM, "platform": "southbound"})["verdict"], "BLOCKED")

    def test_unmapped_direction_is_unknown(self):
        self.assertEqual(self.verdict({**CLAIM, "platform": "eastbound"})["verdict"], "INCONCLUSIVE")

    def test_hash_mismatch_is_recorded(self):
        result = self.verdict(refs=[self.refs[0], {**self.refs[1], "sha256": "0" * 64}])
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["evidence"][1]["validity"], "HASH_MISMATCH")

    def test_missing_or_invalid_evidence_is_recorded(self):
        invalid = self.add("invalid.json", b'{"station":"x","station":"y"}')
        missing = {**invalid, "url": PREFIX + "missing.json"}
        result = self.verdict(refs=[invalid, missing])
        self.assertEqual([r["validity"] for r in result["evidence"]], ["INVALID_FOR_CLAIM", "FETCH_UNAVAILABLE"])

    def test_differing_complete_maps_are_inconclusive(self):
        doc = json.loads(self.fixtures[self.refs[1]["url"]])
        doc["maps"][0]["routes"].pop()
        result = self.verdict(refs=[*self.refs, self.add("other.json", doc)])
        self.assertEqual(result["reason"], "COMPLETE_MAPS_CONFLICT")

    def test_conflicting_status_is_unknown(self):
        doc = json.loads(self.fixtures[self.refs[1]["url"]])
        doc["status"].append({"asset": "west-lift", "state": "out"})
        result = self.verdict(refs=[self.refs[0], self.add("conflict.json", doc)])
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["routes"][1]["assets"]["west-lift"], "UNKNOWN")

    def test_partial_time_coverage_is_invalid(self):
        self.assertEqual(self.verdict({**CLAIM, "from":"2026-10-20T07:59:00Z"})["evidence"][0]["validity"], "INVALID_FOR_CLAIM")

    def test_allowlist_rejects_branch_query_traversal_and_foreign_origin(self):
        for url in (PREFIX + "../test.json", PREFIX + "test.json?raw=1",
                    PREFIX.replace("a" * 40, "main") + "test.json",
                    PREFIX.replace("raw.githubusercontent.com", "example.com") + "test.json"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                access.evidence_ref(self.contract.publisher, url, "a" * 64)

    def test_public_lifecycle_and_linked_hashes(self):
        case = self.open()
        first = self.contract.review(case)
        sdk.gl.message.sender_address = "0xdef"
        second = self.contract.challenge(case, **self.refs[1])
        self.assertEqual(self.contract.finalize(case), second)
        state = json.loads(self.contract.get_case(case))
        self.assertEqual(state["phase"], "FINALIZED")
        self.assertEqual(state["history"][1]["previous"], first)
        self.assertEqual(state["history"][1]["reviewer"], "0xdef")
        for decision in copy.deepcopy(state["history"]):
            digest = decision.pop("hash")
            self.assertEqual(access.fingerprint([case, state["policy"], state["claim"], decision]), digest)
        with self.assertRaises(ValueError):
            self.contract.finalize(case)

    def test_invalid_challenge_does_not_consume_round(self):
        case = self.open()
        self.contract.review(case)
        before = self.contract.get_case(case)
        with self.assertRaisesRegex(ValueError, "failed verification"):
            self.contract.challenge(case, url=self.refs[1]["url"], sha256="0" * 64)
        self.assertEqual(self.contract.get_case(case), before)
        self.contract.challenge(case, **self.refs[1])

    def test_unchanged_challenge_does_not_consume_round(self):
        case = self.open()
        self.contract.review(case)
        doc = json.loads(self.fixtures[self.refs[0]["url"]])
        doc["status"].append({"asset": "unrelated", "state": "up"})
        with self.assertRaisesRegex(ValueError, "change the route"):
            self.contract.challenge(case, **self.add("unrelated.json", doc))

    def test_deadline_and_no_challenge_finalize(self):
        case = self.open()
        self.contract.review(case)
        with self.assertRaisesRegex(ValueError, "cannot be finalized"):
            self.contract.finalize(case)
        sdk.gl.message_raw["datetime"] = "2026-11-10T06:15:00Z"
        with self.assertRaisesRegex(ValueError, "period closed"):
            self.contract.challenge(case, **self.refs[1])
        self.contract.finalize(case)

    def test_duplicate_reference_and_unknown_case(self):
        case = self.open()
        with self.assertRaisesRegex(ValueError, "already used"):
            self.open()
        sdk.gl.message.sender_address = "0xdef"
        self.assertNotEqual(self.open(), case)
        self.assertEqual(self.contract.get_case("0" * 64), "")
