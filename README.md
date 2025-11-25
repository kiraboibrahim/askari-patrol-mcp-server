# Askari Patrol MCP Server

Small utility and MCP server wrapper for interacting with the Askari Patrol / GuardTour API.
Contains a lightweight HTTP client and an MCP (Model Context Processor) server scaffold to expose tooling.

## Features

- HTTP client utilities for the Askari Patrol API
- Minimal MCP server scaffold to expose tools and workflows
- Unit tests and basic developer tooling

## Installation

```bash
# Install dependencies
make install
```

## Usage

```bash
# Run MCP Server
make server

# Run WhatsApp Client
make whatsapp
```

## Development

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Automatically fix lint issues
make fix
```

## Running the Command Line Chat Client

```bash

# Open first terminal(tab)
make server

# Open second terminal(tab)
make chat
```

## Running WhatsApp Client

```bash
# Create a .env file from the .env.example
cp .env.example .env

# Populate with variables
```
### Running Server and Client

1. Open terminal and enter the following command

```bash
make server
```
2. Open a second terminal/tab and enter the following command

```bash
make whatsapp
```
3. You will need to expose the whatsapp client to the web

```bash
ngrok http 8001
```
4. Configure webhook using the given ngrok tunnel url i.e If ngrok has provided `hemicranic-moneyerately-herta.ngrok-free.dev` then the webhook url should be: `https://hemicranic-moneyerately-herta.ngrok-free.dev/webhook`

5. Head over to twilio and set the webhook url

6. Send your first message to the bot!!!!


## Challenges
* WhatsApp formatting is limited i.e Tabular data can't be properly displayed in WhatsApp
* There is a 1600 character limit on for WhatsApp body, meaning large responses will fail
* Rate Limit Exceeded: We tend to hit so may rate lmits most especially the TPM(Tokens Per Minute) due to the voliminous responses
* Instant Responses when clients send messages(Responses are generated on the fly when a request from a client comes in). I believe, we need a task queue to handle client messages
