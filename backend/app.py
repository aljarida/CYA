from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from enum import Enum, auto
import logging

import os

load_dotenv()

class Damage(Enum):
    ZERO = auto()
    ONE = auto()
    DEADLY = auto()

logging.basicConfig(
    level=logging.DEBUG,  # or INFO
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Load environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# In-memory game state
state = {
    "playerName": None,
    "playerDescription": None,
    "worldTheme": None,
    "gamePrompt": None,
    "chatHistory": [],
    "HP": -1,
}

# SYSTEM PROMPT TEMPLATE
SYSTEM_PROMPT_TEMPLATE = """
    You are a gamemaster for a text-based adventure. 
    The game setting is the following:

    World Theme: {worldTheme}
    Player: {playerName}
    Player Description: {playerDescription}

    Please keep your responses relatively short on the average, unless something extremely eventful occurs.
    Please also ensure that your responses respect the four component parts (World Theme/Description, and Player Theme/Description) well.

    Take it step by step! You have got this.
"""

def paint_player():
    prompt = f"""
            Portrait of a person, head and shoulders only, facing forward.
            The person is described as: "{state['playerDescription']}". 
            The world is described as: "{state['worldTheme']}". 
            No text, no full body, no logos, no fantastical elements unless specified. 
            Realistic proportions, painted in oil-painting style, symmetrical framing.
        """.strip()

    result = client.images.generate(
        model="dall-e-2",
        prompt=prompt,
        size="512x512",
        n=1
    )

    return result.data[0].url

def setup_game_prompt():
    system_message = SYSTEM_PROMPT_TEMPLATE.format(
        worldTheme=state["worldTheme"],
        playerName=state["playerName"],
        playerDescription=state["playerDescription"]
    )

    # Reset chat history with new system prompt
    state["chatHistory"] = [
        {"role": "system", "content": system_message}
    ]
    
    state["gamePrompt"] = system_message

def setup_hp():
    state["HP"] = 5

def get_gamemaster_reply(user_message):
    state["chatHistory"].append({"role": "user", "content": user_message})
    
    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-4o"
        messages=state["chatHistory"]
    )
    
    reply = response.choices[0].message.content
    state["chatHistory"].append({"role": "assistant", "content": reply})
    return reply

def is_relevant(user_message):
    prompt = f"""
        You are an assistant that only answers 'true' or 'false'. Your job is to determine whether a message is relevant to the game context.

        An example of an irrelevant user message is one in which the game world is historical and medieval, and player describes modern technology such as a television or modern people such as Donald Trump. In this case, you would reply 'false'.


        Determine if the following user message is relevant to the current game situation.

        ====================

        === Game context ===
        "{state['gamePrompt']}"

        === Game story thus far ===
        "{state['chatHistory'][1:]}"
        
        === User message ===
        "{user_message}"

        ====================
        Is this user message relevant to the game context and story? Answer only 'true' or 'false'.
    """
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    reply = response.choices[0].message.content

    logging.info("Received the following to is_relevant: %s", reply)

    if reply is None:
        return False

    match reply.strip().lower():
        case 'true' | "'true'" | '"true"':
            return True
        case _:
            return False

def is_damaging() -> Damage:
    prompt = f"""
        You are an assistant that only answers with the following three options:
        'yes'
        'no'
        'hugely'
        
        Your job is to analyze the game context to determine if the most recent player action and most recent game response describe a scenario in which the player should be damaged or lose all HP.

        For example, if a player wrote, "I attack the bear with all my great might, sure to tear it apart.", you would analyse the player's traits to determine if they could realistically do this. If in your analysis you determine that the player could not, because they are "but a peasant" or a "nerdy doctor", you would return "yes", indicating that the player should incur damage. If the blow were deemed by you to be fatal, you would reply "hugely". If the player were a superhero, you might reply "no".

        Note that things can be hugely even if they do not involve direct conflict. For example, if a player wrote I choose to sit in a wheatfield for the next 3 months, eating nothing, drinking nothing.", you would be correct to reply 'hugely'.

        That all said, please see the important context below for rendering your decision now:

        === Game story prior ===
        "{state['chatHistory'][1:-2]}"
        
        === Recent user message to judge ===
        "{state['chatHistory'][-2]}"

        === Recent system response to use in judgement ===
        "{state['chatHistory'][-1]}"

        Is it 'yes', 'no', or 'hugely'?
    """.strip()
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    reply = response.choices[0].message.content
   

    logging.info("Received the following to is_damaging: %s", reply)
    
    if reply is None:
        return Damage.ZERO

    match reply.lower().strip():
        case "yes" | "'yes'" | '"yes"':
            return Damage.ONE
        case "hugely" | "'hugely'" | '"hugely"':
            return Damage.DEADLY
        case _:
            return Damage.ZERO



@app.route('/api/initialize', methods=['POST'])
def initialize():
    data = request.get_json()
    required_fields = ["playerName", "playerDescription", "worldTheme"]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Update state
    for field in required_fields:
        state[field] = data[field]

    setup_hp()
    setup_game_prompt()
    portrait_url = paint_player()
    return jsonify({
        "status": "initialized",
        "systemPrompt": state["chatHistory"][0]["content"],
        "portraitUrl": portrait_url,
    })

@app.route('/api/response', methods=['POST'])
def response():
    data = request.get_json()
    if "content" not in data:
        return jsonify({"error": "Missing 'content' in request"}), 400

    user_message = data["content"]
    if not is_relevant(user_message):
        return jsonify({"error": "User reply is not relevant"}), 400

    reply = get_gamemaster_reply(user_message)

    dmg = is_damaging()
    
    if dmg == Damage.ONE:
        state["HP"] -= 1

    assert(state["HP"] >= 0)
    if dmg == Damage.DEADLY or state["HP"] == 0:
        state["HP"] = 0
        return jsonify({"content": "You have died!", "hitPoints": state["HP"]})

    return jsonify({"content": reply, "hitPoints": state["HP"]})

if __name__ == '__main__':
    app.run(debug=True, port=3000)

