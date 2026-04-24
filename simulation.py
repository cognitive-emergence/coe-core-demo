#!/usr/bin/env python3
"""
Multi-Agent Simulation for JEP/COE Protocol Validation
Scenario: Three agents (A/B/C) collaboratively confirm door state (Appendix A)
"""

import json
import uuid
import time
import hashlib
import base64
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from canonicaljson import encode_canonical_json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def sha256_multihash(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

class Agent:
    def __init__(self, agent_id: str, name: str, trust_weight: float = 1.0):
        self.agent_id = agent_id
        self.name = name
        self.trust_weight = trust_weight
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        self.event_log: List[Dict] = []

    def sign(self, payload_bytes: bytes) -> str:
        sig = self.private_key.sign(payload_bytes)
        return base64.urlsafe_b64encode(sig).rstrip(b'=').decode()

    def create_coe_event(self, primitive: str, target: str, prev_event_id: Optional[str] = None,
                         assertion: Optional[Dict] = None, verify_of: Optional[List[str]] = None,
                         verification_result: Optional[str] = None,
                         terminate_of: Optional[str] = None, terminate_reason: Optional[str] = None):
        event = {
            "event_id": str(uuid.uuid4()),
            "protocol": "COE",
            "primitive": primitive,
            "issuer": self.agent_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target": target,
            "prev_event_id": prev_event_id,
        }

        if primitive == "J" and assertion:
            event["assertion"] = assertion
        if primitive == "D" and assertion:
            event["delegate_to"] = assertion.get("delegate_to")
            event["delegation_scope"] = assertion.get("delegation_scope")
        if primitive == "T" and terminate_of:
            event["terminate_of"] = terminate_of
            event["terminate_reason"] = terminate_reason
        if primitive == "V" and verify_of:
            event["verify_of"] = verify_of
            event["verification_result"] = verification_result

        payload = {k: v for k, v in event.items()}
        payload_bytes = encode_canonical_json(payload)
        event["hash"] = sha256_multihash(payload_bytes.decode())
        event["signature"] = self.sign(payload_bytes)

        self.event_log.append(event)
        return event


class ConsensusEngine:
    def __init__(self, threshold: float, weights: Dict[str, float]):
        self.threshold = threshold
        self.weights = weights
        self.sws_history: List[Dict] = []
        self.events: List[Dict] = []

    def add_event(self, event: Dict):
        self.events.append(event)

    def evaluate(self, subject: str, predicate: str) -> Optional[Dict]:
        j_events = [e for e in self.events 
                    if e.get("primitive") == "J" 
                    and e.get("assertion", {}).get("subject") == subject
                    and e.get("assertion", {}).get("predicate") == predicate]

        if not j_events:
            return None

        for j in j_events:
            v_events = [e for e in self.events
                       if e.get("primitive") == "V"
                       and j["event_id"] in e.get("verify_of", [])]

            confirmed_weight = 0.0
            confirmations = []
            for v in v_events:
                if v.get("verification_result") == "confirmed":
                    issuer = v.get("issuer", "")
                    w = self.weights.get(issuer, 0.5)
                    conf = j.get("assertion", {}).get("confidence", 0.5)
                    confirmed_weight += w * conf
                    confirmations.append(v["event_id"])

            if confirmed_weight > self.threshold:
                sws = {
                    "sws_id": str(uuid.uuid4()),
                    "target": j["target"],
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "assertions": [{
                        "subject": subject,
                        "predicate": predicate,
                        "value": j["assertion"]["value"],
                        "confidence": j["assertion"].get("confidence", 0.5),
                        "based_on": [j["event_id"]] + confirmations,
                        "consensus_policy": "weighted_trust",
                        "confirmations": len(confirmations),
                        "confirmed_weight": round(confirmed_weight, 3)
                    }],
                    "previous_sws_id": self.sws_history[-1]["sws_id"] if self.sws_history else None,
                }
                self.sws_history.append(sws)
                return sws
        return None


class AuditChain:
    def __init__(self):
        self.events: List[Dict] = []

    def append(self, event: Dict):
        self.events.append(event)

    def verify(self) -> tuple:
        for i in range(1, len(self.events)):
            curr = self.events[i]
            prev = self.events[i-1]
            if curr.get("prev_event_id") != prev.get("event_id"):
                return False, f"Chain break at index {i}: prev_event_id mismatch"
        return True, f"Chain valid: {len(self.events)} events"

    def export(self) -> Dict:
        return {
            "chain_length": len(self.events),
            "events": self.events,
            "verification": self.verify()[1]
        }


def run_simulation():
    print("=" * 70)
    print("JEP/COE Multi-Agent Simulation")
    print("Scenario: Warehouse Door State Confirmation (Appendix A)")
    print("=" * 70)

    robot_a = Agent("did:example:robotA", "Robot A (JEPA)", trust_weight=0.9)
    robot_b = Agent("did:example:robotB", "Robot B (Dreamer)", trust_weight=0.8)
    human_c = Agent("did:example:humanC", "Human Supervisor", trust_weight=1.0)

    agents = [robot_a, robot_b, human_c]
    chain = AuditChain()
    engine = ConsensusEngine(
        threshold=1.5,
        weights={a.agent_id: a.trust_weight for a in agents}
    )

    log_lines = []

    def log(msg: str):
        print(msg)
        log_lines.append(msg)

    # Step 1
    log("\n[Step 1] Robot A observes door is open")
    e1 = robot_a.create_coe_event(
        "J", "warehouse-zone-3",
        assertion={"subject": "door_01", "predicate": "status", "value": "open", "confidence": 0.95}
    )
    engine.add_event(e1)
    chain.append(e1)
    log(f"  Event ID: {e1['event_id'][:8]}... | Primitive: J | Value: open")

    # Step 2
    log("\n[Step 2] Robot B delegates to Robot A")
    e2 = robot_b.create_coe_event(
        "D", "warehouse-zone-3", prev_event_id=e1["event_id"],
        assertion={"delegate_to": robot_a.agent_id, "delegation_scope": "continuous_observation"}
    )
    chain.append(e2)
    log(f"  Event ID: {e2['event_id'][:8]}... | Primitive: D")

    # Step 3
    log("\n[Step 3] Robot B confirms A's observation")
    e3 = robot_b.create_coe_event(
        "V", "warehouse-zone-3", prev_event_id=e2["event_id"],
        verify_of=[e1["event_id"]], verification_result="confirmed"
    )
    engine.add_event(e3)
    chain.append(e3)
    log(f"  Event ID: {e3['event_id'][:8]}... | Primitive: V | Result: confirmed")

    # Step 4
    log("\n[Step 4] Human C confirms")
    e4 = human_c.create_coe_event(
        "V", "warehouse-zone-3", prev_event_id=e3["event_id"],
        verify_of=[e1["event_id"]], verification_result="confirmed"
    )
    engine.add_event(e4)
    chain.append(e4)
    log(f"  Event ID: {e4['event_id'][:8]}... | Primitive: V | Result: confirmed")

    # Consensus 1
    log("\n[Consensus 1] Evaluating door=open...")
    sws1 = engine.evaluate("door_01", "status")
    if sws1:
        log(f"  🌍 SWS#1 OUTPUT: door = OPEN")
        log(f"  Policy: weighted_trust | Threshold: 1.5")
        log(f"  Confirmed weight: {sws1['assertions'][0]['confirmed_weight']}")
        log(f"  Confirmations: {sws1['assertions'][0]['confirmations']}")

    # Step 5-6
    log("\n[Step 5] Robot A terminates old state")
    e5 = robot_a.create_coe_event(
        "T", "warehouse-zone-3", prev_event_id=e4["event_id"],
        terminate_of=e1["event_id"], terminate_reason="state_changed"
    )
    chain.append(e5)
    log(f"  Event ID: {e5['event_id'][:8]}... | Primitive: T")

    log("\n[Step 6] Robot A observes door closed")
    e6 = robot_a.create_coe_event(
        "J", "warehouse-zone-3", prev_event_id=e5["event_id"],
        assertion={"subject": "door_01", "predicate": "status", "value": "closed", "confidence": 0.95}
    )
    engine.add_event(e6)
    chain.append(e6)
    log(f"  Event ID: {e6['event_id'][:8]}... | Primitive: J | Value: closed")

    # Step 7-8
    log("\n[Step 7] Robot B confirms new state")
    e7 = robot_b.create_coe_event(
        "V", "warehouse-zone-3", prev_event_id=e6["event_id"],
        verify_of=[e6["event_id"]], verification_result="confirmed"
    )
    engine.add_event(e7)
    chain.append(e7)

    log("\n[Step 8] Human C confirms new state")
    e8 = human_c.create_coe_event(
        "V", "warehouse-zone-3", prev_event_id=e7["event_id"],
        verify_of=[e6["event_id"]], verification_result="confirmed"
    )
    engine.add_event(e8)
    chain.append(e8)

    # Consensus 2
    log("\n[Consensus 2] Evaluating door=closed...")
    sws2 = engine.evaluate("door_01", "status")
    if sws2:
        log(f"  🌍 SWS#2 OUTPUT: door = CLOSED")
        log(f"  Confirmed weight: {sws2['assertions'][0]['confirmed_weight']}")
        log(f"  Confirmations: {sws2['assertions'][0]['confirmations']}")

    # Verification
    log("\n" + "=" * 70)
    log("AUDIT CHAIN VERIFICATION")
    log("=" * 70)
    ok, msg = chain.verify()
    log(f"  Chain integrity: {'PASS' if ok else 'FAIL'} — {msg}")

    # Export
    log("\n" + "=" * 70)
    log("EXPORT")
    log("=" * 70)

    output = {
        "simulation": {
            "scenario": "Warehouse Door State Confirmation",
            "agents": [{"id": a.agent_id, "name": a.name, "weight": a.trust_weight} for a in agents],
            "total_events": len(chain.events),
            "consensus_outputs": len(engine.sws_history),
            "chain_valid": ok
        },
        "audit_chain": chain.export(),
        "consensus_states": engine.sws_history,
        "agent_event_logs": {a.agent_id: a.event_log for a in agents}
    }

    with open("simulation_chain.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open("simulation_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    log("  📄 simulation_log.txt — Human-readable execution log")
    log("  📄 simulation_chain.json — Complete machine-readable audit chain")
    log("\nSimulation complete.")

    return output


if __name__ == "__main__":
    run_simulation()
