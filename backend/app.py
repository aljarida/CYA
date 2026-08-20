import asyncio
import os
import random
import re
from typing import Any, TypeVar

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAIError
from pydantic import BaseModel

import prompts
from classes import MAX_HIT_POINTS, InventoryItem, PlayerAttributes, Sender, State
from context import ContextBuilder
from database import GameRepository, RevisionConflictError, create_game_repository
from game_service import GameService
from images import Image, Images
from llm import LLMClient, OpenAILLMClient
from llm_results import BooleanDecision, DamageDecision
from utils import bool_of_str

StructuredResult = TypeVar("StructuredResult")

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

class DraftInventoryItemDTO(BaseModel):
    name: str
    description: str = ""
    weightKg: float = 0.0
    quantity: int = 1

class DraftAttributesDTO(BaseModel):
    ageYears: int
    heightCm: float
    bodyWeightKg: float
    maxCarryWeightKg: float

class GenerateStartingStateRequest(BaseModel):
    playerName: str
    playerDescription: str
    worldTheme: str

class InitializeRequest(BaseModel):
    playerName: str
    playerDescription: str
    worldTheme: str
    startingLocation: str | None = None
    startingInventory: list[DraftInventoryItemDTO] | None = None
    startingConditions: list[str] | None = None
    attributes: DraftAttributesDTO | None = None

class ResponseRequest(BaseModel):
    content: str
    gameId: str | None = None

class DiscardItemRequest(BaseModel):
    gameId: str | None = None
    itemId: str | None = None

load_dotenv()
llm_client: LLMClient = OpenAILLMClient(api_key=os.environ["OPENAI_API_KEY"])

db: GameRepository = create_game_repository()

MAX_SUGGESTED_RESPONSES: int = 5
MAX_MESSAGE_LENGTH: int = 2000
MAX_SETUP_FIELD_LENGTH: int = 500

def error_response(status_code: int, content: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "sender": str(Sender.ERROR),
            "content": content,
        },
    )

def conflict_response() -> JSONResponse:
    return error_response(409, "Game state was modified by another request. Please reload and try again.")

def create_game_service() -> GameService:
    return GameService(db, llm_client)

def startup_failure_response(stage: str, exc: Exception) -> JSONResponse:
    detail = str(exc) or type(exc).__name__
    return error_response(502, f"Game initialization failed during {stage}: {detail}")

def is_valid_id(value: str | None) -> bool:
    return value is not None and len(value.strip()) > 0

def validate_text_length(value: str, label: str, max_length: int) -> JSONResponse | None:
    if len(value) > max_length:
        return error_response(400, f"{label} must be {max_length} characters or fewer.")
    return None

def load_state_from_db(game_id: str) -> State | None:
    """Load a State object from the database by game ID."""
    return db.get_game(game_id)

def empty_str_if_none(reply: str | None) -> str:
    return reply if reply is not None else ""

async def get_new_images_for(s: State) -> Images:
    """Obtain portrait and backdrop images given that a provided State object with a valid _id."""
    if s._id is not None:
        raise ValueError("Cannot create images for a state that already has a game ID.")

    db.save_game(s)
    if s._id is None:
        raise RuntimeError("Unable to save game before generating images.")

    if bool_of_str(os.environ["SKIP_IMAGE_GENERATION"]):
        return Images(
            s._id,
            Image.debug_portrait_bytes(),
            Image.debug_backdrop_bytes(),
        )

    portrait_bytes, backdrop_bytes = await asyncio.gather(
        llm_client.generate_image_bytes(prompts.portrait(s), "1024x1024"),
        llm_client.generate_image_bytes(prompts.backdrop(s), "1536x1024"),
    )

    return Images(s._id, portrait_bytes, backdrop_bytes)

def response_with_sys_user(sys_content: str, user_content: str) -> str:
    return llm_client.text(sys_content, user_content)

def structured_response_with_sys_user(
    sys_content: str,
    user_content: str,
    response_model: type[StructuredResult],
) -> StructuredResult:
    return llm_client.structured(sys_content, user_content, response_model)

async def async_response_with_sys_user(sys_content: str, user_content: str) -> str:
    return await llm_client.async_text(sys_content, user_content)

async def async_structured_response_with_sys_user(
    sys_content: str,
    user_content: str,
    response_model: type[StructuredResult],
) -> StructuredResult:
    return await llm_client.async_structured(sys_content, user_content, response_model)

async def async_response_with_sys_user_temperature(sys_content: str, user_content: str, temperature: float = 0.7) -> str:
    """Generate a response with configurable temperature for randomness."""
    return await llm_client.async_text(sys_content, user_content, temperature=temperature)

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

def narration_messages(state: State, user_message: str) -> list[Any]:
    return ContextBuilder().narration_messages(state, user_message)

async def async_get_gamemaster_reply(state: State, user_message: str) -> str:
    return await llm_client.async_messages(narration_messages(state, user_message))

async def async_is_relevant(state: State, user_message: str) -> bool:
    sys, user  = prompts.relevant(state, user_message)
    decision = await async_structured_response_with_sys_user(sys, user, BooleanDecision)
    return decision.value

async def async_is_realistic(state: State, user_message: str) -> bool:
    sys, user  = prompts.realistic(state, user_message)
    decision = await async_structured_response_with_sys_user(sys, user, BooleanDecision)
    return decision.value

def assess_damage(state: State, user_message: str, gamemaster_reply: str) -> int:
    sys, user = prompts.damaging(state, user_message, gamemaster_reply)
    decision = structured_response_with_sys_user(sys, user, DamageDecision)
    return decision.damage

def game_over_summmary(state: State) -> str:
    sys, user = prompts.game_over_summmary(state)
    return response_with_sys_user(sys, user)    

@app.get('/api/get_suggested_responses')
async def get_suggested_responses(gameId: str, n: int = 3) -> dict[str, Any]:
    """Generate N suggested player responses based on the most recent AI response."""
    if not is_valid_id(gameId):
        return error_response(400, "Invalid game ID.")

    if not 1 <= n <= MAX_SUGGESTED_RESPONSES:
        return error_response(400, f"Suggestion count must be between 1 and {MAX_SUGGESTED_RESPONSES}.")

    state = load_state_from_db(gameId)
    if state is None:
        return error_response(400, "Invalid game ID.")
    
    gamemaster_reply: str | None = None
    if len(state.chat_history) > 0:
        gamemaster_reply = state.chat_history[-1].get("content", None)
    
    if gamemaster_reply is None or len(gamemaster_reply) == 0:
        return error_response(400, "No gamemaster response found. Please send a message first.")
    
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
    if not is_valid_id(_id_string):
        return error_response(400, "Can not delete a game without a valid game ID.")

    if not db.delete_game(_id_string):
        return error_response(400, f"Provided save ID {_id_string} is not valid.")
    return {
            "sender": str(Sender.SYSTEM),
            "content": "Game successfully deleted.",
        }


@app.post('/api/load_game')
def load_game(data: LoadGameRequest) -> dict[str, Any]:
    _id_string: str | None = data.objectIDString
    if not is_valid_id(_id_string):
        return error_response(400, "Can not load a game without a valid game ID.")

    state = load_state_from_db(_id_string)
    if state is None:
        return error_response(400, f"Provided save ID {_id_string} is not valid.")
    
    if state._id is None:
        return error_response(500, "Loaded game state is missing a game ID.")

    image_bytes = db.get_image_bytes(state._id)
    if image_bytes is None:
        return error_response(404, "Images for the provided save could not be found.")
    portrait_bytes, backdrop_bytes = image_bytes
    return {
            "sender": str(Sender.SYSTEM),
            "content": "Game state successfully loaded.",
            "portraitSrc": Image.json_content_from_bytes(portrait_bytes),
            "worldBackdropSrc": Image.json_content_from_bytes(backdrop_bytes),
            "hitPoints": state.hit_points,
            "gameId": str(state._id),
            "worldState": state.world_state.to_api_dict(),
            "playerAttributes": state.player_attributes.to_api_dict(),
            "storySummary": state.story_summary,
            "unresolvedThreads": list(state.unresolved_threads),
        }

@app.post('/api/generate_starting_state')
async def generate_starting_state(data: GenerateStartingStateRequest) -> dict[str, Any]:
    for label, value in (
        ("Player name", data.playerName),
        ("Player description", data.playerDescription),
        ("World theme", data.worldTheme),
    ):
        validation_error = validate_text_length(value, label, MAX_SETUP_FIELD_LENGTH)
        if validation_error is not None:
            return validation_error

    try:
        result = await create_game_service().generate_starting_state(
            data.playerName, data.worldTheme, data.playerDescription
        )
    except (AuthenticationError, APIConnectionError, APIStatusError, OpenAIError) as exc:
        return startup_failure_response("OpenAI character generation", exc)

    return {
        "startingLocation": result.starting_location,
        "startingInventory": [
            {
                "name": item.name,
                "description": item.description,
                "weightKg": item.weight_kg,
                "quantity": item.quantity,
            }
            for item in result.starting_inventory
        ],
        "startingConditions": list(result.starting_conditions),
        "attributes": {
            "ageYears": result.age_years,
            "heightCm": result.height_cm,
            "bodyWeightKg": result.body_weight_kg,
            "maxCarryWeightKg": result.max_carry_weight_kg,
        },
    }

@app.post('/api/initialize')
async def initialize(data: InitializeRequest) -> dict[str, Any]:
    for label, value in (
        ("Player name", data.playerName),
        ("Player description", data.playerDescription),
        ("World theme", data.worldTheme),
    ):
        validation_error = validate_text_length(value, label, MAX_SETUP_FIELD_LENGTH)
        if validation_error is not None:
            return validation_error

    state = State()

    def make_snake_case(value: str) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', value).lower()
    setattr(state, make_snake_case("playerName"), data.playerName)
    setattr(state, make_snake_case("playerDescription"), data.playerDescription)
    setattr(state, make_snake_case("worldTheme"), data.worldTheme)

    if data.startingLocation is not None:
        state.world_state.current_location = data.startingLocation
    if data.startingInventory is not None:
        state.world_state.inventory = [
            InventoryItem(
                name=item.name,
                description=item.description,
                weight_kg=item.weightKg,
                quantity=item.quantity,
            )
            for item in data.startingInventory
        ]
    if data.startingConditions is not None:
        state.world_state.conditions = list(data.startingConditions)
    if data.attributes is not None:
        state.player_attributes = PlayerAttributes(
            age_years=data.attributes.ageYears,
            height_cm=data.attributes.heightCm,
            body_weight_kg=data.attributes.bodyWeightKg,
            max_carry_weight_kg=data.attributes.maxCarryWeightKg,
        )

    setup_initialization_prompt(state)
    try:
        images: Images = await get_new_images_for(state)
    except (AuthenticationError, APIConnectionError, APIStatusError, OpenAIError) as exc:
        return startup_failure_response("OpenAI image generation", exc)
    except httpx.HTTPError as exc:
        return startup_failure_response("image download", exc)
    except (RuntimeError, ValueError) as exc:
        return startup_failure_response("local storage", exc)
    except Exception as exc:
        return startup_failure_response("startup", exc)

    try:
        db.save_game_and_images(state, images)
    except RevisionConflictError:
        return conflict_response()
    except Exception as exc:
        return startup_failure_response("local storage", exc)
    if state._id is None:
        return error_response(500, "Initialized game state is missing a game ID.")

    return {
        "sender": str(Sender.SYSTEM),
        "systemPrompt": state.initialization_prompt,
        "portraitSrc": images.portrait.json_content(),
        "worldBackdropSrc": images.backdrop.json_content(),
        "hitPoints": MAX_HIT_POINTS,
        "gameId": str(state._id),
        "worldState": state.world_state.to_api_dict(),
        "playerAttributes": state.player_attributes.to_api_dict(),
        "storySummary": state.story_summary,
        "unresolvedThreads": list(state.unresolved_threads),
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
    if not is_valid_id(data.gameId):
        return error_response(400, "Game ID is required. Please initialize or load a game first.")

    validation_error = validate_text_length(data.content, "Message", MAX_MESSAGE_LENGTH)
    if validation_error is not None:
        return validation_error

    turn_result = await create_game_service().play_turn(data.gameId, data.content)
    if turn_result.status_code != 200:
        return error_response(turn_result.status_code, turn_result.content)
    return turn_result.to_response()

@app.post('/api/discard_item')
def discard_item(data: DiscardItemRequest) -> dict[str, Any]:
    turn_result = create_game_service().discard_item(data.gameId, data.itemId)
    if turn_result.status_code != 200:
        return error_response(turn_result.status_code, turn_result.content)
    return turn_result.to_response()

@app.get('/api/moments')
def moments(gameId: str) -> dict[str, Any]:
    if not is_valid_id(gameId):
        return error_response(400, "Game ID is required.")

    results = [
        {
            "id": moment.id,
            "caption": moment.caption,
            "imageSrc": Image.json_content_from_bytes(image_bytes),
        }
        for moment, image_bytes in db.list_moments(gameId)
    ]
    return {"results": results}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
