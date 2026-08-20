from classes import InventoryItem, State, WorldState
from context import ContextBuilder


def test_context_builder_instructs_possible_moment_usage():
    state = State(initialization_prompt="rules")

    messages = ContextBuilder().narration_messages(state, "continue")
    system_content = messages[0]["content"]

    assert "possible_moment" in system_content


def test_context_builder_keeps_canonical_state_when_recent_transcript_budget_is_tiny():
    state = State(
        initialization_prompt="You are the gamemaster.",
        chat_history=[
            {"role": "system", "content": "You are the gamemaster."},
            {"role": "user", "content": "old user action " * 80},
            {"role": "assistant", "content": "old assistant reply " * 80},
            {"role": "user", "content": "recent user action"},
            {"role": "assistant", "content": "recent assistant reply"},
        ],
        world_state=WorldState(
            current_location="glass market",
            inventory=[InventoryItem(name="brass key", weight_kg=0.2)],
        ),
    )

    messages = ContextBuilder(recent_transcript_token_budget=8).narration_messages(state, "What do I see?")

    assert messages[0]["role"] == "system"
    assert "=== Canonical world state ===" in messages[0]["content"]
    assert "Current location: glass market" in messages[0]["content"]
    assert "brass key" in messages[0]["content"]
    assert "old user action" not in str(messages)
    assert "old assistant reply" not in str(messages)
    assert messages[-1] == {"role": "user", "content": "What do I see?"}


def test_context_builder_omits_old_verbatim_turns_after_budget():
    state = State(
        initialization_prompt="rules",
        chat_history=[
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "first action " * 40},
            {"role": "assistant", "content": "first reply " * 40},
            {"role": "user", "content": "second action"},
            {"role": "assistant", "content": "second reply"},
        ],
    )

    messages = ContextBuilder(recent_transcript_token_budget=10).narration_messages(state, "third action")
    rendered = str(messages)

    assert "first action" not in rendered
    assert "first reply" not in rendered
    assert "second action" in rendered
    assert "second reply" in rendered


def test_context_builder_outputs_only_valid_message_roles():
    state = State(
        initialization_prompt="rules",
        chat_history=[
            {"role": "system", "content": "rules"},
            {"role": "tool", "content": "internal"},
            {"role": "assistant", "content": "visible reply"},
            {"role": "user", "content": 123},
        ],
    )

    messages = ContextBuilder().narration_messages(state, "continue")

    assert {message["role"] for message in messages} <= {"system", "user", "assistant"}
    assert "internal" not in str(messages)
    assert "visible reply" in str(messages)


def test_context_builder_includes_optional_rolling_summary_fields():
    state = State(initialization_prompt="rules")
    state.story_summary = "Iris crossed the flooded causeway."
    state.unresolved_threads = ["Find the lantern", "Open the sun gate"]

    messages = ContextBuilder().narration_messages(state, "continue")
    system_content = messages[0]["content"]

    assert "=== Rolling narrative summary ===" in system_content
    assert "Iris crossed the flooded causeway." in system_content
    assert "Find the lantern" in system_content
    assert "Open the sun gate" in system_content


def test_context_builder_does_not_truncate_stored_chat_history():
    chat_history = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "old action " * 80},
        {"role": "assistant", "content": "old reply " * 80},
        {"role": "user", "content": "recent action"},
        {"role": "assistant", "content": "recent reply"},
    ]
    state = State(initialization_prompt="rules", chat_history=list(chat_history))

    ContextBuilder(recent_transcript_token_budget=8).narration_messages(state, "continue")

    assert state.chat_history == chat_history
