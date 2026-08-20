from dataclasses import dataclass
from string import Formatter
from types import MappingProxyType
from typing import Any, Literal, Mapping

from classes import State

PromptName = Literal[
    "initialization",
    "portrait",
    "backdrop",
    "relevant.system",
    "relevant.user",
    "realistic.system",
    "realistic.user",
    "action_assessment.system",
    "action_assessment.user",
    "damaging.system",
    "damaging.user",
    "game_over_summary.system",
    "game_over_summary.user",
    "rolling_summary.system",
    "rolling_summary.user",
    "suggested_response.system",
    "suggested_response.user",
    "chargen.system",
    "chargen.user",
    "moment.system",
    "moment.user",
]

PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class PromptTemplate:
    name: PromptName
    version: str
    template: str
    variables: tuple[str, ...]

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "variables": self.variables,
        }


@dataclass(frozen=True)
class PromptRender:
    name: PromptName
    version: str
    text: str
    variables: Mapping[str, Any]

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "variables": tuple(self.variables.keys()),
        }


def _template_variables(template: str) -> tuple[str, ...]:
    variables: list[str] = []
    for _, field_name, _, _ in Formatter().parse(template):
        if field_name is None:
            continue
        if field_name not in variables:
            variables.append(field_name)
    return tuple(variables)


def _prompt_template(name: PromptName, template: str) -> PromptTemplate:
    return PromptTemplate(
        name=name,
        version=PROMPT_VERSION,
        template=template,
        variables=_template_variables(template),
    )


def render_prompt(name: PromptName, variables: Mapping[str, Any] | None = None) -> PromptRender:
    prompt_template = PROMPT_REGISTRY[name]
    variables = variables or {}
    missing_variables = set(prompt_template.variables) - set(variables.keys())
    if missing_variables:
        missing = ", ".join(sorted(missing_variables))
        raise KeyError(f"Missing variables for prompt '{name}': {missing}")

    return PromptRender(
        name=prompt_template.name,
        version=prompt_template.version,
        text=prompt_template.template.format(**variables),
        variables=MappingProxyType(dict(variables)),
    )


def _format_sequence(values: list[str], empty: str) -> str:
    return ", ".join(values) if values else empty


def _format_mapping(values: Mapping[str, Any], empty: str) -> str:
    if not values:
        return empty
    return ", ".join(f"{key}: {value}" for key, value in values.items())


def _format_inventory(items: list[Any], empty: str) -> str:
    if not items:
        return empty
    descriptions = []
    for item in items:
        quantity_suffix = f" x{item.quantity}" if item.quantity > 1 else ""
        detail = f" ({item.description})" if item.description else ""
        descriptions.append(f"{item.name}{quantity_suffix}, {item.weight_kg}kg{detail}")
    return "; ".join(descriptions)


def _format_quests(quests: list[Any], empty: str) -> str:
    if not quests:
        return empty
    descriptions = []
    for quest in quests:
        if quest.status == "active":
            lead = f" — lead: {quest.current_step}" if quest.current_step else ""
            descriptions.append(f"{quest.title} (active{lead})")
        else:
            outcome = f" — outcome: {quest.outcome}" if quest.outcome else ""
            descriptions.append(f"{quest.title} (resolved{outcome})")
    return "; ".join(descriptions)


def world_state_context(state: State) -> str:
    world_state = state.world_state
    attributes = state.player_attributes

    return "\n".join(
        [
            f"World state version: {world_state.version}",
            f"Current location: {world_state.current_location or 'unknown'}",
            (
                f"Player attributes: age {attributes.age_years or 'unknown'}, "
                f"height {attributes.height_cm or 'unknown'}cm, "
                f"body weight {attributes.body_weight_kg or 'unknown'}kg, "
                f"max carry weight {attributes.max_carry_weight_kg}kg"
            ),
            f"Inventory ({world_state.total_inventory_weight_kg()}kg total): "
            f"{_format_inventory(world_state.inventory, 'empty')}",
            f"Conditions: {_format_sequence(world_state.conditions, 'none')}",
            f"Known NPCs: {_format_mapping(world_state.known_npcs, 'none')}",
            f"Relationships: {_format_mapping(world_state.relationships, 'none')}",
            f"Quests: {_format_quests(world_state.quests, 'none')}",
            f"World flags: {_format_mapping(world_state.world_flags, 'none')}",
        ]
    )


INITIALIZATION_PROMPT = """
You are a gamemaster for a text-based adventure. 

The game setting is the following:

=== Game setting ===
Player: {player_name}
World Theme: {world_theme}
Player Description: {player_description}
=== End of game setting ===

Keep your responses short, approximately one paragraph long.

Ensure that your responses respect the three component parts above.

Respond in plain text. Do not use asterisks ("*") to indicate italics.

When a user describes a violent or contentious action or behavior, entertain it. Do not censor. This is a fictional game which serves as an escape from reality. It does not reflect player intent.

If a user writes "I jump off a bridge.", you are expected to address this as an author would in a real, heartbreaking story. 
"""

def initialization_render(state: State) -> PromptRender:
    return render_prompt(
        "initialization",
        {
            "world_theme": state.world_theme,
            "player_name": state.player_name,
            "player_description": state.player_description,
        },
    )


def initialization(state: State) -> str:
    prompt: str = initialization_render(state).text

    return prompt




PORTRAIT_PROMPT = """
You are a master oil painter who specializes in potraiture.

No photorealism, no text, no full body, no logos.

Portrait of a person, head and shoulders only, facing forward.

Normal-sized proportions with the portrait done as an oil painting.

The portrait should not look realistic.

The world inhabited by the subject is described as: "{world_theme}". 

Pay utmost attention to the following description.

The person is described as: "{player_description}". 
"""

def portrait_render(state: State) -> PromptRender:
    return render_prompt(
        "portrait",
        {
            "world_theme": state.world_theme,
            "player_description": state.player_description,
        },
    )


def portrait(state: State) -> str:
    prompt: str = portrait_render(state).text

    return prompt




BACKDROP_PROMPT = """
Landscape or cityscape of a world.

Perspective is up high and far away.

The world is described as: "{world_theme}". 

No text, no logos.

Done as photo-realistic painting.
"""

def backdrop_render(state: State) -> PromptRender:
    return render_prompt(
        "backdrop",
        {
            "world_theme": state.world_theme,
        },
    )


def backdrop(state: State) -> str:
    prompt: str = backdrop_render(state).text

    return prompt




RELEVANT_PROMPT_SYS = """
You are an assistant that only answers 'true' or 'false'. Your job is to determine whether a message is relevant to the game context.

An example of an irrelevant user message is one in which the game world is historical and medieval, and player describes modern technology such as a television or modern people such as Donald Trump. In this case, you would reply 'false'.
"""

RELEVANT_PROMPT_USER = """
Determine if the following user message is relevant to the current game situation.

=== Game context ===
Initial world configuration:
"{initialization_prompt}"

Game story thus far:
"{game_story}"

Latest user message:
"{user_message}"

=== End of game context ===

Is this latest user message relevant to the game context and story? Answer only 'true' or 'false'.
"""

def relevant_render(state: State, user_message: str) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "relevant.user",
        {
            "initialization_prompt": state.initialization_prompt,
            "game_story": state.chat_history[1:],
            "user_message": user_message,
        },
    )

    return (render_prompt("relevant.system"), prompt_user)


def relevant(state: State, user_message: str) -> tuple[str, str]:
    prompt_sys, prompt_user = relevant_render(state, user_message)

    return (prompt_sys.text, prompt_user.text)




REALISTIC_PROMPT_SYS = """
You are an assistant that only answers 'true' or 'false'. Your job is to determine whether a message is realistic given the game context. You should strongly press for realism.

A realistic message aligns with the physical, logical, and narrative constraints of the game. 
It should not involve exaggerated, superhuman, or impossible feats unless such powers have been clearly established in the game story.

For example, if the user is in prison, and says, "I inhale as deep as I can, then suddenly exhale greatly, bringing the whole prison down to free myself!", unless the player has established magical abilities, you would certainly respond with 'false'.
"""

REALISTIC_PROMPT_USER = """
Determine if the following user message is realistic within the current game world. 

=== Game context ===
Initial world configuration:
"{initialization_prompt}"

Game story thus far:
"{game_story}"

Latest user message:
"{user_message}"

=== End of game context ===

Is this latest user message realistic given the game context and world rules? Answer only 'true' or 'false'.
"""

def realistic_render(state: State, user_message: str) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "realistic.user",
        {
            "initialization_prompt": state.initialization_prompt,
            "game_story": state.chat_history[1:],
            "user_message": user_message,
        },
    )

    return (render_prompt("realistic.system"), prompt_user)


def realistic(state: State, user_message: str) -> tuple[str, str]:
    prompt_sys, prompt_user = realistic_render(state, user_message)

    return (prompt_sys.text, prompt_user.text)




ACTION_ASSESSMENT_PROMPT_SYS = """
You assess a player's latest action for a text-based adventure game.

Return structured fields only:
- relevant: whether the action fits the current game context and story.
- realistic: whether the action respects the physical, logical, and narrative constraints established so far.
- damage: an integer from 0 to 5 estimating HP loss caused by attempting this action, where 0 is no damage and 5 is fatal.
- reason: a brief explanation for the assessment.
"""

ACTION_ASSESSMENT_PROMPT_USER = """
Assess the following user action against the current game situation.

=== Game context ===
Initial world configuration:
"{initialization_prompt}"

Canonical world state:
"{world_state}"

Game story thus far:
"{game_story}"

Latest user message:
"{user_message}"
=== End of game context ===
"""


def action_assessment_render(state: State, user_message: str) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "action_assessment.user",
        {
            "initialization_prompt": state.initialization_prompt,
            "world_state": world_state_context(state),
            "game_story": state.chat_history[1:] if len(state.chat_history) > 1 else "[No other context.]",
            "user_message": user_message,
        },
    )

    return (render_prompt("action_assessment.system"), prompt_user)


def action_assessment(state: State, user_message: str) -> tuple[str, str]:
    prompt_sys, prompt_user = action_assessment_render(state, user_message)

    return (prompt_sys.text, prompt_user.text)




DAMAGING_PROMPT_SYS = """
You are an assistant that only answers with the following six numbers:
0
1
2
3
4
5

Note that 0 indicates no damage, whereas 5 indicates maximum damage. 5 damage is enough to end a player's game.

Your job is to analyze the game context to determine if the most recent player action and provided most recent game response describe a scenario in which the player should be damaged or lose all HP.

For example, if a player wrote, "I attack the bear with all my great might, sure to tear it apart.", you would analyse the player's traits to determine if they could realistically do this. If in your analysis you determine that the player could not, because they are "but a peasant" or a "nerdy doctor", you would return an answer between 1 and 5, indicating that the player should incur damage. If the blow were deemed by you to be fatal, you would reply with 5. If the player character were a superhero, you might reply "no".

Note that things can be damaging even if they do not involve direct conflict. For example, if a player wrote "I choose to sit in a wheatfield for the next 3 months, eating nothing, drinking nothing.", you would reply iwht a number beyond 0.
"""

DAMAGING_PROMPT_USER = """
Please see the important context below for rendering your decision below:

=== Game context ===
Description of player:
"{player_description}"

Game story thus far:
"{game_story}"

Lastest user message:
"{user_message}"

Recent system response to use in judgement:
"{gamemaster_reply}
=== End of game context ===

Is your response 'yes', 'no', or 'hugely'?
"""

def damaging_render(
        state: State,
        user_message: str,
        gamemaster_reply: str
        ) -> tuple[PromptRender, PromptRender]:

    prompt_user = render_prompt(
        "damaging.user",
        {
            "player_description": state.player_description,
            "game_story": state.chat_history[1:-2] if len(state.chat_history[1:-2]) > 0 else "[No other context.]",
            "user_message": user_message,
            "gamemaster_reply": gamemaster_reply,
        },
    )
    
    return (render_prompt("damaging.system"), prompt_user)


def damaging(
        state: State,
        user_message: str,
        gamemaster_reply: str
        ) -> tuple[str, str]:
    prompt_sys, prompt_user = damaging_render(state, user_message, gamemaster_reply)

    return (prompt_sys.text, prompt_user.text)




GAME_OVER_SUMMARY_PROMPT_SYS = """
Your job is to provide a rich, description, summary of the player's story as experienced thus far.

Be sure to address the player character by their given name.

Please provide the following items a one- to three-paragraph summary of the player's story.

Respond in plain text. Do not refer to the "player" or the "game". Your job is to narrate what happened without breaking immersion.
"""

GAME_OVER_SUMMARY_PROMPT_USER = """
Please find all relevant information for creating a summary of the following player story.

Player name: "{player_name}".

Player's story: "{story}".
"""

def game_over_summmary_render(
        state: State,
        ) -> tuple[PromptRender, PromptRender]:

    prompt_user = render_prompt(
        "game_over_summary.user",
        {
            "game_story": state.chat_history[1:-2] if len(state.chat_history[1:-2]) > 0 else "[No other context.]",
            "player_name": state.player_name,
            "story": state.chat_history,
        },
    )
    
    return (render_prompt("game_over_summary.system"), prompt_user)


def game_over_summmary(
        state: State,
        ) -> tuple[str, str]:
    prompt_sys, prompt_user = game_over_summmary_render(state)

    return (prompt_sys.text, prompt_user.text)




ROLLING_SUMMARY_PROMPT_SYS = """
You maintain a compact rolling summary for a text adventure.

Return structured fields only:
- story_summary: a concise summary of durable story events, discoveries, character facts, and unresolved consequences.
- unresolved_threads: short labels for promises, mysteries, quests, threats, or pending goals that remain open.

Do not repeat recent verbatim transcript. Preserve important facts from the previous summary unless the new turns supersede them.
"""

ROLLING_SUMMARY_PROMPT_USER = """
Update the rolling summary using only the newly eligible transcript turns.

=== Previous summary ===
{previous_summary}
=== End previous summary ===

=== Previous unresolved threads ===
{previous_unresolved_threads}
=== End previous unresolved threads ===

=== Newly eligible transcript ===
{new_transcript}
=== End newly eligible transcript ===
"""


def rolling_summary_render(
    previous_summary: str,
    previous_unresolved_threads: list[str],
    new_transcript: list[dict[str, str]],
) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "rolling_summary.user",
        {
            "previous_summary": previous_summary or "[No previous summary.]",
            "previous_unresolved_threads": (
                "\n".join(f"- {thread}" for thread in previous_unresolved_threads)
                if previous_unresolved_threads
                else "[No unresolved threads.]"
            ),
            "new_transcript": new_transcript if new_transcript else "[No newly eligible transcript.]",
        },
    )

    return (render_prompt("rolling_summary.system"), prompt_user)


def rolling_summary(
    previous_summary: str,
    previous_unresolved_threads: list[str],
    new_transcript: list[dict[str, str]],
) -> tuple[str, str]:
    prompt_sys, prompt_user = rolling_summary_render(previous_summary, previous_unresolved_threads, new_transcript)

    return (prompt_sys.text, prompt_user.text)




SUGGESTED_RESPONSES_PROMPT_SYS = """
You are an assistant that generates suggested player responses for a text-based adventure game.

Your job is to generate a single, short, natural player response that a player might say in response to the gamemaster's most recent message.

The response should:
- Be brief (one sentence or short phrase)
- Be natural and conversational
- Fit the game context and story
- Be something a player character would realistically say or do
- Not break character or reference the game mechanics

Respond with only the suggested player response, nothing else.
"""

SUGGESTED_RESPONSES_PROMPT_USER = """
Generate a suggested player response for the following game situation.

=== Game context ===
Initial world configuration:
"{initialization_prompt}"

Game story thus far:
"{game_story}"

Most recent gamemaster message:
"{gamemaster_reply}"
=== End of game context ===

Generate a single, brief, natural player response that fits this context.
"""

CHARGEN_PROMPT_SYS = """
You generate a plausible starting state for a new player character in a text-based adventure game.

Return structured fields only:
- starting_location: a short, specific place name consistent with the world theme and player description.
- starting_inventory: a small, modest, era- and setting-appropriate list of items the character would plausibly
  already own. Each item needs a name, an optional short description, a realistic weight in kilograms, and a
  quantity. Do not invent implausible or overpowered items.
- starting_conditions: any starting conditions or ailments implied by the description (leave empty if none are
  implied — do not invent injuries or illnesses that were not suggested).
- age_years, height_cm, body_weight_kg: plausible values for the described character, consistent with the world
  theme (adjust for stated species/creature type if applicable).
- max_carry_weight_kg: a plausible carry capacity proportionate to body_weight_kg (roughly 20-35% of body weight)
  unless the description implies unusual strength.
- reason: a brief explanation for the choices made.
"""

CHARGEN_PROMPT_USER = """
Generate a starting character state for the following new game.

=== Game setting ===
Player: {player_name}
World Theme: {world_theme}
Player Description: {player_description}
=== End of game setting ===
"""


def chargen_render(player_name: str, world_theme: str, player_description: str) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "chargen.user",
        {
            "player_name": player_name,
            "world_theme": world_theme,
            "player_description": player_description,
        },
    )

    return (render_prompt("chargen.system"), prompt_user)


def chargen(player_name: str, world_theme: str, player_description: str) -> tuple[str, str]:
    prompt_sys, prompt_user = chargen_render(player_name, world_theme, player_description)

    return (prompt_sys.text, prompt_user.text)


MOMENT_PROMPT_SYS = """
You decide whether a turn in a text-based adventure deserves a rare, illustrated "memorable moment" — a
Total-War-style banner marking a genuinely significant beat: a decisive battle won or lost, a dramatic quest
resolution, a major milestone (a birth, a coronation, a first flight to the stars), or a similarly iconic turning
point.

Most turns do NOT deserve this. Be selective — only mark a moment for beats a player would want to remember and
revisit later.

Return structured fields only:
- is_moment: true only if this turn is genuinely a memorable, illustration-worthy beat.
- caption: if is_moment is true, a short, evocative one-sentence caption for the scene, written like a
  strategy-game banner. Empty string otherwise.
- image_prompt: if is_moment is true, a vivid, concrete visual description suitable for an image-generation model
  to depict the scene (no text or logos in the image). Empty string otherwise.
- reason: a brief explanation for the decision.
"""

MOMENT_PROMPT_USER = """
Consider whether the following narrated turn depicts a moment worth illustrating.

=== World theme ===
{world_theme}
=== End world theme ===

=== Narrated turn ===
{narration_content}
=== End narrated turn ===
"""


def moment_render(state: State, narration_content: str) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "moment.user",
        {
            "world_theme": state.world_theme,
            "narration_content": narration_content,
        },
    )

    return (render_prompt("moment.system"), prompt_user)


def moment(state: State, narration_content: str) -> tuple[str, str]:
    prompt_sys, prompt_user = moment_render(state, narration_content)

    return (prompt_sys.text, prompt_user.text)


PROMPT_REGISTRY = MappingProxyType({
    "initialization": _prompt_template("initialization", INITIALIZATION_PROMPT),
    "portrait": _prompt_template("portrait", PORTRAIT_PROMPT),
    "backdrop": _prompt_template("backdrop", BACKDROP_PROMPT),
    "relevant.system": _prompt_template("relevant.system", RELEVANT_PROMPT_SYS),
    "relevant.user": _prompt_template("relevant.user", RELEVANT_PROMPT_USER),
    "realistic.system": _prompt_template("realistic.system", REALISTIC_PROMPT_SYS),
    "realistic.user": _prompt_template("realistic.user", REALISTIC_PROMPT_USER),
    "action_assessment.system": _prompt_template("action_assessment.system", ACTION_ASSESSMENT_PROMPT_SYS),
    "action_assessment.user": _prompt_template("action_assessment.user", ACTION_ASSESSMENT_PROMPT_USER),
    "damaging.system": _prompt_template("damaging.system", DAMAGING_PROMPT_SYS),
    "damaging.user": _prompt_template("damaging.user", DAMAGING_PROMPT_USER),
    "game_over_summary.system": _prompt_template("game_over_summary.system", GAME_OVER_SUMMARY_PROMPT_SYS),
    "game_over_summary.user": _prompt_template("game_over_summary.user", GAME_OVER_SUMMARY_PROMPT_USER),
    "rolling_summary.system": _prompt_template("rolling_summary.system", ROLLING_SUMMARY_PROMPT_SYS),
    "rolling_summary.user": _prompt_template("rolling_summary.user", ROLLING_SUMMARY_PROMPT_USER),
    "suggested_response.system": _prompt_template("suggested_response.system", SUGGESTED_RESPONSES_PROMPT_SYS),
    "suggested_response.user": _prompt_template("suggested_response.user", SUGGESTED_RESPONSES_PROMPT_USER),
    "chargen.system": _prompt_template("chargen.system", CHARGEN_PROMPT_SYS),
    "chargen.user": _prompt_template("chargen.user", CHARGEN_PROMPT_USER),
    "moment.system": _prompt_template("moment.system", MOMENT_PROMPT_SYS),
    "moment.user": _prompt_template("moment.user", MOMENT_PROMPT_USER),
})


def suggested_response_render(state: State, gamemaster_reply: str) -> tuple[PromptRender, PromptRender]:
    prompt_user = render_prompt(
        "suggested_response.user",
        {
            "initialization_prompt": state.initialization_prompt,
            "game_story": state.chat_history[1:-1] if len(state.chat_history) >= 3 else "[No other context.]",
            "gamemaster_reply": gamemaster_reply,
        },
    )
    
    return (render_prompt("suggested_response.system"), prompt_user)


def suggested_response(state: State, gamemaster_reply: str) -> tuple[str, str]:
    prompt_sys, prompt_user = suggested_response_render(state, gamemaster_reply)

    return (prompt_sys.text, prompt_user.text)
