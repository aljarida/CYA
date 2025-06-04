from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Load environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# In-memory game state
state = {
    "playerName": None,
    "playerDescription": None,
    "worldTheme": None,
    "worldDescription": None,
    "gamePrompt": None,
    "chatHistory": []
}

# SYSTEM PROMPT TEMPLATE
SYSTEM_PROMPT_TEMPLATE = """
    You are a gamemaster for a text-based adventure. 
    The game setting is the following:

    World Theme: {worldTheme}
    World Description: {worldDescription}

    Player: {playerName}
    Player Description: {playerDescription}

    Please keep your responses relatively short on the average, unless something extremely eventful occurs.
    Please also ensure that your responses respect the four component parts (World Theme/Description, and Player Theme/Description) well.

    Take it step by step! You have got this.
"""

def paint_player():
    prompt = f"""
            Portrait of a person, head and shoulders only, facing forward, in the style of a character selection screen from a medieval strategy game. 
            The person is described as: "{state['playerDescription']}". 
            The world background is: "{state['worldDescription']}". 
            No text, no full body, no logos, no weapons, no fantastical elements unless specified. 
            Neutral lighting, realistic proportions, painted illustration style, symmetrical framing.
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
        worldDescription=state["worldDescription"],
        playerName=state["playerName"],
        playerDescription=state["playerDescription"]
    )

    # Reset chat history with new system prompt
    state["chatHistory"] = [
        {"role": "system", "content": system_message}
    ]
    
    state["gamePrompt"] = system_message

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
        You are an assistant that only answers 'true' or 'false'.

        Determine if the following user message is relevant to the current game situation.

        ====================

        === Game context ===
        "{state['gamePrompt']}"

        === Game story thus far ===
        "{state['chatHistory'][1:]}"
        
        === User message ===
        "{user_message}"

        ====================

        An example of an irrelevant user message is one in which the game world is historical and medieval, and player describes modern technology such as a gun or modern people such as Donald Trump. In this case, you would return 'false'.

        Is this user message relevant to the game context? Answer only 'true' or 'false'.
    """

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-4o"
        messages=state["chatHistory"]
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    reply = response.choices[0].message.content

    if reply is None:
        return False

    return reply.strip().lower() == 'true'

@app.route('/api/initialize', methods=['POST'])
def initialize():
    data = request.get_json()
    required_fields = ["playerName", "playerDescription", "worldTheme", "worldDescription"]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Update state
    for field in required_fields:
        state[field] = data[field]

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
    return jsonify({"content": reply})

if __name__ == '__main__':
    app.run(debug=True, port=3000)

