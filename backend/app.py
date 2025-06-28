from flask import Flask, request, jsonify
from flask.typing import ResponseReturnValue
from flask_cors import CORS

from openai import AsyncOpenAI, OpenAI
from openai.types import ImagesResponse
from openai.types.chat import ChatCompletion

from dotenv import load_dotenv
from typing import Any, Callable
import os
import asyncio
import re

from bson.objectid import ObjectId

import prompts
from classes import MAX_HIT_POINTS, State, Sender
from images import Image, Images
from database import Database
from utils import bool_of_str

app: Flask = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

load_dotenv()
client: OpenAI = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
async_client: AsyncOpenAI = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

state: State = State()

db: Database = Database()

def empty_str_if_none(reply: str | None) -> str:
    return reply if reply is not None else ""

async def get_new_images_for(s: State) -> Images:
    """Obtain portrait and backdrop images given that a provided State object with a valid _id."""
    assert(s._id is None)
    db.save_game(s)
    assert(s._id is not None)

    async def generate_image_with(prompt: str, fallback: str, resolution):
        if bool_of_str(os.environ["DEBUG"]):
            return os.environ[fallback]

        try:
            result: ImagesResponse = await async_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=resolution,
                n=1
            )

            return empty_str_if_none(result.data[0].url)
        except:
            return os.environ[fallback]

    async def get_portrait_url() -> str:
        """Obtain debug image portrait URL or generate a new portrait image URL."""
        return await generate_image_with(
            prompts.portrait(state),
            "PLACEHOLDER_PORTRAIT_URL",
            "1024x1024"
        )
        
    async def get_backdrop_url() -> str:
        return await generate_image_with(
            prompts.backdrop(state),
            "PLACEHOLDER_BACKDROP_URL",
            "1792x1024",
        )


    portrait_url, backdrop_url = await asyncio.gather(
        get_portrait_url(),
        get_backdrop_url()
    )

    return Images(
        s._id,
        Image.bytes_from_url(portrait_url),
        Image.bytes_from_url(backdrop_url),
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

def game_over():
    state.game_over = True
    state.game_over_summary = game_over_summmary()

def update_chat_history(user_message: str, gamemaster_reply: str | None) -> None:
    state.chat_history.append({"role": "user", "content": user_message})
    if gamemaster_reply is not None:
        state.chat_history.append({"role": "assistant", "content": gamemaster_reply})

def get_gamemaster_reply(user_message: str) -> str:
    state.chat_history.append({"role": "user", "content": user_message}) # Temporarily append.
    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=state.chat_history
    )
    
    reply: str = empty_str_if_none(response.choices[0].message.content)
    
    state.chat_history.pop() # Pop to keep state unaffected by function call.
    return reply

def is_relevant(user_message: str) -> bool:
    sys, user  = prompts.relevant(state, user_message)
    reply: str = response_with_sys_user(sys, user)
    
    match reply.strip().lower():
        case 'true' | "'true'" | '"true"':
            return True
        case _:
            return False

def is_realistic(user_message: str) -> bool:
    sys, user  = prompts.realistic(state, user_message)
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

@app.route('/api/delete_game', methods=['POST'])
def delete_game() -> ResponseReturnValue:
    data: dict[str, Any] = request.get_json()
    _id_string: str | None = data.get('objectIDString')
    if _id_string is None:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Can not delete a game without a valid ObjectIdString!",
            }), 400

    _id: ObjectId = ObjectId(_id_string)
    db.delete_game(_id)
    return jsonify({
            "sender": str(Sender.SYSTEM),
            "content": "Game successfully deleted.",
        }), 200


@app.route('/api/load_game', methods=['POST'])
def load_game() -> ResponseReturnValue:
    data: dict[str, Any] = request.get_json()
    _id_string: str | None = data.get('objectIDString')
    if _id_string is None:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Can not load a game without a valid ObjectIdString!",
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
    
    portrait_bytes, backdrop_bytes = db.get_image_bytes(_id)
    return jsonify({
            "sender": str(Sender.SYSTEM),
            "content": "Game state successfully loaded.",
            "portraitSrc": Image.json_content_from_bytes(portrait_bytes),
            "worldBackdropSrc": Image.json_content_from_bytes(backdrop_bytes),
            "hitPoints": state.hit_points,
        }), 200

@app.route('/api/initialize', methods=['POST'])
def initialize() -> ResponseReturnValue:
    # NOTE: Temporary while in development.
    # NOTE: This cannot be used for multiple users.
    global state
    state = State()

    data: dict[str, Any] = request.get_json()
    required_fields: list[str] = ["playerName", "playerDescription", "worldTheme"]
    
    for field in required_fields:
        assert(field in data)

    camel_case: Callable[[str], str] = lambda s: re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
    for field in required_fields:
        setattr(state, camel_case(field), data[field])

    setup_initialization_prompt()
    images: Images = asyncio.run(get_new_images_for(state))

    db.save_game_and_images(state, images)
    return jsonify({
        "sender": str(Sender.SYSTEM),
        "systemPrompt": state.initialization_prompt,
        "portraitSrc": images.portrait.json_content(),
        "worldBackdropSrc": images.backdrop.json_content(),
        "hitPoints": MAX_HIT_POINTS,
    }), 200

@app.route('/api/response', methods=['POST'])
def response() -> ResponseReturnValue:
    if state.game_over:
        return jsonify({
                "sender": str(Sender.SYSTEM),
                "content": "You are dead. Please refresh the browser to play again.",
            }), 200

    data: dict[str, Any] = request.get_json()
    assert("content" in data.keys()) 

    user_message = data["content"]
    no_override: bool = True
    if user_message.startswith("@override"):
        no_override = False
        user_message: str = user_message.removeprefix("@override")

    if no_override:
        if not is_relevant(user_message):
            return jsonify({
                    "sender": str(Sender.ERROR),
                    "content": "Your message is not relevant to the game story.",
                }), 400

        if not is_realistic(user_message):
            return jsonify({
                    "sender": str(Sender.ERROR),
                    "content": "Your message does not respect the realism of the game story.",
                })

    reply: str = get_gamemaster_reply(user_message)
    if len(reply) == 0:
        return jsonify({
                "sender": str(Sender.ERROR),
                "content": "Gamemaster failed to generate a response.",
            }), 500

    dmg: int = assess_damage(user_message, reply)
    state.hit_points -= dmg

    if state.hit_points <= 0:
        game_over()
        update_chat_history(user_message, None)
        db.save_game(state)
        return jsonify({
                "sender": str(Sender.SYSTEM),
                "content": "Oh, no! Unfortunately, you have died!",
                "gameOverSummary": state.game_over_summary,
                "hitPoints": state.hit_points,
            }), 200
    else:
        update_chat_history(user_message, reply)
        db.save_game(state)
        return jsonify({
                "sender": str(Sender.GAMEMASTER),
                "content": reply,
                "hitPoints": state.hit_points,
            }), 200

if __name__ == '__main__':
    app.run(debug=True, port=3000)
