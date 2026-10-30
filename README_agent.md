# Resumable research agent for Ambient

A small agent that turns a topic into a short risk report in four steps
(research, rank, summarize, check). Built from lessons learned during testnet testing.

## What it does
- Each step is saved to a state file, so a crash or restart resumes where it stopped
  and does not repeat finished steps.
- Every call logs its request id, status, latency and finish reason.
- Reads the API key from the AMBIENT_API_KEY environment variable. Never hardcode it.

## Run
    read -rs -p "Ambient key: " AMBIENT_API_KEY; export AMBIENT_API_KEY
    python3 agent_recovery.py
    CRASH_AFTER=3 python3 agent_recovery.py   # simulate an interruption, then run again

## Known limits
- Interruption is simulated with an exit, not a hard kill.
- A crash between a response arriving and the state being saved repeats that one step.
- Output is not schema-validated at every step yet.
- Token budget is fixed at 2048; reasoning models can return empty content if it is too small.
- Tested with one model alias, short chains, single user.

## Needed before others could rely on it
- Per-call idempotency key to detect repeated calls.
- Schema validation and retry-on-invalid at each step.
- Budget that adapts when content comes back empty.
- Configurable model and prompts instead of hardcoded ones.
