"""Constants for Spyster integration."""

# Integration domain
DOMAIN = "spyster"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"

# WebSocket configuration (ARCH-15)
WS_HEARTBEAT_TIMEOUT = 30  # seconds - aiohttp keepalive

# Error codes foundation (expand in future stories)
ERR_INVALID_MESSAGE = "INVALID_MESSAGE"
ERR_MESSAGE_PARSE_FAILED = "MESSAGE_PARSE_FAILED"
ERR_INTERNAL = "INTERNAL"
ERR_INVALID_PHASE = "INVALID_PHASE"
ERR_SESSION_EXISTS = "SESSION_EXISTS"
ERR_NOT_HOST = "NOT_HOST"
ERR_NOT_IN_GAME = "NOT_IN_GAME"
ERR_CANNOT_REMOVE_CONNECTED = "CANNOT_REMOVE_CONNECTED"
ERR_PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"

# Error codes for player join (Story 2.2)
ERR_NAME_INVALID = "NAME_INVALID"
ERR_NAME_TAKEN = "NAME_TAKEN"
ERR_GAME_FULL = "GAME_FULL"
ERR_GAME_ALREADY_STARTED = "GAME_ALREADY_STARTED"

# Error codes for game start (Story 3.2)
ERR_NOT_ENOUGH_PLAYERS = "NOT_ENOUGH_PLAYERS"
ERR_START_ABORTED = "START_ABORTED"

# Error codes for role assignment (Story 3.3)
ERR_ROLE_ASSIGNMENT_FAILED = "ROLE_ASSIGNMENT_FAILED"

# Error codes for session management (Story 2.3)
ERR_INVALID_TOKEN = "INVALID_TOKEN"
ERR_SESSION_EXPIRED = "SESSION_EXPIRED"

# Error codes for connection management
ERR_CONNECTION_LIMIT = "CONNECTION_LIMIT"

# Error codes for configuration (Story 3.1)
ERR_CONFIG_INVALID_DURATION = "CONFIG_INVALID_DURATION"
ERR_CONFIG_INVALID_ROUNDS = "CONFIG_INVALID_ROUNDS"
ERR_CONFIG_INVALID_PACK = "CONFIG_INVALID_PACK"
ERR_CONFIG_GAME_STARTED = "CONFIG_GAME_STARTED"

# Error codes for call vote (Story 4.5)
ERR_NOT_CONNECTED = "ERR_NOT_CONNECTED"

# Error codes for voting (Story 5.3)
ERR_ALREADY_VOTED = "ALREADY_VOTED"
ERR_INVALID_TARGET = "INVALID_TARGET"
ERR_NO_TARGET_SELECTED = "NO_TARGET_SELECTED"

# Error codes for spy guess (Story 5.4)
ERR_NOT_SPY = "NOT_SPY"
ERR_SPY_ALREADY_ACTED = "SPY_ALREADY_ACTED"
ERR_INVALID_LOCATION = "INVALID_LOCATION"

# Error codes for phase transitions and timers (Story 4.1)
ERR_INVALID_PHASE_TRANSITION = "INVALID_PHASE_TRANSITION"
ERR_TIMER_ALREADY_RUNNING = "TIMER_ALREADY_RUNNING"
ERR_NO_ROUND_DURATION = "NO_ROUND_DURATION"

# Error codes for turn management (Story 4.3)
ERR_INSUFFICIENT_PLAYERS = "INSUFFICIENT_PLAYERS"
ERR_TURN_NOT_INITIALIZED = "TURN_NOT_INITIALIZED"

# Error codes for game progression (Story 6.6)
ERR_GAME_ENDED = "GAME_ENDED"

# Error messages for user display
ERROR_MESSAGES = {
    ERR_INVALID_MESSAGE: "Message must be JSON with a 'type' field.",
    ERR_MESSAGE_PARSE_FAILED: "Could not parse message as JSON.",
    ERR_INTERNAL: "Something went wrong. Please try again.",
    ERR_INVALID_PHASE: "You can't do that right now.",
    ERR_SESSION_EXISTS: "A game session already exists.",
    ERR_NOT_HOST: "Only the host can perform this action.",
    ERR_NOT_IN_GAME: "You are not in the game.",
    ERR_CANNOT_REMOVE_CONNECTED: "Cannot remove a connected player. Wait for them to disconnect first.",
    ERR_PLAYER_NOT_FOUND: "Player not found in the game.",
    ERR_NAME_INVALID: "Please enter a name between 1-20 characters.",
    ERR_NAME_TAKEN: "That name is already taken. Please choose another.",
    ERR_GAME_FULL: "Sorry, this game is full (max 10 players).",
    ERR_GAME_ALREADY_STARTED: "This game has already started.",
    ERR_INVALID_TOKEN: "Invalid session. Please join again.",
    ERR_SESSION_EXPIRED: "Your session has expired. Please join again.",
    ERR_CONNECTION_LIMIT: "Server is at capacity. Please try again later.",
    ERR_NOT_ENOUGH_PLAYERS: "Need at least 4 players to start the game.",
    ERR_START_ABORTED: "Game start aborted - not enough players.",
    ERR_ROLE_ASSIGNMENT_FAILED: "Failed to assign roles. Please try again.",
    ERR_CONFIG_INVALID_DURATION: "Round duration must be between 1-30 minutes.",
    ERR_CONFIG_INVALID_ROUNDS: "Number of rounds must be between 1-20.",
    ERR_CONFIG_INVALID_PACK: "Selected location pack not found.",
    ERR_CONFIG_GAME_STARTED: "Cannot change configuration after game has started.",
    ERR_NOT_CONNECTED: "You are not connected to the game.",
    ERR_INVALID_PHASE_TRANSITION: "Cannot transition from current phase.",
    ERR_TIMER_ALREADY_RUNNING: "Timer is already running.",
    ERR_NO_ROUND_DURATION: "Round duration not configured.",
    ERR_INSUFFICIENT_PLAYERS: "Not enough players to continue.",
    ERR_TURN_NOT_INITIALIZED: "Turn order has not been initialized.",
    ERR_GAME_ENDED: "Game has already ended.",
    ERR_ALREADY_VOTED: "You've already submitted your vote.",
    ERR_INVALID_TARGET: "Invalid vote target.",
    ERR_NO_TARGET_SELECTED: "Please select a player to vote for.",
    ERR_NOT_SPY: "Only the spy can guess the location.",
    ERR_SPY_ALREADY_ACTED: "You've already made your choice.",
    ERR_INVALID_LOCATION: "Invalid location selection.",
}

# Game configuration defaults
DEFAULT_ROUND_DURATION = 420  # 7 minutes in seconds
DEFAULT_ROUND_COUNT = 5
DEFAULT_VOTE_DURATION = 60  # 60 seconds

# Timer durations (seconds) - ARCH-10
TIMER_DURATION_ROLE_DISPLAY = 5  # Display roles before questioning (Story 4.1)
TIMER_DURATION_ROUND_DEFAULT = 300  # Default 5 minutes for questioning, configurable (Story 4.1)
TIMER_DURATION_VOTE = 60  # 60 seconds for voting (Story 4.1, FR30)
TIMER_DURATION_REVEAL_DELAY = 3  # Delay before reveal sequence (Story 4.1)
VOTE_TIMER_DURATION = 60  # FR30, ARCH-10 (kept for backward compatibility)
SCORING_DISPLAY_SECONDS = 10  # Time to view leaderboard before next round (Story 6.5)

# Configuration Limits (Story 3.1)
CONFIG_MIN_ROUND_DURATION = 1      # minutes
CONFIG_MAX_ROUND_DURATION = 30     # minutes
CONFIG_DEFAULT_ROUND_DURATION = 7  # minutes

CONFIG_MIN_ROUNDS = 1
CONFIG_MAX_ROUNDS = 20
CONFIG_DEFAULT_ROUNDS = 5

CONFIG_DEFAULT_LOCATION_PACK = "classic"

# Timer type identifiers (string names for timer management)
TIMER_TYPE_ROUND = "round"
TIMER_TYPE_VOTE = "vote"
TIMER_TYPE_ROLE_DISPLAY = "role_display"
TIMER_TYPE_REVEAL_DELAY = "reveal_delay"

# Disconnect handling (Story 2.4)
DISCONNECT_GRACE_SECONDS = 30  # seconds - NFR11 requirement
HEARTBEAT_INTERVAL = 10  # seconds - client sends heartbeat every 10s
RECONNECT_WINDOW_SECONDS = 300  # 5 minutes in seconds - NFR12 (Story 2.3)
MIN_DISCONNECT_DURATION_FOR_REMOVAL = 60  # seconds - minimum time disconnected before host can remove player (Story 2.6)

# WebSocket connection pool limits (ARCH-12)
MAX_CONNECTIONS = 50  # Maximum concurrent WebSocket connections
DISCONNECT_GRACE_TIMEOUT = DISCONNECT_GRACE_SECONDS  # Alias for test compatibility

# Player constraints
MIN_PLAYERS = 4
MAX_PLAYERS = 10
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 20

# QR code configuration
DEFAULT_QR_SIZE = 300  # pixels for mobile
DEFAULT_QR_BOX_SIZE = 10  # QR code box size
DEFAULT_QR_BORDER = 4  # QR code border size

# Phase transition validation map (using string literals to avoid circular import)
# GameState.can_transition() will convert these to GamePhase enum values
VALID_TRANSITIONS = {
    "LOBBY": ["ROLES", "PAUSED"],
    "ROLES": ["QUESTIONING", "PAUSED"],
    "QUESTIONING": ["VOTE", "PAUSED"],
    "VOTE": ["REVEAL", "PAUSED"],
    "REVEAL": ["SCORING", "PAUSED"],
    "SCORING": ["ROLES", "END", "PAUSED"],
    "END": ["LOBBY", "PAUSED"],
    "PAUSED": ["LOBBY", "ROLES", "QUESTIONING", "VOTE", "REVEAL", "SCORING"],
}
