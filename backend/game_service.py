import os
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

import prompts
from classes import MIN_HIT_POINTS, InventoryItem, Quest, Sender, State, StoryMoment
from context import ContextBuilder
from database import GameRepository, RevisionConflictError
from images import Image
from llm import LLMClient, LLMError
from llm_results import (
    ActionAssessment,
    InventoryOperation,
    MomentPackage,
    NarrationResult,
    QuestOperation,
    StartingStateResult,
    StateDelta,
    StateDeltaOperation,
    StorySummaryResult,
)
from observability import NoOpTraceRecorder, StageTrace, TraceRecorder, TurnTrace, safe_metadata
from utils import bool_of_str

DEFAULT_SUMMARY_REFRESH_TURN_THRESHOLD = 8
RECENT_TURNS_TO_KEEP_UNSUMMARIZED = 4
QUEST_GROUNDING_STOPWORDS = {
    "a", "an", "the", "of", "to", "and", "or", "for", "with", "in", "on", "at",
    "from", "by", "his", "her", "their", "its", "your", "you", "is", "are",
}
MODEL_TRACE_STAGES = {"action_assessment", "narration", "game_over_summary", "rolling_summary"}
MOMENT_DAMAGE_THRESHOLD = 4
MOMENT_IMAGE_SIZE = "1536x1024"


@dataclass(frozen=True)
class TurnResult:
    sender: Sender
    content: str
    status_code: int = 200
    hit_points: int | None = None
    game_over_summary: str | None = None
    world_state: dict[str, Any] | None = None
    player_attributes: dict[str, Any] | None = None
    story_summary: str | None = None
    unresolved_threads: list[str] | None = None
    moment: dict[str, Any] | None = None

    def to_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "sender": str(self.sender),
            "content": self.content,
        }
        if self.game_over_summary is not None:
            response["gameOverSummary"] = self.game_over_summary
        if self.hit_points is not None:
            response["hitPoints"] = self.hit_points
        if self.player_attributes is not None:
            response["playerAttributes"] = self.player_attributes
        if self.world_state is not None:
            response["worldState"] = self.world_state
        if self.story_summary is not None:
            response["storySummary"] = self.story_summary
        if self.unresolved_threads is not None:
            response["unresolvedThreads"] = self.unresolved_threads
        if self.moment is not None:
            response["moment"] = self.moment
        return response


class GameService:
    def __init__(
        self,
        repository: GameRepository,
        llm_client: LLMClient,
        context_builder: ContextBuilder | None = None,
        summary_refresh_turn_threshold: int = DEFAULT_SUMMARY_REFRESH_TURN_THRESHOLD,
        recent_turns_to_keep_unsummarized: int = RECENT_TURNS_TO_KEEP_UNSUMMARIZED,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        self.repository = repository
        self.llm_client = llm_client
        self.context_builder = context_builder or ContextBuilder()
        self.summary_refresh_turn_threshold = summary_refresh_turn_threshold
        self.recent_turns_to_keep_unsummarized = recent_turns_to_keep_unsummarized
        self.trace_recorder = trace_recorder or NoOpTraceRecorder()

    async def play_turn(self, game_id: str | None, content: str) -> TurnResult:
        correlation_id = uuid4().hex
        started_at = perf_counter()
        trace_context: dict[str, int | None] = {"turn_id": None}
        status = "error"
        try:
            result = await self._play_turn(game_id, content, correlation_id, trace_context)
            status = "success" if result.status_code == 200 else "error"
            return result
        finally:
            self.trace_recorder.record_turn(
                TurnTrace(
                    correlation_id=correlation_id,
                    game_id=game_id or "",
                    turn_id=trace_context["turn_id"],
                    duration_ms=max(0, (perf_counter() - started_at) * 1000),
                    status=status,
                )
            )

    async def _play_turn(
        self,
        game_id: str | None,
        content: str,
        correlation_id: str,
        trace_context: dict[str, int | None],
    ) -> TurnResult:
        if not self._is_valid_id(game_id):
            return self._error(
                400,
                "Game ID is required. Please initialize or load a game first.",
            )

        state = self.repository.get_game(game_id)
        if state is None:
            return self._error(
                400,
                "Invalid game ID. Please initialize or load a game first.",
            )
        turn_id = self._completed_turn_count(state)
        trace_context["turn_id"] = turn_id

        if state.game_over:
            return TurnResult(
                sender=Sender.SYSTEM,
                content="You are dead. Please refresh the browser to play again.",
            )

        user_message = content
        override = False
        if user_message.startswith("@override"):
            override = True
            user_message = user_message.removeprefix("@override")

        if override:
            damage = 0
        else:
            stage_started_at = perf_counter()
            try:
                assessment = await self._assess_action(state, user_message)
            except LLMError:
                self._record_stage(correlation_id, game_id, turn_id, "action_assessment", stage_started_at, "error")
                return self._model_error(correlation_id)
            accepted = assessment.relevant and assessment.realistic
            self._record_stage(
                correlation_id,
                game_id,
                turn_id,
                "action_assessment",
                stage_started_at,
                "success",
                accepted=accepted,
            )
            rejection = self._rejection_for(assessment)
            if rejection is not None:
                return rejection
            damage = assessment.damage

        stage_started_at = perf_counter()
        try:
            narration = await self._get_narration_result(state, user_message)
        except LLMError:
            self._record_stage(correlation_id, game_id, turn_id, "narration", stage_started_at, "error")
            return self._model_error(correlation_id)
        self._record_stage(correlation_id, game_id, turn_id, "narration", stage_started_at, "success", accepted=True)
        reply = narration.content
        if len(reply) == 0:
            return self._error(500, "Gamemaster failed to generate a response.")

        self._apply_state_delta(state, narration.state_delta)
        left_behind_notes = self._apply_inventory_operations(state, reply, narration.inventory_operations)
        if left_behind_notes:
            reply = reply + "\n\n" + " ".join(left_behind_notes)
        quest_resolved = self._apply_quest_operations(state, reply, narration.quest_operations)
        state.hit_points = max(MIN_HIT_POINTS, state.hit_points - damage)

        moment_result: tuple[StoryMoment, bytes] | None = None
        if damage >= MOMENT_DAMAGE_THRESHOLD or quest_resolved or narration.possible_moment:
            moment_result = await self._capture_moment(state, reply)

        if state.hit_points <= 0:
            stage_started_at = perf_counter()
            try:
                self._mark_game_over(state)
            except LLMError:
                self._record_stage(correlation_id, game_id, turn_id, "game_over_summary", stage_started_at, "error")
                return self._model_error(correlation_id)
            self._record_stage(correlation_id, game_id, turn_id, "game_over_summary", stage_started_at, "success")
            self._update_chat_history(state, user_message, None)
            stage_started_at = perf_counter()
            try:
                self.repository.save_game(state)
            except RevisionConflictError:
                self._record_stage(correlation_id, game_id, turn_id, "persist_turn", stage_started_at, "conflict")
                return self._conflict()
            self._record_stage(correlation_id, game_id, turn_id, "persist_turn", stage_started_at, "success")
            await self._refresh_summary_if_needed(state, correlation_id, game_id, turn_id)
            return TurnResult(
                sender=Sender.SYSTEM,
                content="Oh, no! Unfortunately, you have died!",
                game_over_summary=state.game_over_summary,
                hit_points=state.hit_points,
                world_state=state.world_state.to_api_dict(),
                player_attributes=state.player_attributes.to_api_dict(),
                story_summary=state.story_summary,
                unresolved_threads=list(state.unresolved_threads),
                moment=self._moment_response(moment_result),
            )

        self._update_chat_history(state, user_message, reply)
        stage_started_at = perf_counter()
        try:
            self.repository.save_game(state)
        except RevisionConflictError:
            self._record_stage(correlation_id, game_id, turn_id, "persist_turn", stage_started_at, "conflict")
            return self._conflict()
        self._record_stage(correlation_id, game_id, turn_id, "persist_turn", stage_started_at, "success")
        await self._refresh_summary_if_needed(state, correlation_id, game_id, turn_id)

        return TurnResult(
            sender=Sender.GAMEMASTER,
            content=reply,
            hit_points=state.hit_points,
            world_state=state.world_state.to_api_dict(),
            player_attributes=state.player_attributes.to_api_dict(),
            story_summary=state.story_summary,
            unresolved_threads=list(state.unresolved_threads),
            moment=self._moment_response(moment_result),
        )

    def discard_item(self, game_id: str | None, item_id: str | None) -> TurnResult:
        if not self._is_valid_id(game_id):
            return self._error(400, "Game ID is required. Please initialize or load a game first.")
        if not self._is_valid_id(item_id):
            return self._error(400, "Item ID is required.")

        state = self.repository.get_game(game_id)
        if state is None:
            return self._error(400, "Invalid game ID. Please initialize or load a game first.")

        item = self._find_inventory_item_by_id(state.world_state.inventory, item_id)
        if item is None:
            return self._error(400, "Item not found in inventory.")

        state.world_state.inventory.remove(item)
        try:
            self.repository.save_game(state)
        except RevisionConflictError:
            return self._conflict()

        return TurnResult(
            sender=Sender.SYSTEM,
            content=f"You discard the {item.name}.",
            world_state=state.world_state.to_api_dict(),
            player_attributes=state.player_attributes.to_api_dict(),
        )

    @staticmethod
    def _find_inventory_item_by_id(items: list[InventoryItem], item_id: str) -> InventoryItem | None:
        for item in items:
            if item.id == item_id:
                return item
        return None

    async def generate_starting_state(
        self, player_name: str, world_theme: str, player_description: str
    ) -> StartingStateResult:
        system_prompt, user_prompt = prompts.chargen(player_name, world_theme, player_description)
        return await self.llm_client.async_structured(system_prompt, user_prompt, StartingStateResult)

    async def _assess_action(self, state: State, user_message: str) -> ActionAssessment:
        system_prompt, user_prompt = prompts.action_assessment(state, user_message)
        return await self.llm_client.async_structured(system_prompt, user_prompt, ActionAssessment)

    def _rejection_for(self, assessment: ActionAssessment) -> TurnResult | None:
        if assessment.relevant and assessment.realistic:
            return None

        if not assessment.relevant and not assessment.realistic:
            content = "Your message is not relevant or realistic."
        elif not assessment.relevant:
            content = "Your message is not relevant to the game story."
        else:
            content = "Your message does not respect the realism of the game story."
        return self._error(400, content)

    async def _get_narration_result(self, state: State, user_message: str) -> NarrationResult:
        return await self.llm_client.async_structured_messages(
            self.context_builder.narration_messages(state, user_message),
            NarrationResult,
        )

    def _game_over_summary(self, state: State) -> str:
        system_prompt, user_prompt = prompts.game_over_summmary(state)
        return self.llm_client.text(system_prompt, user_prompt)

    def _mark_game_over(self, state: State) -> None:
        state.game_over = True
        state.game_over_summary = self._game_over_summary(state)

    async def _refresh_summary_if_needed(
        self,
        state: State,
        correlation_id: str,
        game_id: str,
        turn_id: int,
    ) -> None:
        summary_range = self._summary_refresh_range(state)
        if summary_range is None:
            return

        start, end = summary_range
        new_transcript = self._transcript_slice(state, start, end)
        stage_started_at = perf_counter()
        try:
            summary = await self._summarize_story(state, new_transcript)
        except Exception:
            self._record_stage(correlation_id, game_id, turn_id, "rolling_summary", stage_started_at, "error")
            return

        state.story_summary = summary.story_summary
        state.unresolved_threads = summary.unresolved_threads
        state.summary_through_turn = end
        try:
            self.repository.save_game(state)
        except RevisionConflictError:
            self._record_stage(correlation_id, game_id, turn_id, "rolling_summary", stage_started_at, "conflict")
            return
        self._record_stage(correlation_id, game_id, turn_id, "rolling_summary", stage_started_at, "success")

    def _summary_refresh_range(self, state: State) -> tuple[int, int] | None:
        total_turns = self._completed_turn_count(state)
        end = max(0, total_turns - self.recent_turns_to_keep_unsummarized)
        unsummarized_turns = end - state.summary_through_turn
        if unsummarized_turns < self.summary_refresh_turn_threshold:
            return None
        return (state.summary_through_turn, end)

    async def _summarize_story(self, state: State, new_transcript: list[dict[str, str]]) -> StorySummaryResult:
        system_prompt, user_prompt = prompts.rolling_summary(
            state.story_summary,
            state.unresolved_threads,
            new_transcript,
        )
        return await self.llm_client.async_structured(system_prompt, user_prompt, StorySummaryResult)

    @staticmethod
    def _completed_turn_count(state: State) -> int:
        return sum(1 for message in state.chat_history if message.get("role") == "user")

    @staticmethod
    def _transcript_slice(state: State, start_turn: int, end_turn: int) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        current_turn = -1
        for message in state.chat_history:
            role = message.get("role")
            content = message.get("content")
            if role == "system":
                continue
            if role == "user":
                current_turn += 1
            if start_turn <= current_turn < end_turn and role in {"user", "assistant"} and isinstance(content, str):
                selected.append({"role": role, "content": content})
            if current_turn >= end_turn:
                break
        return selected

    def _apply_state_delta(self, state: State, state_delta: StateDelta) -> None:
        for operation in state_delta.operations:
            self._apply_state_delta_operation(state, operation)

    def _apply_state_delta_operation(self, state: State, operation: StateDeltaOperation) -> None:
        key = operation.key.strip()
        if not key:
            return

        world_state = state.world_state
        match operation.operation:
            case "set_location":
                if operation.value is not None:
                    world_state.current_location = str(operation.value).strip()
            case "add_condition":
                self._append_unique(world_state.conditions, key)
            case "remove_condition":
                self._remove_if_present(world_state.conditions, key)
            case "upsert_npc":
                if operation.value is not None:
                    world_state.known_npcs[key] = str(operation.value)
            case "set_relationship":
                if operation.value is not None:
                    world_state.relationships[key] = str(operation.value)
            case "set_world_flag":
                world_state.world_flags[key] = operation.value

    def _apply_inventory_operations(
        self,
        state: State,
        narration_content: str,
        operations: list[InventoryOperation],
    ) -> list[str]:
        world_state = state.world_state
        left_behind_notes: list[str] = []
        for operation in operations:
            name = operation.name.strip()
            if not name or not self._is_grounded(name, narration_content):
                continue
            match operation.operation:
                case "add_item":
                    added_weight = operation.weight_kg * operation.quantity
                    projected_weight = world_state.total_inventory_weight_kg() + added_weight
                    if projected_weight > state.player_attributes.max_carry_weight_kg:
                        left_behind_notes.append(f"(Too heavy to carry — the {name} is left behind.)")
                        continue
                    existing = self._find_inventory_item(world_state.inventory, name)
                    if existing is not None:
                        existing.quantity += operation.quantity
                    else:
                        world_state.inventory.append(
                            InventoryItem(
                                name=name,
                                description=operation.description,
                                weight_kg=operation.weight_kg,
                                quantity=operation.quantity,
                            )
                        )
                case "remove_item":
                    existing = self._find_inventory_item(world_state.inventory, name)
                    if existing is None:
                        continue
                    if existing.quantity > operation.quantity:
                        existing.quantity -= operation.quantity
                    else:
                        world_state.inventory.remove(existing)
        return left_behind_notes

    @staticmethod
    def _find_inventory_item(items: list[InventoryItem], name: str) -> InventoryItem | None:
        for item in items:
            if item.name.lower() == name.lower():
                return item
        return None

    @staticmethod
    def _is_grounded(text: str, narration_content: str) -> bool:
        text = text.strip().lower()
        if not text:
            return False
        return text in narration_content.lower()

    @staticmethod
    def _is_quest_grounded(text: str, narration_content: str) -> bool:
        """Looser grounding check for quest text: the model authors a formalized
        title/step/outcome rather than quoting the narration verbatim, so an exact
        substring match (as used for inventory item names) is too strict here."""
        text = text.strip().lower()
        if not text:
            return False
        narration_lower = narration_content.lower()
        if text in narration_lower:
            return True
        significant_words = [
            word
            for word in re.findall(r"[a-z']+", text)
            if word not in QUEST_GROUNDING_STOPWORDS and len(word) >= 4
        ]
        if not significant_words:
            return False
        return any(word in narration_lower for word in significant_words)

    def _apply_quest_operations(
        self,
        state: State,
        narration_content: str,
        operations: list[QuestOperation],
    ) -> bool:
        world_state = state.world_state
        any_resolved = False
        for operation in operations:
            title = operation.title.strip()
            if not title:
                continue
            match operation.operation:
                case "start_quest":
                    if not self._is_quest_grounded(title, narration_content):
                        continue
                    if self._find_quest_by_title(world_state.quests, title) is not None:
                        continue
                    world_state.quests.append(
                        Quest(
                            title=title,
                            description=operation.description,
                            status="active",
                            current_step=operation.next_step,
                        )
                    )
                case "advance_quest":
                    next_step = operation.next_step.strip()
                    if not next_step or not self._is_quest_grounded(next_step, narration_content):
                        continue
                    quest = self._find_quest_by_title(world_state.quests, title)
                    if quest is None or quest.status != "active":
                        continue
                    if quest.current_step:
                        quest.step_history.append(quest.current_step)
                    quest.current_step = next_step
                case "resolve_quest":
                    outcome = operation.outcome.strip()
                    if not outcome or not self._is_quest_grounded(outcome, narration_content):
                        continue
                    quest = self._find_quest_by_title(world_state.quests, title)
                    if quest is None or quest.status != "active":
                        continue
                    if quest.current_step:
                        quest.step_history.append(quest.current_step)
                    quest.current_step = ""
                    quest.status = "resolved"
                    quest.outcome = operation.outcome
                    any_resolved = True
        return any_resolved

    @staticmethod
    def _find_quest_by_title(quests: list[Quest], title: str) -> Quest | None:
        for quest in quests:
            if quest.title.lower() == title.lower():
                return quest
        return None

    async def _capture_moment(self, state: State, narration_content: str) -> tuple[StoryMoment, bytes] | None:
        if state._id is None:
            return None
        try:
            system_prompt, user_prompt = prompts.moment(state, narration_content)
            package = await self.llm_client.async_structured(system_prompt, user_prompt, MomentPackage)
            if not package.is_moment:
                return None
            caption = package.caption.strip()
            image_prompt = package.image_prompt.strip()
            if not caption or not image_prompt:
                return None
            if bool_of_str(os.environ.get("SKIP_IMAGE_GENERATION", "false")):
                image_bytes = Image.debug_backdrop_bytes()
            else:
                image_bytes = await self.llm_client.generate_image_bytes(image_prompt, MOMENT_IMAGE_SIZE)
            return self.repository.add_moment(state._id, caption, image_bytes), image_bytes
        except Exception:
            return None

    @staticmethod
    def _moment_response(moment_result: tuple[StoryMoment, bytes] | None) -> dict[str, Any] | None:
        if moment_result is None:
            return None
        moment, image_bytes = moment_result
        return {
            "id": moment.id,
            "caption": moment.caption,
            "imageSrc": Image.json_content_from_bytes(image_bytes),
        }

    @staticmethod
    def _append_unique(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)

    @staticmethod
    def _remove_if_present(values: list[str], value: str) -> None:
        if value in values:
            values.remove(value)

    @staticmethod
    def _update_chat_history(state: State, user_message: str, gamemaster_reply: str | None) -> None:
        state.chat_history.append({"role": "user", "content": user_message})
        if gamemaster_reply is not None:
            state.chat_history.append({"role": "assistant", "content": gamemaster_reply})

    @staticmethod
    def _is_valid_id(value: str | None) -> bool:
        return value is not None and len(value.strip()) > 0

    @staticmethod
    def _error(status_code: int, content: str) -> TurnResult:
        return TurnResult(
            sender=Sender.ERROR,
            content=content,
            status_code=status_code,
        )

    def _conflict(self) -> TurnResult:
        return self._error(
            409,
            "Game state was modified by another request. Please reload and try again.",
        )

    def _model_error(self, correlation_id: str) -> TurnResult:
        return self._error(
            502,
            f"The gamemaster is temporarily unavailable. Please try again. Reference: {correlation_id}",
        )

    def _record_stage(
        self,
        correlation_id: str,
        game_id: str,
        turn_id: int,
        stage: str,
        started_at: float,
        status: str,
        accepted: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        is_model_stage = stage in MODEL_TRACE_STAGES
        token_usage = getattr(self.llm_client, "last_token_usage", None) if is_model_stage else None
        retry_count = getattr(self.llm_client, "last_retry_count", None) if is_model_stage else None
        self.trace_recorder.record(
            StageTrace(
                correlation_id=correlation_id,
                game_id=game_id,
                turn_id=turn_id,
                stage=stage,
                duration_ms=max(0, (perf_counter() - started_at) * 1000),
                status=status,
                accepted=accepted,
                model=getattr(self.llm_client, "text_model", None) if is_model_stage else None,
                prompt_version=prompts.PROMPT_VERSION,
                token_usage=dict(token_usage) if isinstance(token_usage, dict) else None,
                retry_count=retry_count,
                metadata=safe_metadata(metadata),
            )
        )
