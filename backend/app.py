from flask import Flask, request, jsonify
from flask.typing import ResponseReturnValue
from flask_cors import CORS

from openai import OpenAI
from openai.types import ImagesResponse
from openai.types.chat import ChatCompletion

from dotenv import load_dotenv
from typing import Any, Callable
import os
import re
import requests

from bson.objectid import ObjectId

import prompts
from classes import State, Sender, Images, Image
from database import Database

PLACEHOLDER_PORTRAIT_URL = "https://upload.wikimedia.org/wikipedia/commons/4/4b/Josef_Bergenthal_oil_painting_portrait.jpg"
PLACEHOLDER_BACKDROP_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/%28Venice%29_Rape_of_Europa_by_Francesco_Zuccarelli_-_Gallerie_Accademia.jpg/1024px-%28Venice%29_Rape_of_Europa_by_Francesco_Zuccarelli_-_Gallerie_Accademia.jpg"

DEBUG_MODE: bool = True

app: Flask = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

load_dotenv()
client: OpenAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

state: State = State()

db: Database = Database()


def empty_str_if_none(reply: str | None) -> str:
    return reply if reply is not None else ""

def get_portrait_url() -> str:
    if DEBUG_MODE:
        return PLACEHOLDER_PORTRAIT_URL

    prompt: str = prompts.portrait(state)
    try:
        result: ImagesResponse = client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            size="512x512",
            n=1
        )

        return empty_str_if_none(result.data[0].url)
    except:
        return PLACEHOLDER_PORTRAIT_URL
    
def get_landscape_url() -> str:
    if DEBUG_MODE:
        return PLACEHOLDER_BACKDROP_URL

    prompt: str = prompts.backdrop(state)
    try:
        result: ImagesResponse = client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            size="1024x1024",
            n=1
        )

        return empty_str_if_none(result.data[0].url)
    except Exception as e:
        return str(e)

def get_images(s: State) -> Images:
    assert(s._id is not None)
    portrait_url: str = get_portrait_url()
    landscape_url: str = get_landscape_url()
    return Images(
        s._id,
        Image.bytes_from_url(portrait_url),
        Image.bytes_from_url(landscape_url),
    )

def response_with_sys_user(sys_content: str, user_content: str) -> str:
    response: ChatCompletion = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    reply: str = empty_str_if_none(response.choices[0].message.content)
    return reply


def setup_initialization_prompt() -> None:
    prompt: str = prompts.initialization(state)

    state.chat_history = [
        {"role": "system", "content": prompt}
    ]
    
    state.initialization_prompt = prompt

def get_gamemaster_reply(user_message: str) -> str:
    state.chat_history.append({"role": "user", "content": user_message})
    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=state.chat_history
    )
    
    reply: str = empty_str_if_none(response.choices[0].message.content)
    
    state.chat_history.append({"role": "assistant", "content": reply})

    return reply

def is_relevant(user_message: str):
    sys, user  = prompts.relevant(state, user_message)
    reply: str = response_with_sys_user(sys, user)
    
    match reply.strip().lower():
        case 'true' | "'true'" | '"true"':
            return True
        case _:
            return False

def assess_damage(user_message: str, gamemaster_reply: str) -> int:
    sys, user = prompts.damaging(state, user_message, gamemaster_reply)
    reply: str = response_with_sys_user(sys, user)
    
    remove_quotes: Callable[[str], str] = lambda s: s.replace('"', '').replace("'", '')
    damage: str = remove_quotes(reply).lower().strip()

    match damage:
        case "5" | "4" | "3" | "2" | "1":
            return int(damage)
        case _:
            return 0

def game_over_summmary() -> str:
    sys, user = prompts.game_over_summmary(state)
    return response_with_sys_user(sys, user)    

@app.route('/api/existing_games', methods=['GET'])
def existing_games() -> ResponseReturnValue:
    saves: list[State] = db.all_games()
    results: list[dict[str, Any]] = []
    for s in saves:
        results.append({
            "playerName": s.player_name,
            "playerDescription": s.player_description,
            "worldTheme": s.world_theme,
            "gameOverSummary": s.game_over_summary,
            "gameOver": s.game_over,
            "createdAt": s.created_at.isoformat(),
            "updatedAt": s.updated_at.isoformat() if s.updated_at is not None else "",
            "objectIDString": str(s._id),
            "chatHistory": s.chat_history,

        })

    return jsonify({ "results": results }), 200


# TODO: Update logic to obtain images from database and then
# send them to the front end for display.
@app.route('/api/load_game', methods=['POST'])
def load_game() -> ResponseReturnValue:
    data: dict[str, Any] = request.get_json()
    _id_string: str | None = data.get('objectIDString')
    if _id_string is None:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Can not load a game without a save ID string!",
            }), 400

    _id: ObjectId = ObjectId(_id_string)
    save_data, ok = db.get_game_data(_id)
    if not ok:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": f"Provided save ID {_id_string} is not valid."
            }), 400

    assert(save_data is not None)
    for key in save_data.keys():
        setattr(state, key, save_data[key])

    return jsonify({
            "sender": str(Sender.SYSTEM),
            "content": "Game state successfully loaded."
        }), 200



@app.route('/api/initialize', methods=['POST'])
def initialize() -> ResponseReturnValue:
    data: dict[str, Any] = request.get_json()
    required_fields: list[str] = ["playerName", "playerDescription", "worldTheme"]
    
    for field in required_fields:
        if field not in data:
            return jsonify({
                    "sender": str(Sender.ERROR),
                    "content": f"Missing field: {field}!"
                }), 400

    camel_case: Callable[[str], str] = lambda s: re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
    for field in required_fields:
        setattr(state, camel_case(field), data[field])

    setup_initialization_prompt()
    images: Images = get_images(state)

    # TODO: Change API interactions to ensure that bytes can be sent over.
    db.save_game_and_images(state, images)
    return jsonify({
        "sender": str(Sender.SYSTEM),
        "systemPrompt": state.initialization_prompt,
        "portraitUrl": portrait_url,
        "worldBackdropUrl": world_backdrop_url,
    }), 200

@app.route('/api/response', methods=['POST'])
def response() -> ResponseReturnValue:
    if state.game_over:
        return jsonify({
                "sender": str(Sender.SYSTEM),
                "content": "You are dead. Please refresh the browser to play again.",
            }), 200

    data = request.get_json()
    if "content" not in data:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Missing 'content' in request."
            }), 400

    user_message = data["content"]
    if not is_relevant(user_message):
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Your message is not relevant to the game story."
            }), 400

    reply: str = get_gamemaster_reply(user_message)
    if len(reply) == 0:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Gamemaster failed to generate a response."
            }), 500

    dmg: int = assess_damage(user_message, reply)
    state.hit_points -= dmg

    if state.hit_points <= 0:
        state.game_over = True
        state.game_over_summary = game_over_summmary()
        db.save_game(state)

        return jsonify({
                "sender": str(Sender.SYSTEM),
                "content": "Oh, no! Unfortunately, you have died!",
                "gameOverSummary": state.game_over_summary,
                "hitPoints": state.hit_points,
            }), 200

    db.save_game(state)
    return jsonify({
            "sender": str(Sender.GAMEMASTER),
            "content": reply,
            "hitPoints": state.hit_points
        }), 200

if __name__ == '__main__':
    app.run(debug=True, port=3000)
