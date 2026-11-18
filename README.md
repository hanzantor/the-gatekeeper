# The Gatekeeper

**An LLM-driven investigation game that doubles as a research platform for evaluating reasoning, persona consistency and evidence handling in language-model agents.**

MSc dissertation project, *Advanced Data Science & AI*, University of Liverpool (2026).

The player is trying to get through a restricted door in an office, hospital, research lab or government building. They collect clues from the room and argue their case. A locally hosted reasoning model plays the **Gatekeeper**, who weighs the evidence and the player's story turn by turn, then grants or denies access.

## Research focus

- **Persona conditioning**: the Gatekeeper runs as *fair*, *suspicious* or *corruptible*. Do models stay in character under pressure?
- **Evidence reasoning**: each scenario has a balanced set of supporting, identity, neutral and incriminating clues. Does the agent's decision follow the evidence?
- **Coherence metric**: the Gatekeeper's private reasoning is logged (never shown to the player) and compared against its spoken reply and final decision.
- **Matched runs**: scenarios can be frozen as fixtures and replayed across every persona and model combination (DeepSeek-R1 8B vs 14B), so only the variable under test changes.

## Architecture

| Layer | Stack | Role |
|---|---|---|
| Frontend | React 19 + Vite | Room scene, clue inventory, dialogue, persona selection |
| Backend | Python, Flask | Scenario generation, prompt building, response parsing, session logging |
| Model | Ollama (local), DeepSeek-R1 | Scenario writer and Gatekeeper agent |

```
backend/
  scenario_generator.py   LLM-generated scenarios, validated against a fixed clue library
  clue_library.py         Clue catalogue and quota-based picker
  personas.py             Gatekeeper persona definitions
  prompt_builder.py       Turn prompts with a sliding memory window
  response_parser.py      Extracts reasoning, reply and decision from model output
  session_logger.py       Per-session JSON logs for evaluation
logs/                     Evaluation runs (persona × model × scenario)
frontend/                 React client
```

## Running locally

Requires Python 3.11+, Node 20+ and [Ollama](https://ollama.com) with `deepseek-r1:8b` and/or `deepseek-r1:14b` pulled.

```bash
# backend
pip install -r requirements.txt
cd backend && python app.py

# frontend (new terminal)
cd frontend && npm install && npm run dev
```

Set `DEV_MODE` in `backend/config.py` to switch between the 8B (development) and 14B (evaluation) models.

## Author

**Hanin Al-Naamani**, Lecturer in Computer Science, Muscat College
