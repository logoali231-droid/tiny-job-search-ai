# Tiny Job Search AI

A tiny Q-learning agent that learns which search keywords find *you* the best job offers.
Runs 100% locally. No ChatGPT, no Gemini, no API keys.

## Install (Linux Mint / Ubuntu / Debian)

    ./install.sh

Then launch **"Tiny Job Search AI"** from your applications menu,
or run:

    ./run.sh

## How it works

1. Pick your role family + specialty + expertise level.
2. The agent picks a keyword strategy (ε-greedy over a Q-table).
3. We query Remotive + Jobicy (both keyless public APIs).
4. You rate the results with 👍 / 👎 / Skip.
5. The Q-table updates with a Bellman update and is saved to `data/q_table.json`.

Over time it converges on the keyword combinations that work best *for you*.

## Uninstall

    ./uninstall.sh