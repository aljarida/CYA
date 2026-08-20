from observability import InMemoryTraceRecorder, StageTrace, TurnTrace, safe_metadata


def test_safe_metadata_redacts_prompt_and_message_fields():
    metadata = safe_metadata(
        {
            "user_message": "I reveal a secret.",
            "prompt": "system instructions",
            "status": "ok",
        }
    )

    assert metadata == {
        "user_message": "[redacted]",
        "prompt": "[redacted]",
        "status": "ok",
    }


def test_safe_metadata_redacts_secret_like_fields_case_insensitively():
    metadata = safe_metadata(
        {
            "api_key": "sk-test",
            "Authorization": "Bearer test-token",
            "password": "correct-horse-battery-staple",
            "status": "ok",
        }
    )

    assert metadata == {
        "api_key": "[redacted]",
        "Authorization": "[redacted]",
        "password": "[redacted]",
        "status": "ok",
    }


def test_in_memory_trace_recorder_stores_traces():
    recorder = InMemoryTraceRecorder()

    recorder.record(
        trace=StageTrace(
            correlation_id="turn-1",
            game_id="game-1",
            turn_id=2,
            stage="narration",
            duration_ms=1.5,
            status="success",
        )
    )

    assert len(recorder.traces) == 1
    assert recorder.traces[0].stage == "narration"


def test_in_memory_trace_recorder_stores_total_turn_trace():
    recorder = InMemoryTraceRecorder()

    recorder.record_turn(
        TurnTrace(
            correlation_id="turn-1",
            game_id="game-1",
            turn_id=2,
            duration_ms=4.5,
            status="success",
        )
    )

    assert recorder.turn_traces[0].correlation_id == "turn-1"
    assert recorder.turn_traces[0].duration_ms == 4.5
