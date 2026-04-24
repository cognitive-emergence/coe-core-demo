import gradio as gr
import json
import uuid
import time
import hashlib
import base64
from datetime import datetime, timezone
from canonicaljson import encode_canonical_json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# =============================================================================
# COE Core — Cognition-Oriented Emergence (draft-wang-coe-00)
# =============================================================================

class COEEvent:
    """
    COE Event per Section 3.1
    protocol: "COE" (distinguishes from JEP)
    primitive: J/D/T/V with world-observation semantics
    """
    def __init__(self, primitive, issuer, target, prev_event_id=None,
                 assertion=None, delegate_to=None, delegation_scope=None,
                 terminate_of=None, terminate_reason=None,
                 verify_of=None, verification_result=None,
                 extensions=None):
        self.event_id = str(uuid.uuid4())
        self.protocol = "COE"
        self.primitive = primitive
        self.issuer = issuer
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.target = target
        self.prev_event_id = prev_event_id
        self.extensions = extensions or {}
        
        # Primitive-specific fields
        self.assertion = assertion
        self.delegate_to = delegate_to
        self.delegation_scope = delegation_scope
        self.terminate_of = terminate_of
        self.terminate_reason = terminate_reason
        self.verify_of = verify_of
        self.verification_result = verification_result
        
        # Signature fields
        self._hash = None
        self.signature = None
    
    def to_dict(self, include_sig=True):
        d = {
            "event_id": self.event_id,
            "protocol": self.protocol,
            "primitive": self.primitive,
            "issuer": self.issuer,
            "timestamp": self.timestamp,
            "target": self.target,
        }
        if self.prev_event_id:
            d["prev_event_id"] = self.prev_event_id
        else:
            d["prev_event_id"] = None
        
        if self.primitive == "J" and self.assertion:
            d["assertion"] = self.assertion
        if self.primitive == "D":
            if self.delegate_to:
                d["delegate_to"] = self.delegate_to
            if self.delegation_scope:
                d["delegation_scope"] = self.delegation_scope
        if self.primitive == "T":
            if self.terminate_of:
                d["terminate_of"] = self.terminate_of
            if self.terminate_reason:
                d["terminate_reason"] = self.terminate_reason
        if self.primitive == "V":
            if self.verify_of:
                d["verify_of"] = self.verify_of
            if self.verification_result:
                d["verification_result"] = self.verification_result
        
        if self.extensions:
            d["extensions"] = self.extensions
        
        if self._hash:
            d["hash"] = self._hash
        if include_sig and self.signature:
            d["signature"] = self.signature
        return d
    
    def canonicalize(self):
        payload = {k: v for k, v in self.to_dict(include_sig=False).items()}
        return encode_canonical_json(payload)
    
    def compute_hash(self):
        self._hash = f"sha256:{hashlib.sha256(self.canonicalize()).hexdigest()}"
        return self._hash


class COESigner:
    def __init__(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
    
    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
    
    def sign(self, payload_bytes):
        sig = self.private_key.sign(payload_bytes)
        return base64.urlsafe_b64encode(sig).rstrip(b'=').decode()


class ConsensusEngine:
    """
    Section 4: Consensus Emergence Engine
    Supports simple_majority, weighted_trust, bft
    """
    def __init__(self, policy="simple_majority", threshold=1.5, weights=None):
        self.policy = policy
        self.threshold = threshold
        self.weights = weights or {}
        self.sws_history = []
        self.events = []
    
    def add_event(self, event_dict):
        self.events.append(event_dict)
    
    def evaluate(self, target_assertion):
        """
        target_assertion: dict with subject, predicate, value
        Returns SWS or None
        """
        # Collect V events for this assertion
        relevant_v = []
        for e in self.events:
            if e.get("primitive") == "V" and e.get("verify_of"):
                # Check if this V confirms a J with matching assertion
                for parent_id in e.get("verify_of", []):
                    parent = self._find_event(parent_id)
                    if parent and self._assertion_matches(parent, target_assertion):
                        relevant_v.append(e)
                        break
        
        if not relevant_v:
            return None
        
        if self.policy == "simple_majority":
            confirmed = sum(1 for v in relevant_v if v.get("verification_result") == "confirmed")
            total = len(relevant_v)
            if total >= 3 and confirmed > total / 2:
                return self._make_sws(target_assertion, relevant_v)
        
        elif self.policy == "weighted_trust":
            confirmed_weight = 0.0
            for v in relevant_v:
                if v.get("verification_result") == "confirmed":
                    issuer = v.get("issuer", "")
                    w = self.weights.get(issuer, 0.5)
                    # Extract confidence from parent J event
                    parent = self._find_event(v.get("verify_of", [None])[0])
                    conf = parent.get("assertion", {}).get("confidence", 0.5) if parent else 0.5
                    confirmed_weight += w * conf
            if confirmed_weight > self.threshold:
                return self._make_sws(target_assertion, relevant_v)
        
        elif self.policy == "bft":
            confirmed = sum(1 for v in relevant_v if v.get("verification_result") == "confirmed")
            total = len(relevant_v)
            f = (total - 1) // 3  # tolerate f byzantine nodes
            if total >= 2 * f + 1 and confirmed > f + 1:
                return self._make_sws(target_assertion, relevant_v)
        
        return None
    
    def _find_event(self, event_id):
        for e in self.events:
            if e.get("event_id") == event_id:
                return e
        return None
    
    def _assertion_matches(self, event, target):
        a = event.get("assertion", {})
        return (a.get("subject") == target.get("subject") and
                a.get("predicate") == target.get("predicate"))
    
    def _make_sws(self, assertion, confirmations):
        sws = {
            "sws_id": str(uuid.uuid4()),
            "target": assertion.get("target", "unknown"),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "assertions": [{
                "subject": assertion.get("subject"),
                "predicate": assertion.get("predicate"),
                "value": assertion.get("value"),
                "confidence": assertion.get("confidence", 0.5),
                "based_on": [c.get("event_id") for c in confirmations],
                "consensus_policy": self.policy,
                "confirmations": len(confirmations)
            }],
            "previous_sws_id": self.sws_history[-1]["sws_id"] if self.sws_history else None,
            "hash": f"sha256:{hashlib.sha256(encode_canonical_json(assertion)).hexdigest()}"
        }
        self.sws_history.append(sws)
        return sws


class AuditChain:
    """Section 5: Versioned Audit Chain"""
    def __init__(self):
        self.events = []
        self.versions = []
    
    def append(self, event_dict):
        self.events.append(event_dict)
    
    def verify_chain(self):
        for i in range(1, len(self.events)):
            curr = self.events[i]
            prev = self.events[i-1]
            if curr.get("prev_event_id") != prev.get("event_id"):
                return False, f"Chain break at index {i}: prev_event_id mismatch"
            # Verify hash
            payload = {k: v for k, v in curr.items() if k not in ["hash", "signature"]}
            computed = f"sha256:{hashlib.sha256(encode_canonical_json(payload)).hexdigest()}"
            if curr.get("hash") != computed:
                return False, f"Hash mismatch at index {i}"
        return True, f"Chain valid: {len(self.events)} events linked"
    
    def anchor_version(self, sws):
        version = {
            "version_id": str(uuid.uuid4()),
            "sws": sws,
            "dependent_events": [e["event_id"] for e in self.events],
            "anchor_event_id": self.events[-1]["event_id"] if self.events else None,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "previous_version_id": self.versions[-1]["version_id"] if self.versions else None,
            "hash": f"sha256:{hashlib.sha256(encode_canonical_json(sws)).hexdigest()}"
        }
        self.versions.append(version)
        return version


# =============================================================================
# Gradio Interface
# =============================================================================

def generate_coe_event(primitive, issuer, target, prev_event_id,
                       j_subject, j_predicate, j_value, j_confidence,
                       d_delegate_to, d_scope,
                       t_terminate_of, t_reason,
                       v_verify_of, v_result,
                       ext_key, ext_value):
    
    assertion = None
    if primitive == "J":
        assertion = {
            "subject": j_subject,
            "predicate": j_predicate,
            "value": j_value,
            "confidence": j_confidence
        }
    
    event = COEEvent(
        primitive=primitive,
        issuer=issuer,
        target=target,
        prev_event_id=prev_event_id if prev_event_id.strip() else None,
        assertion=assertion,
        delegate_to=d_delegate_to if d_delegate_to.strip() else None,
        delegation_scope=d_scope if d_scope.strip() else None,
        terminate_of=t_terminate_of if t_terminate_of.strip() else None,
        terminate_reason=t_reason if t_reason.strip() else None,
        verify_of=[x.strip() for x in v_verify_of.split(",") if x.strip()] if v_verify_of.strip() else None,
        verification_result=v_result if v_result != "none" else None
    )
    
    signer = COESigner()
    event.compute_hash()
    payload = event.canonicalize()
    event.signature = signer.sign(payload)
    
    event_dict = event.to_dict()
    pretty_json = json.dumps(event_dict, indent=2, ensure_ascii=False)
    canonical_str = payload.decode('utf-8')
    pub_key = signer.get_public_key_pem()
    
    return pretty_json, canonical_str, event.signature, pub_key, event.event_id


def run_consensus_demo(policy, threshold, weight_a, weight_b, weight_c):
    """Appendix A: Three robots confirming door state"""
    engine = ConsensusEngine(
        policy=policy,
        threshold=float(threshold),
        weights={
            "did:example:robotA": float(weight_a),
            "did:example:robotB": float(weight_b),
            "did:example:humanC": float(weight_c)
        }
    )
    
    chain = AuditChain()
    results = []
    
    # Step 1: A observes door open
    e1 = COEEvent("J", "did:example:robotA", "warehouse-zone-3", None,
                  assertion={"subject": "door_01", "predicate": "status", "value": "open", "confidence": 0.95})
    s1 = COESigner()
    e1.compute_hash()
    e1.signature = s1.sign(e1.canonicalize())
    d1 = e1.to_dict()
    engine.add_event(d1)
    chain.append(d1)
    results.append(f"Step 1: A observes door open → J event\n{d1['event_id'][:8]}...")
    
    # Step 2: B delegates to A (optional D)
    e2 = COEEvent("D", "did:example:robotB", "warehouse-zone-3", e1.event_id,
                  delegate_to="did:example:robotA", delegation_scope="continuous_observation")
    s2 = COESigner()
    e2.compute_hash()
    e2.signature = s2.sign(e2.canonicalize())
    d2 = e2.to_dict()
    engine.add_event(d2)
    chain.append(d2)
    results.append(f"Step 2: B delegates to A → D event\n{d2['event_id'][:8]}...")
    
    # Step 3: B confirms A's observation
    e3 = COEEvent("V", "did:example:robotB", "warehouse-zone-3", e2.event_id,
                  verify_of=[e1.event_id], verification_result="confirmed")
    s3 = COESigner()
    e3.compute_hash()
    e3.signature = s3.sign(e3.canonicalize())
    d3 = e3.to_dict()
    engine.add_event(d3)
    chain.append(d3)
    results.append(f"Step 3: B confirms → V event\n{d3['event_id'][:8]}...")
    
    # Step 4: C confirms
    e4 = COEEvent("V", "did:example:humanC", "warehouse-zone-3", e3.event_id,
                  verify_of=[e1.event_id], verification_result="confirmed")
    s4 = COESigner()
    e4.compute_hash()
    e4.signature = s4.sign(e4.canonicalize())
    d4 = e4.to_dict()
    engine.add_event(d4)
    chain.append(d4)
    results.append(f"Step 4: C confirms → V event\n{d4['event_id'][:8]}...")
    
    # Consensus 1: door=open
    target = {"subject": "door_01", "predicate": "status", "value": "open", "confidence": 0.95, "target": "warehouse-zone-3"}
    sws1 = engine.evaluate(target)
    if sws1:
        v1 = chain.anchor_version(sws1)
        results.append(f"\n🌍 SWS#1: door = OPEN\nConsensus: {sws1['assertions'][0]['consensus_policy']}\nConfirmations: {sws1['assertions'][0]['confirmations']}")
    else:
        results.append("\n❌ Consensus failed for door=open")
    
    # Step 5: A observes door closed (T + J)
    e5 = COEEvent("T", "did:example:robotA", "warehouse-zone-3", e4.event_id,
                  terminate_of=e1.event_id, terminate_reason="state_changed")
    s5 = COESigner()
    e5.compute_hash()
    e5.signature = s5.sign(e5.canonicalize())
    d5 = e5.to_dict()
    engine.add_event(d5)
    chain.append(d5)
    results.append(f"\nStep 5: A terminates old state → T event\n{d5['event_id'][:8]}...")
    
    e6 = COEEvent("J", "did:example:robotA", "warehouse-zone-3", e5.event_id,
                  assertion={"subject": "door_01", "predicate": "status", "value": "closed", "confidence": 0.95})
    s6 = COESigner()
    e6.compute_hash()
    e6.signature = s6.sign(e6.canonicalize())
    d6 = e6.to_dict()
    engine.add_event(d6)
    chain.append(d6)
    results.append(f"Step 6: A observes door closed → J event\n{d6['event_id'][:8]}...")
    
    # Step 7-8: B and C confirm new state
    e7 = COEEvent("V", "did:example:robotB", "warehouse-zone-3", e6.event_id,
                  verify_of=[e6.event_id], verification_result="confirmed")
    s7 = COESigner()
    e7.compute_hash()
    e7.signature = s7.sign(e7.canonicalize())
    d7 = e7.to_dict()
    engine.add_event(d7)
    chain.append(d7)
    results.append(f"Step 7: B confirms new state → V event")
    
    e8 = COEEvent("V", "did:example:humanC", "warehouse-zone-3", e7.event_id,
                  verify_of=[e6.event_id], verification_result="confirmed")
    s8 = COESigner()
    e8.compute_hash()
    e8.signature = s8.sign(e8.canonicalize())
    d8 = e8.to_dict()
    engine.add_event(d8)
    chain.append(d8)
    results.append(f"Step 8: C confirms new state → V event")
    
    # Consensus 2: door=closed
    target2 = {"subject": "door_01", "predicate": "status", "value": "closed", "confidence": 0.95, "target": "warehouse-zone-3"}
    sws2 = engine.evaluate(target2)
    if sws2:
        v2 = chain.anchor_version(sws2)
        results.append(f"\n🌍 SWS#2: door = CLOSED\nConsensus: {sws2['assertions'][0]['consensus_policy']}\nConfirmations: {sws2['assertions'][0]['confirmations']}")
    else:
        results.append("\n❌ Consensus failed for door=closed")
    
    # Verify chain
    ok, msg = chain.verify_chain()
    results.append(f"\n🔗 Audit Chain: {msg}")
    results.append(f"📦 Versions anchored: {len(chain.versions)}")
    
    return "\n".join(results), json.dumps(chain.versions, indent=2, ensure_ascii=False)


def verify_coe_event(event_json, public_key_pem):
    if not event_json.strip() or not public_key_pem.strip():
        return "❌ 请输入事件 JSON 和公钥 PEM"
    
    try:
        event_dict = json.loads(event_json)
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析错误: {str(e)}"
    
    sig = event_dict.pop("signature", None)
    if not sig:
        return "❌ 缺少 signature 字段"
    
    try:
        pub_key = serialization.load_pem_public_key(public_key_pem.encode())
    except Exception as e:
        return f"❌ 公钥错误: {str(e)}"
    
    payload = {k: v for k, v in event_dict.items() if k != "signature"}
    payload_bytes = encode_canonical_json(payload)
    
    padding_needed = 4 - (len(sig) % 4)
    if padding_needed != 4:
        sig += '=' * padding_needed
    
    try:
        sig_bytes = base64.urlsafe_b64decode(sig)
        pub_key.verify(sig_bytes, payload_bytes)
        return "✅ COE Signature VALID — Event integrity confirmed"
    except InvalidSignature:
        return "❌ Invalid Ed25519 signature"
    except Exception as e:
        return f"❌ Verification error: {str(e)}"


with gr.Blocks(
    title="COE Core — Cognition-Oriented Emergence",
    css=".contain { max-width: 1400px; margin: auto; }"
) as demo:
    gr.Markdown("""
    # COE Core — Cognition-Oriented Emergence
    ### A Cognitive Interaction Protocol for Shared World Models (draft-wang-coe-00)
    
    COE 为碎片化的世界模型生态提供统一的**认知交互层**。
    
    > **J** (Judge) — 发起观察断言："我观察到 X"
    > **D** (Delegate) — 委托观察权："我授权你观察 X"
    > **T** (Terminate) — 终止状态："X 不再有效"
    > **V** (Verify) — 交叉验证："我确认你的观察"
    
    与 JEP 共享 J/D/T/V 基因，但语义不同：
    - **JEP** = 问责追溯 (post-hoc) → "谁负责？"
    - **COE** = 认知共识 (ex-ante) → "世界是什么？"
    """)
    
    with gr.Row():
        # =================== LEFT: Event Generator ===================
        with gr.Column(scale=1):
            gr.Markdown("### 🛠️ 生成 COE 事件")
            
            coe_primitive = gr.Dropdown(
                choices=["J", "D", "T", "V"],
                value="J",
                label="primitive (认知原语)",
                info="J=观察断言, D=委托, T=终止, V=验证"
            )
            coe_issuer = gr.Textbox(
                label="issuer (认知单元 CU)",
                value="did:example:robotA",
                info="DID 或 URI"
            )
            coe_target = gr.Textbox(
                label="target (世界模型/场景)",
                value="warehouse-zone-3",
                info="所有事件关联到同一物理空间"
            )
            coe_prev = gr.Textbox(
                label="prev_event_id (链引用)",
                value="",
                info="null = 创世事件; 否则引用前一个事件"
            )
            
            gr.Markdown("---")
            gr.Markdown("**J 事件字段** (primitive='J')")
            j_subject = gr.Textbox(label="assertion.subject", value="door_01")
            j_predicate = gr.Textbox(label="assertion.predicate", value="status")
            j_value = gr.Textbox(label="assertion.value", value="open")
            j_conf = gr.Number(label="assertion.confidence", value=0.95, minimum=0, maximum=1)
            
            gr.Markdown("---")
            gr.Markdown("**D 事件字段** (primitive='D')")
            d_delegate = gr.Textbox(label="delegate_to", value="did:example:robotB")
            d_scope = gr.Textbox(label="delegation_scope", value="continuous_observation")
            
            gr.Markdown("---")
            gr.Markdown("**T 事件字段** (primitive='T')")
            t_terminate = gr.Textbox(label="terminate_of", value="")
            t_reason = gr.Textbox(label="terminate_reason", value="state_changed")
            
            gr.Markdown("---")
            gr.Markdown("**V 事件字段** (primitive='V')")
            v_verify = gr.Textbox(label="verify_of (逗号分隔)", value="")
            v_result = gr.Dropdown(
                choices=["none", "confirmed", "rejected", "partial"],
                value="none",
                label="verification_result"
            )
            
            gen_btn = gr.Button("生成并签名", variant="primary")
        
        # =================== CENTER: Output ===================
        with gr.Column(scale=1):
            gr.Markdown("### 📤 COE 事件输出")
            coe_json = gr.Textbox(
                label="COE 事件 (JSON)",
                lines=16,
                info="protocol='COE' 区分于 JEP"
            )
            coe_canonical = gr.Textbox(
                label="JCS 规范化载荷 (RFC 8785)",
                lines=4
            )
            coe_sig = gr.Textbox(label="签名", lines=2)
            coe_pubkey = gr.Textbox(
                label="Ed25519 公钥 (PEM)",
                lines=4,
                info="保存用于验证"
            )
            coe_event_id = gr.Textbox(label="event_id (UUID)", lines=1)
            
            gr.Markdown("---")
            gr.Markdown("### 🔍 验证")
            verify_input = gr.Textbox(
                label="粘贴 COE 事件 JSON",
                lines=8,
                info="必须包含 signature 字段"
            )
            verify_key = gr.Textbox(
                label="公钥 PEM",
                lines=3
            )
            verify_btn = gr.Button("验证签名", variant="secondary")
            verify_result = gr.Textbox(label="验证结果", lines=2)
        
        # =================== RIGHT: Consensus Demo ===================
        with gr.Column(scale=1):
            gr.Markdown("### 🌍 共识引擎演示")
            gr.Markdown("*Appendix A: 三机器人确认门状态*")
            
            policy = gr.Dropdown(
                choices=["simple_majority", "weighted_trust", "bft"],
                value="weighted_trust",
                label="共识策略 (Section 4.2)"
            )
            threshold = gr.Number(
                label="Weighted Trust 阈值",
                value=1.5,
                info="Simple Majority 和 BFT 忽略此值"
            )
            
            gr.Markdown("**信任权重** (Weighted Trust / BFT 使用)")
            w_a = gr.Number(label="Robot A (JEPA)", value=0.9, minimum=0, maximum=1)
            w_b = gr.Number(label="Robot B (Dreamer)", value=0.8, minimum=0, maximum=1)
            w_c = gr.Number(label="Human C", value=1.0, minimum=0, maximum=1)
            
            demo_btn = gr.Button("运行验证场景", variant="primary")
            demo_result = gr.Textbox(
                label="场景执行结果",
                lines=20,
                info="8 步事件序列 + 2 次共识输出 + 审计链验证"
            )
            demo_versions = gr.Textbox(
                label="版本锚定记录",
                lines=10,
                info="SWS 版本历史 (Section 5.2)"
            )
    
    gen_btn.click(
        generate_coe_event,
        inputs=[coe_primitive, coe_issuer, coe_target, coe_prev,
                j_subject, j_predicate, j_value, j_conf,
                d_delegate, d_scope,
                t_terminate, t_reason,
                v_verify, v_result,
                gr.Textbox(value="", visible=False), gr.Textbox(value="", visible=False)],
        outputs=[coe_json, coe_canonical, coe_sig, coe_pubkey, coe_event_id]
    )
    
    verify_btn.click(
        verify_coe_event,
        inputs=[verify_input, verify_key],
        outputs=verify_result
    )
    
    demo_btn.click(
        run_consensus_demo,
        inputs=[policy, threshold, w_a, w_b, w_c],
        outputs=[demo_result, demo_versions]
    )
    
    gr.Markdown("""
    ---
    ### COE 在 JEP 生态中的位置
    
    ```
    因果可观测性 (数学基础)
           ↓
    JEP (问责语法: 谁负责?)
           ↓
    HJS (记录层: 机器不可变 + 人类隐私)
           ↓
    JAC (因果链: task_based_on)
           ↓
    COE (认知层: 世界是什么?)  ← 你在这里
    ```
    
    ### 窄腰架构 (Section 2.2)
    
    ```
    上层: 多智能体协作场景 (机器人协同、AR/VR、分布式科学共识)
           ↓ COE Events (J/D/T/V)
    窄腰: COE Core (2000-3000 行参考实现)
           ↓ COE Adapters
    下层: 异构世界模型 (JEPA, Dreamer, World Labs, Cosmos...)
    ```
    
    ### 共识策略对比 (Section 4.2)
    
    | 策略 | 适用场景 | 规则 |
    |------|---------|------|
    | Simple Majority | 少量 CU，信任平等 | 确认数 > 50% |
    | Weighted Trust | 能力异构，可靠性不同 | Σ(w_i × confidence_i) > threshold |
    | BFT | 高安全，存在恶意节点 | 2f+1 总事件，> f+1 确认 |
    
    ### 许可证
    Apache-2.0
    """)

if __name__ == "__main__":
    demo.launch()