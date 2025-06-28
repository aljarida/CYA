from classes import State

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

def initialization(state: State) -> str:
    prompt: str = INITIALIZATION_PROMPT.format(
        world_theme=state.world_theme,
        player_name=state.player_name,
        player_description=state.player_description,
    )

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

def portrait(state: State) -> str:
    prompt: str = PORTRAIT_PROMPT.format(
        world_theme=state.world_theme,
        player_description=state.player_description,
    )

    return prompt




BACKDROP_PROMPT = """
Landscape or cityscape of a world.

Perspective is up high and far away.

The world is described as: "{world_theme}". 

No text, no logos.

Done as photo-realistic painting.
"""

def backdrop(state: State) -> str:
    prompt: str = BACKDROP_PROMPT.format(
        world_theme=state.world_theme,
    )

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

def relevant(state: State, user_message: str) -> tuple[str, str]:
    prompt_user: str = RELEVANT_PROMPT_USER.format(
        initialization_prompt=state.initialization_prompt,
        game_story=state.chat_history[1:],
        user_message=user_message,
    )

    return (RELEVANT_PROMPT_SYS, prompt_user)




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

def realistic(state: State, user_message: str) -> tuple[str, str]:
    prompt_user: str = REALISTIC_PROMPT_USER.format(
        initialization_prompt=state.initialization_prompt,
        game_story=state.chat_history[1:],
        user_message=user_message,
    )

    return (REALISTIC_PROMPT_SYS, prompt_user)




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

def damaging(
        state: State,
        user_message: str,
        gamemaster_reply: str
        ) -> tuple[str, str]:

    prompt_user: str = DAMAGING_PROMPT_USER.format(
        player_description=state.player_description,
        game_story=state.chat_history[1:-2] if len(state.chat_history[1:-2]) > 0 else "[No other context.]",
        user_message=user_message,
        gamemaster_reply=gamemaster_reply,
    )
    
    return (DAMAGING_PROMPT_SYS, prompt_user)




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

def game_over_summmary(
        state: State,
        ) -> tuple[str, str]:

    prompt_user: str = GAME_OVER_SUMMARY_PROMPT_USER.format(
        game_story=state.chat_history[1:-2] if len(state.chat_history[1:-2]) > 0 else "[No other context.]",
        player_name=state.player_name,
        story=state.chat_history
    )
    
    return (GAME_OVER_SUMMARY_PROMPT_SYS, prompt_user)
