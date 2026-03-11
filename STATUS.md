# Parsec Zero — Project Status

> Managed by: **Project Manager Agent**
> Last updated: 2026-03-10

---

## Current Phase: 1 — Project Scaffold

**Phase 1 goal:** Playable Level 1 — player movement, one room, collision, passing smoke test, exportable .exe.

### Phase 1 Checklist
- [x] Godot project directory structure created
- [x] `project.godot` initialized
- [x] `game_bible.json` authored
- [x] Python agent framework scaffolded
- [x] `.env.example` created
- [ ] GitHub repo initialized and remote set
- [ ] ChromaDB initialized with design documents
- [ ] `player.tscn` verified by QA
- [ ] `level_1.tscn` verified by QA
- [x] Headless smoke test passes
- [ ] `.exe` build exports and runs

---

## Agent Activity Log

| Timestamp | Agent | Task | Result |
|-----------|-------|------|--------|
| 2026-03-10 | Project Manager | Initial scaffold | Completed |

---

## Decisions Made (reference for all agents)

- **Framework**: CrewAI (sequential + hierarchical modes)
- **LLMs**: Anthropic only — Sonnet 4.6 for design/dev/PM, Haiku 4.5 for QA/assets/marketing
- **Image gen**: Stable Diffusion local via Automatic1111 (GPU)
- **Music**: Suno API
- **SFX**: ElevenLabs Sound Effects API
- **Memory**: ChromaDB (local)
- **Marketing automation**: n8n (self-hosted)
- **Art style**: pixel art, 32x32, sci-fi space station, dark palette, neon accents
- **Branch strategy**: feature branches → QA approval → PM merges to main

---

## Known Issues / Blockers

_None yet._

---

## Upcoming Milestones

| Phase | Milestone | Dependencies |
|-------|-----------|--------------|
| 1 | Smoke test passes | player.gd, level_1.tscn |
| 2 | All 5 agents operational | Phase 1 done |
| 3 | Autonomous build loop running | Phase 2 done |
| 4 | Asset pipeline live | Phase 3 done, SD local running |
| 5 | Marketing pipeline live | Phase 4 done, n8n running |
| 6 | Safety guardrails enforced | All phases |
