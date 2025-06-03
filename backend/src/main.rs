use axum::{
    routing::{get, post},
    extract::{State, Json},
    Router,
};

use serde::{Deserialize, Serialize};
use tower_http::cors::{CorsLayer, Any};

use std::{
    net::SocketAddr,
    sync::{Arc, Mutex},
    env,
};

use dotenv::dotenv;

use openai_api_rs::v1::{
    api::OpenAIClient,
    chat_completion::{self, ChatCompletionRequest},
    common::GPT4_O,
};

#[derive(Serialize, Deserialize)]
struct Message {
    content: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Config {
    player_name: String,
    world_theme: String,
    player_description: String,
    world_description: String,
}

#[derive(Clone)]
struct AppState {
    config: Arc<Mutex<Config>>
}

// === Start: Basic test functions ===
async fn echo(Json(message): Json<Message>) -> Json<Message> {
    Json(Message {
        content: format!("Server received: {}", message.content),
    })
}

async fn greet() -> Json<Message> {
    Json(Message {
        content: "Hello, tester!".to_string()
    })
}
// === End ===

#[tokio::main]
async fn main() {
    let app_state = AppState {
        config: Arc::new(Mutex::new(Config {
            player_name: String::from(""),
            world_theme: String::from(""),
            player_description: String::from(""),
            world_description: String::from(""),
        })),
    };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any)
        .expose_headers(Any);

    let app = Router::new()
        .route("/test/greet", get(greet))
        .route("/test/echo", post(echo))
        .route("/api/response", post(response))
        .route("/api/initialize", post(initialize))
        .with_state(app_state)
        .layer(cors);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Listening on http://{}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn initialize(
    State(state): State<AppState>,
    Json(new_config): Json<Config>,
) -> Json<Message> {
    let mut config = state.config.lock().unwrap();
    *config = new_config;

    Json(Message {
        content: String::from("Config successfully updated!")
    })
}

async fn response(
    State(state): State<AppState>,
    Json(message): Json<Message>
) -> Json<Message> {
    dotenv().ok();
    
    let api_key = env::var("OPENAI_API_KEY").unwrap();
    
    let mut client = OpenAIClient::builder().with_api_key(api_key).build().unwrap();

    let config = state.config.lock().unwrap();
    let name = &config.player_name;

    // Temporary holding: "You are an adventure gamemaster. Please respond to requests with descriptive but (generally) short responses. Always end your response with the question 'What do you choose to do?' Do not answer questions that are irrelevant to the established game world. If the user asks a question about the real world, inform the user that you can not respond to the request."
    let req = ChatCompletionRequest::new(
        GPT4_O.to_string(),
        vec![
            chat_completion::ChatCompletionMessage {
                role: chat_completion::MessageRole::system,
                content: chat_completion::Content::Text(
                    String::from(format!("Greet them by their name {}", name))
                ),
                name: None,
                tool_calls: None,
                tool_call_id: None,
            },
            chat_completion::ChatCompletionMessage {
                role: chat_completion::MessageRole::user,
                content: chat_completion::Content::Text(String::from(message.content)),
                name: None,
                tool_calls: None,
                tool_call_id: None,
            }
        ],
    );

    let result = client.chat_completion(req).await.unwrap();
    let response_content = match &result.choices[0].message.content {
        Some(content) => content.to_string(),
        None => "No content returned.".to_string(),
    };
    
    Json(Message {
        content: response_content
    })
}
