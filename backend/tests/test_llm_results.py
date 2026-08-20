import pytest
from pydantic import ValidationError

from llm_results import (
    ActionAssessment,
    BooleanDecision,
    DamageDecision,
    InventoryOperation,
    MomentPackage,
    NarrationResult,
    QuestOperation,
    StartingStateResult,
    StateDelta,
    StateDeltaOperation,
    StorySummaryResult,
)


def test_boolean_decision_requires_boolean_value():
    assert BooleanDecision(value=True).value is True

    with pytest.raises(ValidationError):
        BooleanDecision(value="maybe")


@pytest.mark.parametrize("damage", [0, 1, 2, 3, 4, 5])
def test_damage_decision_accepts_valid_damage_range(damage):
    assert DamageDecision(damage=damage).damage == damage


@pytest.mark.parametrize("damage", [-1, 6])
def test_damage_decision_rejects_invalid_damage_range(damage):
    with pytest.raises(ValidationError):
        DamageDecision(damage=damage)


@pytest.mark.parametrize("damage", [0, 1, 2, 3, 4, 5])
def test_action_assessment_accepts_valid_damage_range(damage):
    assessment = ActionAssessment(relevant=True, realistic=True, damage=damage)

    assert assessment.damage == damage


@pytest.mark.parametrize("damage", [-1, 6])
def test_action_assessment_rejects_invalid_damage_range(damage):
    with pytest.raises(ValidationError):
        ActionAssessment(relevant=True, realistic=True, damage=damage)


@pytest.mark.parametrize(
    "operation",
    [
        "set_location",
        "add_condition",
        "remove_condition",
        "upsert_npc",
        "set_relationship",
        "set_world_flag",
    ],
)
def test_state_delta_accepts_allow_listed_operations(operation):
    delta = StateDelta(operations=[StateDeltaOperation(operation=operation, key="brass key")])

    assert delta.operations[0].operation == operation


def test_state_delta_rejects_unknown_operations():
    with pytest.raises(ValidationError):
        StateDeltaOperation(operation="delete_save", key="brass key")


def test_state_delta_rejects_legacy_inventory_operations():
    with pytest.raises(ValidationError):
        StateDeltaOperation(operation="add_inventory", key="brass key")


def test_state_delta_rejects_legacy_quest_operations():
    with pytest.raises(ValidationError):
        StateDeltaOperation(operation="activate_quest", key="find the lantern")


def test_story_summary_result_defaults_unresolved_threads():
    result = StorySummaryResult(story_summary="Iris crossed the causeway.")

    assert result.story_summary == "Iris crossed the causeway."
    assert result.unresolved_threads == []


@pytest.mark.parametrize("weight_kg", [-1, -0.1])
def test_inventory_operation_rejects_negative_weight(weight_kg):
    with pytest.raises(ValidationError):
        InventoryOperation(operation="add_item", name="rock", weight_kg=weight_kg)


def test_inventory_operation_defaults_quantity_to_one():
    operation = InventoryOperation(operation="add_item", name="torch")

    assert operation.quantity == 1


def test_narration_result_defaults_inventory_operations_to_empty_list():
    result = NarrationResult(content="Nothing happens.")

    assert result.inventory_operations == []
    assert result.quest_operations == []
    assert result.possible_moment is False


def test_narration_result_accepts_possible_moment_flag():
    result = NarrationResult(content="A decisive battle is won.", possible_moment=True)

    assert result.possible_moment is True


def test_moment_package_defaults_caption_and_image_prompt_empty():
    package = MomentPackage(is_moment=False)

    assert package.caption == ""
    assert package.image_prompt == ""


def test_moment_package_accepts_caption_and_image_prompt():
    package = MomentPackage(
        is_moment=True,
        caption="Iris drives back the tide-wraith.",
        image_prompt="a glassmaker standing triumphant over a defeated sea creature",
    )

    assert package.is_moment is True
    assert package.caption == "Iris drives back the tide-wraith."
    assert package.image_prompt == "a glassmaker standing triumphant over a defeated sea creature"


@pytest.mark.parametrize("operation", ["start_quest", "advance_quest", "resolve_quest"])
def test_quest_operation_accepts_allow_listed_operations(operation):
    op = QuestOperation(operation=operation, title="find the lantern")

    assert op.operation == operation


def test_quest_operation_rejects_unknown_operations():
    with pytest.raises(ValidationError):
        QuestOperation(operation="fail_quest", title="find the lantern")


def _valid_starting_state_kwargs(**overrides):
    kwargs = dict(
        starting_location="a quiet harbor",
        age_years=30,
        height_cm=170.0,
        body_weight_kg=65.0,
        max_carry_weight_kg=25.0,
    )
    kwargs.update(overrides)
    return kwargs


@pytest.mark.parametrize("age_years", [-1, 151])
def test_starting_state_result_rejects_invalid_age(age_years):
    with pytest.raises(ValidationError):
        StartingStateResult(**_valid_starting_state_kwargs(age_years=age_years))


@pytest.mark.parametrize("field", ["height_cm", "body_weight_kg", "max_carry_weight_kg"])
def test_starting_state_result_rejects_non_positive_physical_fields(field):
    with pytest.raises(ValidationError):
        StartingStateResult(**_valid_starting_state_kwargs(**{field: 0}))


def test_starting_state_result_defaults_empty_inventory_and_conditions():
    result = StartingStateResult(**_valid_starting_state_kwargs())

    assert result.starting_inventory == []
    assert result.starting_conditions == []
