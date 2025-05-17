use axum::{
    routing::{get, post},
    Json, Router,
};

use serde::{Deserialize, Serialize};
use tower_http::cors::{CorsLayer, Any};

use std::net::SocketAddr;
use std::env;
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

#[tokio::main]
async fn main() {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any)
        .expose_headers(Any);

    let app = Router::new()
        .route("/", get(root))
        .route("/api/echo", post(echo))
        .route("/api/response", post(response))
        .layer(cors);

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Listening on http://{}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn root() -> &'static str {
    "Hello from the Rust server!"
}

async fn echo(Json(message): Json<Message>) -> Json<Message> {
    Json(Message {
        content: format!("Server received: {}", message.content),
    })
}

async fn response(Json(message): Json<Message>) -> Json<Message> {
    dotenv().ok();
    // Get API key from environment
    let api_key = env::var("OPENAI_API_KEY").unwrap();
    
    // Build the OpenAI client
    let mut client = OpenAIClient::builder().with_api_key(api_key).build().unwrap();

    // Create the request
    let req = ChatCompletionRequest::new(
        GPT4_O.to_string(),
        vec![chat_completion::ChatCompletionMessage {
            role: chat_completion::MessageRole::user,
            content: chat_completion::Content::Text(String::from(message.content)),
            name: None,
            tool_calls: None,
            tool_call_id: None,
        }],
    );

    // Send the request and await the response
    let result = client.chat_completion(req).await.unwrap();

    let response_content = match &result.choices[0].message.content {
        Some(content) => content.to_string(),
        None => "No content returned".to_string(),
    };
    
    // Return the response as Json
    Json(Message {
        content: response_content
    })
}
