# COE Core — Cognition-Oriented Emergence

**Historical prototype for shared observations and state claims.**

This repository preserves an early COE experiment associated with `draft-wang-coe-00`: simulated actors issue observations, record delegation and confirmation, and derive local state claims under a chosen counting policy.

## Status and relationship to JEP

The revised [COE draft](https://datatracker.ietf.org/doc/draft-wang-coe/) (`draft-wang-coe-01`, COE v0.5) defines an optional JEP profile for binding observation records, validation records, shared-state claims, and evidence references. It retains JEP's core event and verification rules. State synthesis and consensus methods are optional deployment extensions.

COE records support checking declared evidence and its bindings; they do not establish objective world truth, factual causality, authority, or governance consensus. The draft is an individual Internet-Draft and remains work in progress.

**This implementation retains its earlier local format.** Its `protocol: "COE"` envelope, `primitive` field, event-ID links, and standalone signatures have not been migrated to the revised profile or [JEP-Core v0.6](https://github.com/hjs-spec/jep-v06). Use the draft for the revised design and this repository to inspect the earlier experiment.

## What the prototype contains

- [`simulation.py`](simulation.py): a scripted warehouse-door scenario with simulated Robot A, Robot B, and Human C.
- [`app.py`](app.py): a Gradio event generator, a signature-checking panel, and a local state-synthesis demonstration.
- Local J/D/T/V mappings for observation, delegation, termination, and confirmation records.
- Event serialization using Python's `canonicaljson` package, SHA-256 hashes, and Ed25519 signatures made with generated demonstration keys.
- Local event and state-version records. Their timestamps are generated locally; no external timestamp anchoring service is integrated.

JEPA and Dreamer names in the interface are actor labels. The prototype does not run those models or integrate World Labs or Cosmos.

## Run locally

From a checkout of this repository, run the scripted simulation:

```bash
pip install canonicaljson cryptography
python simulation.py
```

This writes `simulation_log.txt` and `simulation_chain.json` in the working directory, replacing the existing example files there.

For the interactive interface:

```bash
pip install -r requirements.txt
python app.py
```

## How to interpret the checks

| Check or output | Scope in this implementation |
| --- | --- |
| Signature panel | Checks the submitted event against the supplied public key. It does not establish that the key belongs to the declared issuer. The event generator creates a fresh key for each generation. |
| Simulation `AuditChain.verify()` | Checks adjacent `prev_event_id` links only; it does not verify event hashes or signatures. |
| App `AuditChain.verify_chain()` | Checks adjacent event-ID links and hashes from the second event onward; it does not validate the first event's hash or any signatures. |
| Local state claim / SWS | Reports a result of the selected demonstration policy, not an independently verified physical state. |

The app's `simple_majority`, `weighted_trust`, and `bft` options are illustrative counting rules. The `bft` label does not establish distributed Byzantine fault tolerance. Confidence values and weights are demonstration inputs, not calibrated reliability estimates.

## Known scenario limitation

The intended scenario includes an `open` observation followed by a `closed` observation. However, the checked-in [JSON output](simulation_chain.json) contains **two `open` state claims**, while the [log](simulation_log.txt) labels the second output `CLOSED`.

The scripted evaluator returns the first qualifying observation and does not apply termination records to remove it. The example therefore does not demonstrate a correct open-to-closed state transition. The original simulation and outputs remain available for inspection; a successful chain-link check does not resolve this state-selection limitation.

## License

Apache-2.0

## Author

Cognitive Emergence Lab
