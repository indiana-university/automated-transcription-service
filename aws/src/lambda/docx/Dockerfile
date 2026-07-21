ARG RUST_VERSION=1.97.1

FROM rust:${RUST_VERSION}-trixie AS build

WORKDIR /build

COPY Cargo.toml Cargo.lock ./
COPY src ./src

RUN cargo build --locked --release

FROM gcr.io/distroless/cc-debian13:nonroot

WORKDIR /function

COPY --from=build --chown=nonroot:nonroot /build/target/release/transcribe-to-docx /function/transcribe-to-docx

USER nonroot

ENTRYPOINT ["/function/transcribe-to-docx"]
