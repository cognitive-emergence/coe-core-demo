import pytest
from app import COEEvent, COESigner, ConsensusEngine, AuditChain

def test_coe_event_protocol_field():
    """Section 3.1: protocol 字段必须为 COE"""
    event = COEEvent("J", "did:robotA", "warehouse-zone-3",
                     assertion={"subject": "door", "predicate": "status", "value": "open"})
    assert event.to_dict()["protocol"] == "COE"

def test_j_event_assertion():
    """Section 3.1: J 事件必须包含 assertion"""
    event = COEEvent("J", "did:robotA", "zone-3",
                     assertion={"subject": "door", "predicate": "status", "value": "open", "confidence": 0.95})
    d = event.to_dict()
    assert d["assertion"]["subject"] == "door"
    assert d["assertion"]["confidence"] == 0.95

def test_v_event_verification():
    """Section 3.1: V 事件包含 verify_of 和 verification_result"""
    event = COEEvent("V", "did:robotB", "zone-3",
                     verify_of=["uuid-123"], verification_result="confirmed")
    d = event.to_dict()
    assert d["verify_of"] == ["uuid-123"]
    assert d["verification_result"] == "confirmed"

def test_consensus_simple_majority():
    """Section 4.2.1: Simple Majority 策略"""
    engine = ConsensusEngine(policy="simple_majority")
    
    j = {"event_id": "j1", "primitive": "J", "assertion": {"subject": "door", "predicate": "status", "value": "open", "confidence": 0.9}}
    engine.add_event(j)
    
    for i in range(3):
        engine.add_event({
            "event_id": f"v{i}", "primitive": "V", "verify_of": ["j1"],
            "verification_result": "confirmed", "issuer": f"robot-{i}"
        })
    
    target = {"subject": "door", "predicate": "status", "value": "open", "confidence": 0.9, "target": "zone-3"}
    sws = engine.evaluate(target)
    assert sws is not None
    assert sws["assertions"][0]["value"] == "open"

def test_consensus_weighted_trust():
    """Section 4.2.2: Weighted Trust 策略"""
    engine = ConsensusEngine(
        policy="weighted_trust",
        threshold=1.5,
        weights={"did:robotA": 0.9, "did:robotB": 0.8, "did:humanC": 1.0}
    )
    
    j = {"event_id": "j1", "primitive": "J", "assertion": {"subject": "door", "predicate": "status", "value": "open", "confidence": 0.95}}
    engine.add_event(j)
    
    engine.add_event({"event_id": "v1", "primitive": "V", "verify_of": ["j1"], "verification_result": "confirmed", "issuer": "did:robotB"})
    engine.add_event({"event_id": "v2", "primitive": "V", "verify_of": ["j1"], "verification_result": "confirmed", "issuer": "did:humanC"})
    
    target = {"subject": "door", "predicate": "status", "value": "open", "confidence": 0.95, "target": "zone-3"}
    sws = engine.evaluate(target)
    assert sws is not None

def test_audit_chain_integrity():
    """Section 5.1: 审计链完整性验证"""
    chain = AuditChain()
    
    e1 = COEEvent("J", "did:a", "zone-1", assertion={"subject": "x", "predicate": "y", "value": "z"})
    s1 = COESigner()
    e1.compute_hash()
    e1.signature = s1.sign(e1.canonicalize())
    chain.append(e1.to_dict())
    
    e2 = COEEvent("V", "did:b", "zone-1", prev_event_id=e1.event_id, verify_of=[e1.event_id], verification_result="confirmed")
    s2 = COESigner()
    e2.compute_hash()
    e2.signature = s2.sign(e2.canonicalize())
    chain.append(e2.to_dict())
    
    ok, msg = chain.verify_chain()
    assert ok is True
    assert "valid" in msg.lower()

def test_audit_chain_break_detection():
    """Section 5.1: 篡改链应被检测"""
    chain = AuditChain()
    
    e1 = COEEvent("J", "did:a", "zone-1", assertion={"subject": "x", "predicate": "y", "value": "z"})
    s1 = COESigner()
    e1.compute_hash()
    e1.signature = s1.sign(e1.canonicalize())
    chain.append(e1.to_dict())
    
    e2 = COEEvent("V", "did:b", "zone-1", prev_event_id="wrong-id", verify_of=[e1.event_id], verification_result="confirmed")
    s2 = COESigner()
    e2.compute_hash()
    e2.signature = s2.sign(e2.canonicalize())
    chain.append(e2.to_dict())
    
    ok, msg = chain.verify_chain()
    assert ok is False
    assert "break" in msg.lower() or "mismatch" in msg.lower()