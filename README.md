title: COE Core Demo
emoji: 🌍
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
---

# COE Core — Cognition-Oriented Emergence

**A Cognitive Interaction Protocol for Shared World Models**

COE provides a unified **cognitive interaction layer** for the fragmented world model ecosystem (JEPA, Dreamer, World Labs, Cosmos, etc.). Through the J/D/T/V four primitives, heterogeneous agents achieve **verifiable consensus** on world states within a traceable, auditable framework.

## Relationship with JEP

| Protocol | Question Answered | Temporal Aspect | Semantics |
|----------|-------------------|-----------------|-----------|
| **JEP** | "Who is responsible?" | Post-hoc | Accountability grammar |
| **COE** | "What is the world?" | Ex-ante / in-situ | Cognitive consensus |

> Both share the J/D/T/V primitive gene, forming a complete **"cognition-accountability" dual-loop architecture**.

## Core Components

- **Four-Primitive Cognitive Algebra**: J (Observation Assertion) / D (Delegated Observation) / T (Terminate State) / V (Cross-Validation)
- **Consensus Engine**: Simple Majority / Weighted Trust / Byzantine Fault Tolerance
- **Versioned Audit Chain**: Git-like version control + timestamp anchoring
- **Narrow-Waist Architecture**: ~2000-3000 lines reference implementation; lower-layer world models can evolve independently

## Verification Scenario (Appendix A)

Three robots (A/B/C) collaboratively confirm warehouse door state:
1. A observes door open → J event
2. B delegates continuous observation to A → D event
3. B confirms A's observation → V event
4. C human confirms → V event
5. Consensus engine outputs SWS: door=open
6. A observes door closed → T + J event
7. B/C confirm new state
8. Consensus engine updates SWS: door=closed

## Multi-Agent Simulation

`simulation.py` — Reproduces Appendix A scenario (3 robots confirming door state).

Run:
```bash
pip install canonicaljson cryptography
python simulation.py
```

Outputs:
- `simulation_log.txt` — Human-readable execution trace
- `simulation_chain.json` — Complete audit chain with signatures

Results:
- 8 events generated (J/D/T/V)
- 2 consensus outputs (door=open → door=closed)
- Chain integrity: PASS
- Weighted trust: 1.71 > threshold 1.5


## License

Apache-2.0

## Author

Cognitive Emergence Lab
```
