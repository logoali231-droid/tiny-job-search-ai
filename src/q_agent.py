import json
import os
import random
from collections import defaultdict
import hashlib


class JobSearchQLearner:
    """
    Tabular Q-learning agent. Now the state includes the full skill set
    and the user's current university period, so strategies are
    personalized per (role, specialty, expertise, skills, period).
    """

    GENERIC_TEMPLATES = [
        "{specialty} {expertise} {skills}",
        "{specialty} {skills} {expertise} remote",
        "{skills} {specialty}",
        "{specialty} {expertise}",
        "{skills} estagio",
        "{specialty} estagio {skills}",
    ]

    ROLE_TEMPLATES = {
        "software_engineering": [
            "{specialty} {expertise} developer {skills}",
            "{specialty} engineer {expertise} {skills}",
            "backend {specialty} {skills}",
            "python {specialty} {skills}",
            "{skills} {specialty} remoto",
            "estagio {specialty} {skills}",
        ],
        "data_science": [
            "{specialty} data scientist {skills}",
            "machine learning {specialty} {skills}",
            "{specialty} analyst {skills}",
            "data {specialty} {skills}",
            "AI {specialty} {skills}",
            "estagio dados {skills}",
        ],
        "design": [
            "{specialty} designer {skills}",
            "UX {specialty} {skills}",
            "product {specialty} designer {skills}",
            "UI {specialty} {skills}",
            "{specialty} estagio {skills}",
            "figma {specialty} {skills}",
        ],
        "marketing": [
            "{specialty} marketing {skills}",
            "digital {specialty} {skills}",
            "growth {specialty} {skills}",
            "SEO {specialty} {skills}",
            "{specialty} estagio {skills}",
            "social media {specialty} {skills}",
        ],
    }


    def __init__(self, alpha=0.1, epsilon=0.25):
        self.alpha = alpha
        self.epsilon = epsilon
        self.q_table = defaultdict(float)
        self.action_counts = defaultdict(int)
        self.total_updates = 0
        self.last_state = None
        self.last_action = None

    def _state_hash(self, role, specialty, expertise, skills, min_period):
        skills_key = sorted(
            {
                str(skill).strip().casefold()
                for skill in skills
                if skill and str(skill).strip()
            }
        )

        state = [
            str(role or "").strip().casefold(),
            str(specialty or "").strip().casefold(),
            str(expertise or "").strip().casefold(),
            skills_key,
            int(min_period),
        ]

        serialized = json.dumps(
            state,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        digest = hashlib.sha256(serialized).digest()
        return int.from_bytes(digest[:8], byteorder="big")

    def _templates_for(self, role):
        return self.ROLE_TEMPLATES.get(role, self.GENERIC_TEMPLATES)

    def act(self, role, specialty, expertise, skills, min_period, training=True):
        state = self._state_hash(role, specialty, expertise, skills, min_period)
        templates = self._templates_for(role)
        actions = list(enumerate(templates))

        if training and random.random() < self.epsilon:
            action_idx, template = random.choice(actions)
        else:
            scored = [(self.q_table[(state, i)], i, t) for i, t in actions]
            best_q = max(s[0] for s in scored)
            tied = [(i, t) for q, i, t in scored if q == best_q]
            action_idx, template = min(
                tied, key=lambda x: self.action_counts[(state, x[0])]
            )

        self.last_state = state
        self.last_action = action_idx
        self.action_counts[(state, action_idx)] += 1

        skills_str = " ".join(skills[:3])
        query = template.format(
            specialty=specialty or "general",
            expertise=expertise or "mid",
            skills=skills_str,
            role=role.replace("_", " "),
            period=min_period,
        )
        return query, action_idx


    def update(self, reward):
        if self.last_state is None or self.last_action is None:
            return

        key = (self.last_state, self.last_action)
        old_value = self.q_table[key]

        self.q_table[key] = (
            old_value + self.alpha * (reward - old_value)
        )

        self.total_updates += 1

    def save(self, path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            payload = {
                "schema_version": 2,
                "q_table": {f"{k[0]}|{k[1]}": v for k, v in self.q_table.items()},
                "action_counts": {
                    f"{k[0]}|{k[1]}": v for k, v in self.action_counts.items()
                },
                "total_updates": self.total_updates,
            }
            with open(path, "w") as f:
                json.dump(payload, f)
        except Exception as e:
            print(f"[QAgent] save failed: {e}")

    def load(self, path):
        if not os.path.exists(path):
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            # A tabela antiga usa identificadores que podem mudar
            # entre execuções do Python. Não podemos reaproveitá-la.
            if payload.get("schema_version") != 2:
                self.q_table = defaultdict(float)
                self.action_counts = defaultdict(int)
                self.total_updates = 0

                print(
                    "[Tiny] Tabela antiga descartada. "
                    "O aprendizado novo será salvo corretamente."
                )
                return

            self.q_table = defaultdict(float)

            for k, v in payload.get("q_table", {}).items():
                state, action = k.split("|", 1)
                self.q_table[(int(state), int(action))] = float(v)

            self.action_counts = defaultdict(int)

            for k, v in payload.get("action_counts", {}).items():
                state, action = k.split("|", 1)
                self.action_counts[(int(state), int(action))] = int(v)

            self.total_updates = int(payload.get("total_updates", 0))

        except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"[Tiny] Não foi possível carregar o aprendizado: {e}")

    def stats(self):
        return {
            "updates": self.total_updates,
            "strategies": len(self.q_table),
            "epsilon": round(self.epsilon, 3),
        }
