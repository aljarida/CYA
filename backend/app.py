from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openai import AsyncOpenAI, OpenAI
from openai.types import ImagesResponse
from openai.types.chat import ChatCompletion

from dotenv import load_dotenv
from typing import Any, Callable
import os
import asyncio
import re
import random

from bson.objectid import ObjectId

import prompts
from classes import MAX_HIT_POINTS, State, Sender
from images import Image, Images
from database import Database
from utils import bool_of_str

app: FastAPI = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeleteGameRequest(BaseModel):
    objectIDString: str | None = None

class LoadGameRequest(BaseModel):
    objectIDString: str | None = None

class InitializeRequest(BaseModel):
    playerName: str
    playerDescription: str
    worldTheme: str

class ResponseRequest(BaseModel):
    content: str
    gameId: str | None = None

load_dotenv()
client: OpenAI = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
async_client: AsyncOpenAI = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

db: Database = Database()

def load_state_from_db(game_id: str) -> State | None:
    """Load a State object from the database by game ID."""
    try:
        _id: ObjectId = ObjectId(game_id)
        save_data, ok = db.get_game_data(_id)
        if not ok or save_data is None:
            return None
        
        # Convert MongoDB document to State object
        state = State.deserialize(save_data)
        return state
    except Exception:
        return None

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
            raise Exception("The image request failed for some reason!")

    async def get_portrait_url() -> str:
        """Obtain debug image portrait URL or generate a new portrait image URL."""
        return await generate_image_with(
            prompts.portrait(s),
            "PLACEHOLDER_PORTRAIT_URL",
            "1024x1024"
        )
        
    async def get_backdrop_url() -> str:
        return await generate_image_with(
            prompts.backdrop(s),
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

async def async_response_with_sys_user(sys_content: str, user_content: str) -> str:
    response = await async_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    reply: str = empty_str_if_none(response.choices[0].message.content)
    return reply

async def async_response_with_sys_user_temperature(sys_content: str, user_content: str, temperature: float = 0.7) -> str:
    """Generate a response with configurable temperature for randomness."""
    response = await async_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
    )
    reply: str = empty_str_if_none(response.choices[0].message.content)
    return reply

def setup_initialization_prompt(state: State) -> None:
    prompt: str = prompts.initialization(state)

    state.chat_history = [
        {"role": "system", "content": prompt}
    ]
    
    state.initialization_prompt = prompt

def game_over(state: State) -> None:
    state.game_over = True
    state.game_over_summary = game_over_summmary(state)

def update_chat_history(state: State, user_message: str, gamemaster_reply: str | None) -> None:
    state.chat_history.append({"role": "user", "content": user_message})
    if gamemaster_reply is not None:
        state.chat_history.append({"role": "assistant", "content": gamemaster_reply})

async def async_get_gamemaster_reply(state: State, user_message: str) -> str:
    state.chat_history.append({"role": "user", "content": user_message}) # Temporarily append.
    
    response = await async_client.chat.completions.create(
        model="gpt-4.1",
        messages=state.chat_history
    )
    
    reply: str = empty_str_if_none(response.choices[0].message.content)
    
    state.chat_history.pop() # Pop to keep state unaffected by function call.
    return reply

async def async_is_relevant(state: State, user_message: str) -> bool:
    sys, user  = prompts.relevant(state, user_message)
    reply: str = await async_response_with_sys_user(sys, user)
    
    match reply.strip().lower():
        case 'true' | "'true'" | '"true"':
            return True
        case _:
            return False

async def async_is_realistic(state: State, user_message: str) -> bool:
    sys, user  = prompts.realistic(state, user_message)
    reply: str = await async_response_with_sys_user(sys, user)
    
    match reply.strip().lower():
        case 'true' | "'true'" | '"true"':
            return True
        case _:
            return False

def assess_damage(state: State, user_message: str, gamemaster_reply: str) -> int:
    sys, user = prompts.damaging(state, user_message, gamemaster_reply)
    reply: str = response_with_sys_user(sys, user)
    
    remove_quotes: Callable[[str], str] = lambda s: s.replace('"', '').replace("'", '')
    damage: str = remove_quotes(reply).lower().strip()

    match damage:
        case "5" | "4" | "3" | "2" | "1":
            return int(damage)
        case _:
            return 0

def game_over_summmary(state: State) -> str:
    sys, user = prompts.game_over_summmary(state)
    return response_with_sys_user(sys, user)    

@app.get('/api/get_suggested_responses')
async def get_suggested_responses(gameId: str, n: int = 3) -> dict[str, Any]:
    """Generate N suggested player responses based on the most recent AI response."""
    state = load_state_from_db(gameId)
    if state is None:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": "Invalid game ID.",
            }
        )
    
    gamemaster_reply: str | None = state.chat_history[-1].get("content", None)
    
    if gamemaster_reply is None or len(gamemaster_reply) == 0:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": "No gamemaster response found. Please send a message first.",
            }
        )
    
    # Generate N suggested responses in parallel with randomness
    sys_prompt, user_prompt = prompts.suggested_response(state, gamemaster_reply)
    
    async def generate_suggestion() -> str:
        # Vary temperature slightly (0.7-0.9) for each request to ensure diversity
        temperature = random.uniform(0.7, 0.9)
        return await async_response_with_sys_user_temperature(sys_prompt, user_prompt, temperature=temperature)
    
    tasks = [generate_suggestion() for _ in range(n)]
    suggestions: list[str] = await asyncio.gather(*tasks)
    
    return {
        "suggestions": suggestions
    }

@app.get('/api/existing_games')
def existing_games() -> dict[str, Any]:
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

    return { "results": results }

@app.post('/api/delete_game')
def delete_game(data: DeleteGameRequest) -> dict[str, Any]:
    _id_string: str | None = data.objectIDString
    if _id_string is None:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": "Can not delete a game without a valid ObjectIdString!",
            }
        )

    _id: ObjectId = ObjectId(_id_string)
    db.delete_game(_id)
    return {
            "sender": str(Sender.SYSTEM),
            "content": "Game successfully deleted.",
        }


@app.post('/api/load_game')
def load_game(data: LoadGameRequest) -> dict[str, Any]:
    _id_string: str | None = data.objectIDString
    if _id_string is None:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": "Can not load a game without a valid ObjectIdString!",
            }
        )

    state = load_state_from_db(_id_string)
    if state is None:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": f"Provided save ID {_id_string} is not valid."
            }
        )
    
    assert(state._id is not None)
    portrait_bytes, backdrop_bytes = db.get_image_bytes(state._id)
    return {
            "sender": str(Sender.SYSTEM),
            "content": "Game state successfully loaded.",
            "portraitSrc": Image.json_content_from_bytes(portrait_bytes),
            "worldBackdropSrc": Image.json_content_from_bytes(backdrop_bytes),
            "hitPoints": state.hit_points,
            "gameId": str(state._id),
        }

@app.post('/api/initialize')
def initialize(data: InitializeRequest) -> dict[str, Any]:
    state = State()

    make_snake_case: Callable[[str], str] = lambda s: re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
    setattr(state, make_snake_case("playerName"), data.playerName)
    setattr(state, make_snake_case("playerDescription"), data.playerDescription)
    setattr(state, make_snake_case("worldTheme"), data.worldTheme)

    setup_initialization_prompt(state)
    images: Images = asyncio.run(get_new_images_for(state))

    db.save_game_and_images(state, images)
    assert(state._id is not None)
    return {
        "sender": str(Sender.SYSTEM),
        "systemPrompt": state.initialization_prompt,
        "portraitSrc": images.portrait.json_content(),
        "worldBackdropSrc": images.backdrop.json_content(),
        "hitPoints": MAX_HIT_POINTS,
        "gameId": str(state._id),
    }

async def validate_and_get_gamemaster_reply(state: State, user_message: str) -> str | JSONResponse:
    relevant_task = asyncio.create_task(async_is_relevant(state, user_message))
    realistic_task = asyncio.create_task(async_is_realistic(state, user_message))
    
    relevant, realistic = await asyncio.gather(
        relevant_task,
        realistic_task
    )
    
    if not relevant or not realistic:
        
        content: str = ""
        if not relevant and not realistic:
            content = "Your message is not relevant or realistic."
        elif not relevant:
            content = "Your message is not relevant to the game story."
        else:
            content = "Your message does not respect the realism of the game story."

        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": content,
            }
        )
    
    return await async_get_gamemaster_reply(state, user_message)

@app.post('/api/response')
async def response(data: ResponseRequest) -> dict[str, Any]:
    if data.gameId is None:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": "Game ID is required. Please initialize or load a game first.",
            }
        )
    
    state = load_state_from_db(data.gameId)
    if state is None:
        return JSONResponse(
            status_code=400,
            content={
                "sender": str(Sender.ERROR),
                "content": "Invalid game ID. Please initialize or load a game first.",
            }
        )
    
    if state.game_over:
        return {
                "sender": str(Sender.SYSTEM),
                "content": "You are dead. Please refresh the browser to play again.",
            }

    user_message = data.content
    override: bool = False
    if user_message.startswith("@override"):
        override = True
        user_message: str = user_message.removeprefix("@override")

    if override:
        reply: str = await async_get_gamemaster_reply(state, user_message)
    else:
        result = await validate_and_get_gamemaster_reply(state, user_message)
        if isinstance(result, JSONResponse):
            return result
        reply: str = result

    if len(reply) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "sender": str(Sender.ERROR),
                "content": "Gamemaster failed to generate a response.",
            }
        )

    dmg: int = assess_damage(state, user_message, reply)
    state.hit_points -= dmg

    if state.hit_points <= 0:
        game_over(state)
        update_chat_history(state, user_message, None)
        db.save_game(state)
        return {
                "sender": str(Sender.SYSTEM),
                "content": "Oh, no! Unfortunately, you have died!",
                "gameOverSummary": state.game_over_summary,
                "hitPoints": state.hit_points,
            }
    else:
        update_chat_history(state, user_message, reply)
        db.save_game(state)
        return {
                "sender": str(Sender.GAMEMASTER),
                "content": reply,
                "hitPoints": state.hit_points,
            }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
