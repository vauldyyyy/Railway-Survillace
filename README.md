# RailGuard AI — Railway Surveillance SOC

**A real-time Security Operations Centre for railway platforms: five threat classes detected across live camera feeds, with cross-camera person re-identification under differential privacy.**

Built for the AI Systems & Software Hackathon (BITS Pilani × IIT Madras).

---

## The problem

Indian railway platforms are monitored by CCTV that nobody watches in real time. Footage is reviewed *after* an incident. The failure modes that matter — someone on the track, an abandoned bag, smoke in a waiting area — are exactly the ones where a thirty-second response beats a thirty-minute forensic review.

The constraint is not detection accuracy. It is that a control room operator can watch four screens, not forty, and that a system which cries wolf gets muted within a week.

## What it detects

| Class | Why it matters |
|---|---|
| Track intrusion | Immediate life safety |
| Abandoned baggage | Security escalation |
| Fire / smoke | Evacuation trigger |
| Track obstruction | Braking distance |
| Crowd density | Crush-risk precursor |

## Measured performance

Trained on merged railway-domain imagery. Numbers below are the final epoch of `railfod_merged5`, reproducible from `runs/detect/railfod_merged5/results.csv`, which is committed:

| Metric | Value |
|---|---|
| mAP@50 | **0.744** |
| Precision | **0.789** |
| Recall | 0.723 |
| mAP@50-95 | 0.616 |
| Epochs | 27 |

Peak mAP@50 across training reached 0.782; the final-epoch figure is reported instead because it corresponds to the shipped checkpoint. Earlier runs (`railfod_merged` through `merged4`) are retained for comparison and reached 0.589–0.724.

## Architecture

```
backend/
├── main.py               FastAPI app, WebSocket fan-out to the dashboard
├── ai/                   Inference, privacy, tamper detection
├── detection/
│   └── entity_state.py   Cross-frame entity tracking and state machine
├── security/
│   └── prompt_sanitizer.py   Input hardening for the LLM scene-description path
├── app/api/              REST surface
└── app/core/             Config, encryption

src/                      React 19 + TypeScript SOC dashboard
├── pages/                Overview · LiveFeeds · ThreatAlerts · PersonTracking · AIAgents
├── components/ThomasAI   Natural-language scene interrogation
└── store/                Zustand system state
```

### Design decisions worth defending

**Hybrid GPU inference with failover.** A remote Colab T4 bridge handles inference when available and falls back to local CPU when it does not. Hackathon-grade pragmatism, but the failover path is the interesting part: a surveillance system that stops detecting when a GPU disappears is worse than one that degrades to slower detection.

**Entity state machine, not per-frame detection.** `detection/entity_state.py` tracks objects across frames rather than raising an alert per detection. "A bag has been stationary and unattended for N seconds" is an incident; "a bag is visible" is not. This is what keeps the alert volume low enough that operators keep the system on.

**Differential privacy on re-identification.** Cross-camera person tracking uses OSNet embeddings with calibrated noise (ε=0.1). Re-identifying individuals across a public transport network is a surveillance capability with real misuse potential; the noise budget is a deliberate constraint on how precisely any single person can be followed.

**Prompt sanitisation.** The LLM scene-description path takes model output and camera metadata as input. `security/prompt_sanitizer.py` exists because that is an injection surface, not a text field.

**AES-256-GCM at rest.** Incident records include imagery of identifiable people; encrypted SQLite is the minimum defensible storage posture.

## Stack

| Layer | Technology |
|---|---|
| Detection | YOLOv8s (custom-trained), YOLO-World (open-vocabulary) |
| Re-identification | OSNet + differential privacy |
| Backend | Python, FastAPI, WebSockets |
| Vision | OpenCV, PyTorch |
| Frontend | React 19, TypeScript, Zustand |
| Storage | SQLite with AES-256-GCM |
| Scene description | Gemini |

## Running it

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env                             # add your keys
uvicorn main:app --reload

# Frontend
npm install
npm run dev
```

**Model weights are not in the repository.** Pretrained YOLO checkpoints download automatically via Ultralytics on first run. The custom-trained `best.pt` is a 22 MB artifact distributed as a release asset rather than committed — see *Known issues*.

## Known issues

An honest list of what a reviewer would find:

- [ ] **Repository history is ~888 MB.** Model weights (9 files, ~217 MB, including freely downloadable pretrained checkpoints) and `__pycache__` were committed before `.gitignore` covered them — and `.gitignore` does not untrack files already in the index. They are untracked as of this commit, but the blobs remain in history. Reclaiming that space requires `git filter-repo`, which rewrites history and needs coordination with anyone who has cloned.
- [ ] `accuracy_results.txt` is empty and should either be populated from `results.csv` or removed.
- [ ] Five training runs are retained; four are superseded and could be pruned to `merged5` plus one baseline.
- [ ] No automated tests. The entity state machine is the highest-value target — its timing thresholds are exactly the kind of logic that regresses silently.
- [ ] The Colab GPU bridge is a hackathon expedient. Production would use a persistent inference service.
- [ ] Detection performance is reported on a held-out split of the training distribution. Robustness under fog and low light was assessed qualitatively, not on a labelled adverse-conditions test set.

## License

Not currently licensed.
