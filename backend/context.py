from dataclasses import dataclass
from typing import Any

import prompts
from classes import State

VALID_MESSAGE_ROLES = {"system", "user", "assistant"}
DEFAULT_RECENT_TRANSCRIPT_TOKEN_BUDGET = 1200


def approximate_token_count(value: str) -> int:
    return max(1, (len(value) + 3) // 4)


@dataclass(frozen=True)
class ContextBuilder:
    recent_transcript_token_budget: int = DEFAULT_RECENT_TRANSCRIPT_TOKEN_BUDGET

    def narration_messages(self, state: State, user_message: str) -> list[dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": self._system_context(state),
            }
        ]
        messages.extend(self._recent_transcript_messages(state.chat_history))
        messages.append({"role": "user", "content": user_message})
        return messages

    def _system_context(self, state: State) -> str:
        sections = [
            self._base_system_rules(state),
            "=== Canonical world state ===\n"
            f"{prompts.world_state_context(state)}\n"
            "=== End canonical world state ===",
        ]
        rolling_summary = self._rolling_summary_context(state)
        if rolling_summary is not None:
            sections.append(rolling_summary)
        sections.append(
            "Return structured output with content for the player, state_delta operations for durable world-state "
            "changes, inventory_operations for any item the player picks up, is given, buys, consumes, drops, or "
            "loses, and quest_operations for quests the player starts, advances, or resolves. Only include "
            "state_delta, inventory_operations, or quest_operations entries for facts clearly and unambiguously "
            "established by the narrated turn in `content` — never invent an item, quest, or state change the "
            "narration does not describe, and never grant an item or advance a quest just because the player "
            "asked for or claimed it. A quest may be resolved whenever its premise stops being pursuable in any "
            "direction, not only on success — describe what actually happened in the outcome field neutrally, "
            "without judging it as a win or a loss. Set possible_moment to true only when this turn itself "
            "depicts a rare, narratively significant beat worth illustrating later (a decisive battle, a major "
            "milestone, a dramatic turning point) — leave it false on ordinary turns."
        )
        return "\n\n".join(section.strip() for section in sections if section.strip())

    @staticmethod
    def _base_system_rules(state: State) -> str:
        for message in state.chat_history:
            if message.get("role") == "system":
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
        return state.initialization_prompt

    @staticmethod
    def _rolling_summary_context(state: State) -> str | None:
        story_summary = getattr(state, "story_summary", "")
        unresolved_threads = getattr(state, "unresolved_threads", [])

        sections: list[str] = []
        if isinstance(story_summary, str) and story_summary.strip():
            sections.append(f"Story summary:\n{story_summary.strip()}")
        if isinstance(unresolved_threads, list) and unresolved_threads:
            threads = "\n".join(f"- {thread}" for thread in unresolved_threads if str(thread).strip())
            if threads:
                sections.append(f"Unresolved threads:\n{threads}")
        if not sections:
            return None
        return "=== Rolling narrative summary ===\n" + "\n\n".join(sections) + "\n=== End rolling narrative summary ==="

    def _recent_transcript_messages(self, chat_history: list[Any]) -> list[dict[str, str]]:
        selected_reversed: list[dict[str, str]] = []
        used_tokens = 0

        for raw_message in reversed(chat_history):
            message = self._validated_transcript_message(raw_message)
            if message is None:
                continue
            message_tokens = approximate_token_count(message["content"])
            if selected_reversed and used_tokens + message_tokens > self.recent_transcript_token_budget:
                break
            if not selected_reversed and message_tokens > self.recent_transcript_token_budget:
                continue
            selected_reversed.append(message)
            used_tokens += message_tokens

        return list(reversed(selected_reversed))

    @staticmethod
    def _validated_transcript_message(raw_message: Any) -> dict[str, str] | None:
        if not isinstance(raw_message, dict):
            return None
        role = raw_message.get("role")
        content = raw_message.get("content")
        if role == "system":
            return None
        if role not in VALID_MESSAGE_ROLES or not isinstance(content, str):
            return None
        return {"role": role, "content": content}
