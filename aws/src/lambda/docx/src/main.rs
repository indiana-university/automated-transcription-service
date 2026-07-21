use std::sync::Arc;

use lambda_runtime::{Error, service_fn};
use tracing_subscriber::EnvFilter;
use transcribe_to_docx::app::{AppState, Config, handler};

#[tokio::main]
async fn main() -> Result<(), Error> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .without_time()
        .init();

    let config = Config::from_env()?;
    let sdk_config = aws_config::load_defaults(aws_config::BehaviorVersion::latest()).await;
    let state = Arc::new(AppState {
        config,
        s3: aws_sdk_s3::Client::new(&sdk_config),
        transcribe: aws_sdk_transcribe::Client::new(&sdk_config),
        http: reqwest::Client::new(),
    });

    lambda_runtime::run(service_fn(move |event| handler(event, Arc::clone(&state)))).await
}
