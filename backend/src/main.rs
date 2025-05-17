use axum::{
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;

#[derive(Serialize, Deserialize)]
struct Message {
    content: String,
}

#[tokio::main]
async fn main() {
    // Build our application with a route
    let app = Router::new()
        .route("/", get(root))
        .route("/api/echo", post(echo));

    // Run the app
    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Listening on http://{}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

// Simple GET route to test server
async fn root() -> &'static str {
    "Hello from the Rust server!"
}

// Simple POST route to echo back a message
async fn echo(Json(message): Json<Message>) -> Json<Message> {
    Json(Message {
        content: format!("Server received: {}", message.content),
    })
}

