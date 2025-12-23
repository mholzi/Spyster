/**
 * Spyster Host Display JavaScript
 * Handles WebSocket connection and game state rendering for host/TV display
 */

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

let ws = null;
let reconnectTimeout = null;
let heartbeatTimer = null; // Story 2.4: Heartbeat timer
const HEARTBEAT_INTERVAL = 10000; // Story 2.4: 10 seconds (matches const.py)

// Story 3.2: Player count constants
const MIN_PLAYERS = 4;
const MAX_PLAYERS = 10;

/**
 * Initialize WebSocket connection to game server (Story 2.1 & 2.4)
 */
function initWebSocket() {
  console.log('[Host] Initializing WebSocket connection');

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/api/spyster/ws`;

  ws = new WebSocket(wsUrl);
  ws.onopen = handleWebSocketOpen;
  ws.onmessage = handleWebSocketMessage;
  ws.onerror = handleWebSocketError;
  ws.onclose = handleWebSocketClose;
}

/**
 * Handle WebSocket open event (Story 2.4)
 */
function handleWebSocketOpen() {
  console.log('[Host] WebSocket connected');
  clearTimeout(reconnectTimeout);
  startHeartbeat(); // Story 2.4: Start sending heartbeats
}

/**
 * Handle incoming WebSocket messages
 * @param {MessageEvent} event - WebSocket message event
 */
function handleWebSocketMessage(event) {
  console.log('[Host] WebSocket message received:', event.data);
  try {
    const message = JSON.parse(event.data);
    handleGameStateUpdate(message);
  } catch (error) {
    console.error('[Host] Failed to parse WebSocket message:', error);
  }
}

/**
 * Handle WebSocket error
 * @param {Event} event - WebSocket error event
 */
function handleWebSocketError(event) {
  console.error('[Host] WebSocket error:', event);
}

/**
 * Handle WebSocket close event (Story 2.4)
 * @param {CloseEvent} event - WebSocket close event
 */
function handleWebSocketClose(event) {
  console.log('[Host] WebSocket closed:', event.code, event.reason);
  stopHeartbeat(); // Story 2.4: Stop heartbeat on disconnect

  // Attempt reconnection after 3 seconds
  reconnectTimeout = setTimeout(() => {
    console.log('[Host] Attempting to reconnect...');
    initWebSocket();
  }, 3000);
}

// ============================================================================
// STATE RENDERING
// ============================================================================

/**
 * Handle game state updates from server
 * @param {Object} message - Game state message
 */
function handleGameStateUpdate(message) {
  console.log('[Host] Game state update:', message);

  // Story 3.2: Handle phase-specific rendering
  if (message.type === 'state') {
    const phase = message.phase;

    if (phase === 'LOBBY') {
      renderLobby(message);
    } else if (phase === 'ROLES') {
      renderRoles(message);
    } else if (phase === 'QUESTIONING') {
      renderQuestioning(message);
    }
    // TODO: Other phases in future stories
  }

  // FIX: Handle error messages from admin actions and config updates
  if (message.type === 'error') {
    console.error('[Host] Server error:', message.code, message.message);
    // Show error feedback with better UX
    showErrorBanner(message.message || 'An error occurred', message.code);
  }
}

/**
 * Show error banner with auto-dismiss (Story 3.1 error handling)
 * @param {string} message - Error message to display
 * @param {string} code - Error code (optional)
 */
function showErrorBanner(message, code) {
  // Create error banner if it doesn't exist
  let banner = document.getElementById('error-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'error-banner';
    banner.className = 'error-banner';
    banner.setAttribute('role', 'alert');
    banner.setAttribute('aria-live', 'assertive');
    document.body.appendChild(banner);
  }

  // Set message
  banner.textContent = message;
  banner.classList.add('show');

  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    banner.classList.remove('show');
  }, 5000);
}

/**
 * Render lobby state
 * @param {Object} state - Lobby state data
 */
function renderLobby(state) {
  console.log('[Host] Rendering lobby:', state);

  // Show lobby section
  showPhaseSection('lobby-section');

  // Load QR code
  loadQRCode();

  // Update player count
  const connectedCount = state.connected_count || 0;
  if (state.player_count !== undefined) {
    setText('current-player-count', connectedCount);
  }
  if (state.max_players !== undefined) {
    setText('max-player-count', state.max_players);
  }

  // Story 3.1: Render configuration
  if (state.config) {
    renderConfig(state.config);
  }

  // Story 2.4: Render player list with connection status
  if (state.players) {
    renderPlayerList(state.players);
  }

  // Story 3.2: Update START button state
  updateStartButton(state);

  // Update session info
  if (state.session_id) {
    setText('session-id-display', `Session: ${state.session_id.substring(0, 8)}`);
  }
  setText('phase-display', 'LOBBY');
}

/**
 * Update START button state based on game conditions (Story 3.2)
 * @param {Object} state - Game state
 */
function updateStartButton(state) {
  const startBtn = getElement('start-game-btn');
  const startMessage = getElement('start-message');

  if (!startBtn || !startMessage) return;

  const connectedCount = state.connected_count || 0;
  const canStart = state.can_start || false;

  // Update button state
  startBtn.disabled = !canStart;

  // Update status message
  if (connectedCount < MIN_PLAYERS) {
    startMessage.textContent = `Need at least ${MIN_PLAYERS} players`;
    startMessage.className = 'help-text warning';
    startBtn.classList.add('disabled');
  } else if (connectedCount >= MIN_PLAYERS && connectedCount <= MAX_PLAYERS) {
    startMessage.textContent = 'Ready to start!';
    startMessage.className = 'help-text success';
    startBtn.classList.remove('disabled');
  }
}

/**
 * Render roles loading state (Story 3.2)
 * @param {Object} state - Roles phase state
 */
function renderRoles(state) {
  console.log('[Host] Rendering roles phase:', state);

  // Show roles section
  showPhaseSection('roles-section');

  // Update phase display
  setText('phase-display', 'ROLES');
}

/**
 * Render player list with connection status indicators and Remove buttons (Story 2.4 & 2.6)
 * @param {Array} players - Array of player objects with name, connected, is_host, disconnect_duration
 */
function renderPlayerList(players) {
  const playerListEl = getElement('player-list');
  if (!playerListEl) {
    return;
  }

  if (!players || players.length === 0) {
    playerListEl.innerHTML = '<p class="empty-state">Waiting for players to join...</p>';
    return;
  }

  // Story 2.6: Minimum disconnect duration before removal allowed
  // CRITICAL: Must match MIN_DISCONNECT_DURATION_FOR_REMOVAL in const.py
  // TODO: Fetch this value from server config endpoint instead of hardcoding
  const MIN_DISCONNECT_FOR_REMOVAL = 60;  // seconds - synchronized with const.py

  playerListEl.innerHTML = players.map(player => {
    // FIXED: Use correct CSS class names for status indicators
    const statusClass = player.connected ? 'status-connected' : 'status-disconnected';
    const statusLabel = player.connected ? 'Connected' : 'Disconnected';
    const hostBadge = player.is_host ? '<span class="host-badge">HOST</span>' : '';

    // Show Remove button only if disconnected >= MIN_DISCONNECT_FOR_REMOVAL seconds (Story 2.6)
    let removeButton = '';
    if (!player.connected && player.disconnect_duration !== null) {
      // FIX: Validate disconnect_duration is a number and handle edge cases
      const duration = typeof player.disconnect_duration === 'number' && !isNaN(player.disconnect_duration)
        ? player.disconnect_duration
        : 0;

      if (duration >= MIN_DISCONNECT_FOR_REMOVAL) {
        // FIX: Escape player name in onclick attribute to prevent XSS
        const escapedName = player.name.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        removeButton = `
          <button
            class="btn-remove"
            onclick="removePlayer('${escapedName}')"
            aria-label="Remove ${player.name}"
          >
            Remove
          </button>
        `;
      } else {
        // Show countdown for when removal will be allowed
        const secondsRemaining = Math.ceil(MIN_DISCONNECT_FOR_REMOVAL - duration);
        removeButton = `
          <span class="disconnect-timer">
            Remove in ${secondsRemaining}s
          </span>
        `;
      }
    }

    // SECURITY FIX: Escape player name for HTML display to prevent XSS
    const escapeHtml = (unsafe) => {
      return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };

    return `
      <div class="player-card">
        <div class="status-indicator ${statusClass}" aria-label="${statusLabel}"></div>
        <div class="player-info">
          <span class="player-name">${escapeHtml(player.name)}</span>
          ${hostBadge}
        </div>
        ${removeButton}
      </div>
    `;
  }).join('');
}

/**
 * Remove a disconnected player from the lobby (Story 2.6)
 * @param {string} playerName - Name of player to remove
 */
function removePlayer(playerName) {
  // FIX: Sanitize player name for display to prevent dialog injection
  const sanitizedName = playerName.replace(/[<>'"&\n\r]/g, '');

  const confirmed = confirm(
    `Remove ${sanitizedName} from the lobby?\n\n` +
    `This player has been disconnected for 60+ seconds and will be permanently removed from this game session.`
  );
  if (!confirmed) return;

  // FIX: Add error handling and user feedback
  sendMessage({
    type: 'admin',
    action: 'remove_player',
    player_name: playerName
  });

  // Provide immediate feedback (optimistic UI)
  console.log(`[Host] Attempting to remove player: ${playerName}`);
  // Note: Actual removal confirmation will come via state broadcast
}

/**
 * Send WebSocket message to server
 * @param {Object} message - Message object to send
 */
function sendMessage(message) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  } else {
    console.error('[Host] Cannot send message: WebSocket not connected');
  }
}

/**
 * Start sending heartbeat messages to server (Story 2.4)
 */
function startHeartbeat() {
  // Clear any existing heartbeat timer
  stopHeartbeat();

  // Send heartbeat every 10 seconds
  heartbeatTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      sendMessage({ type: 'heartbeat' });
      // PERFORMANCE FIX: Remove excessive logging (60 msgs/min with 10 players)
    }
  }, HEARTBEAT_INTERVAL);
}

/**
 * Stop sending heartbeat messages (Story 2.4)
 */
function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
    console.log('[Host] Heartbeat stopped');
  }
}

/**
 * Render questioning phase (Story 4.3)
 * @param {Object} state - Questioning phase state
 */
function renderQuestioning(state) {
  console.log('[Host] Rendering questioning phase:', state);

  // Show questioning section
  showPhaseSection('questioning-section');

  // Update phase display
  setText('phase-display', 'QUESTIONING');

  // Update timer (Story 4.2)
  if (state.round_time_remaining !== undefined) {
    updateRoundTimer(state.round_time_remaining);
  }

  // Update turn display (Story 4.3)
  if (state.current_turn) {
    updateTurnDisplay(state.current_turn);
  }

  // Update player status grid
  if (state.players) {
    updatePlayerStatusGrid(state.players);
  }
}

/**
 * Update turn display with current questioner and answerer (Story 4.3)
 * @param {Object} turnInfo - Turn information object
 */
function updateTurnDisplay(turnInfo) {
  if (!turnInfo || !turnInfo.questioner || !turnInfo.answerer) {
    return;
  }

  const questionerElem = getElement('questioner-name');
  const answererElem = getElement('answerer-name');

  if (questionerElem) {
    questionerElem.textContent = escapeHtml(turnInfo.questioner.name);
  }

  if (answererElem) {
    answererElem.textContent = escapeHtml(turnInfo.answerer.name);
  }
}

/**
 * Update round timer display (Story 4.2)
 * @param {number} timeRemaining - Remaining time in seconds
 */
function updateRoundTimer(timeRemaining) {
  const timerElem = getElement('round-timer-host');
  if (!timerElem) return;

  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const timerValue = timerElem.querySelector('.timer-value');

  if (timerValue) {
    timerValue.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
}

/**
 * Update player status grid showing connection status (Story 4.3)
 * @param {Array} players - Array of player objects
 */
function updatePlayerStatusGrid(players) {
  const gridElem = getElement('player-status-grid');
  if (!gridElem || !players || players.length === 0) return;

  gridElem.innerHTML = players.map(player => {
    const statusClass = player.connected ? 'connected' : 'disconnected';
    const dotClass = player.connected ? 'online' : 'offline';

    return `
      <div class="player-status-card ${statusClass}" role="listitem">
        <span class="player-name">${escapeHtml(player.name)}</span>
        <span class="connection-dot ${dotClass}" aria-label="${player.connected ? 'Connected' : 'Disconnected'}"></span>
      </div>
    `;
  }).join('');
}

/**
 * Escape HTML to prevent XSS (Story 4.3)
 * @param {string} unsafe - Unsafe string
 * @returns {string} Escaped string
 */
function escapeHtml(unsafe) {
  if (typeof unsafe !== 'string') {
    return '';
  }
  const div = document.createElement('div');
  div.textContent = unsafe;
  return div.innerHTML;
}

/**
 * Render voting phase (placeholder)
 * @param {Object} state - Voting phase state
 */
function renderVoting(state) {
  console.log('[Host] Rendering voting phase:', state);
  // TODO: Display submission tracker (e.g., "4/7 voted")
}

/**
 * Render reveal sequence (placeholder)
 * @param {Object} state - Reveal state
 */
function renderReveal(state) {
  console.log('[Host] Rendering reveal sequence:', state);
  // TODO: Implement dramatic reveal with staggered animations
}

/**
 * Render scoring/results (placeholder)
 * @param {Object} state - Scoring state
 */
function renderScoring(state) {
  console.log('[Host] Rendering scoring:', state);
  // TODO: Display leaderboard, round results, NEXT ROUND button
}

// ============================================================================
// DOM MANIPULATION UTILITIES
// ============================================================================

/**
 * Get element by ID with error handling
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} Element or null
 */
function getElement(id) {
  const element = document.getElementById(id);
  if (!element) {
    console.warn(`[Host] Element not found: ${id}`);
  }
  return element;
}

/**
 * Set text content safely
 * @param {string} id - Element ID
 * @param {string} text - Text content
 */
function setText(id, text) {
  const element = getElement(id);
  if (element) {
    element.textContent = text;
  }
}

/**
 * Toggle element visibility
 * @param {string} id - Element ID
 * @param {boolean} visible - Visibility state
 */
function toggleVisibility(id, visible) {
  const element = getElement(id);
  if (element) {
    element.style.display = visible ? 'block' : 'none';
  }
}

/**
 * Show specific phase section and hide all others
 * @param {string} sectionId - ID of section to show
 */
function showPhaseSection(sectionId) {
  const sections = [
    'lobby-section',
    'roles-section',
    'questioning-section',
    'vote-section',
    'reveal-section',
    'scoring-section',
    'end-section'
  ];

  sections.forEach(id => {
    const section = getElement(id);
    if (section) {
      if (id === sectionId) {
        section.classList.remove('hidden');
      } else {
        section.classList.add('hidden');
      }
    }
  });
}

// ============================================================================
// QR CODE LOADING (Story 1.3)
// ============================================================================

/**
 * Load and display QR code from server
 */
async function loadQRCode() {
  const qrImage = getElement('qr-code-image');
  const joinUrlText = getElement('join-url-text');

  try {
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    const response = await fetch('/api/spyster/qr', {
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      // Set QR code image with descriptive alt text
      if (qrImage) {
        qrImage.src = data.qr_code_data;
        qrImage.alt = `QR Code to join game session ${data.session_id.substring(0, 8)}`;
      }

      // Set join URL text
      if (joinUrlText) {
        joinUrlText.textContent = data.join_url;
        joinUrlText.classList.remove('error');
      }

      console.log('[Host] QR code loaded successfully');
    } else {
      throw new Error(data.message || 'QR code generation failed');
    }
  } catch (error) {
    console.error('[Host] Failed to load QR code:', error);

    // Clear image source and show error in UI
    if (qrImage) {
      qrImage.src = '';
      qrImage.alt = 'QR Code failed to load';
    }

    if (joinUrlText) {
      joinUrlText.textContent = error.name === 'AbortError'
        ? 'Connection timeout - please refresh the page'
        : 'Failed to load QR code - please refresh the page';
      joinUrlText.classList.add('error');
    }
  }
}

// ============================================================================
// CONFIGURATION MANAGEMENT (Story 3.1)
// ============================================================================

// Configuration state
let currentConfig = {
  round_duration_minutes: 7,
  num_rounds: 5,
  location_pack: "classic"
};

// Configuration bounds (must match const.py)
const CONFIG_MIN_ROUND_DURATION = 1;
const CONFIG_MAX_ROUND_DURATION = 30;
const CONFIG_MIN_ROUNDS = 1;
const CONFIG_MAX_ROUNDS = 20;

/**
 * Initialize configuration controls
 */
function initConfigControls() {
  // Round duration controls
  const durationInc = getElement("config-round-duration-inc");
  const durationDec = getElement("config-round-duration-dec");

  if (durationInc) {
    durationInc.addEventListener("click", () => {
      const newValue = currentConfig.round_duration_minutes + 1;
      // CLIENT-SIDE VALIDATION: Check bounds before sending
      if (newValue <= CONFIG_MAX_ROUND_DURATION) {
        updateConfig("round_duration_minutes", newValue);
      }
      updateButtonStates();
    });
  }

  if (durationDec) {
    durationDec.addEventListener("click", () => {
      const newValue = currentConfig.round_duration_minutes - 1;
      // CLIENT-SIDE VALIDATION: Check bounds before sending
      if (newValue >= CONFIG_MIN_ROUND_DURATION) {
        updateConfig("round_duration_minutes", newValue);
      }
      updateButtonStates();
    });
  }

  // Number of rounds controls
  const roundsInc = getElement("config-num-rounds-inc");
  const roundsDec = getElement("config-num-rounds-dec");

  if (roundsInc) {
    roundsInc.addEventListener("click", () => {
      const newValue = currentConfig.num_rounds + 1;
      // CLIENT-SIDE VALIDATION: Check bounds before sending
      if (newValue <= CONFIG_MAX_ROUNDS) {
        updateConfig("num_rounds", newValue);
      }
      updateButtonStates();
    });
  }

  if (roundsDec) {
    roundsDec.addEventListener("click", () => {
      const newValue = currentConfig.num_rounds - 1;
      // CLIENT-SIDE VALIDATION: Check bounds before sending
      if (newValue >= CONFIG_MIN_ROUNDS) {
        updateConfig("num_rounds", newValue);
      }
      updateButtonStates();
    });
  }

  // Location pack selector
  const packSelect = getElement("config-location-pack");
  if (packSelect) {
    packSelect.addEventListener("change", (e) => {
      updateConfig("location_pack", e.target.value);
    });
  }
}

/**
 * Update button disabled states based on current config values
 */
function updateButtonStates() {
  const durationInc = getElement("config-round-duration-inc");
  const durationDec = getElement("config-round-duration-dec");
  const roundsInc = getElement("config-num-rounds-inc");
  const roundsDec = getElement("config-num-rounds-dec");

  if (durationInc) {
    durationInc.disabled = currentConfig.round_duration_minutes >= CONFIG_MAX_ROUND_DURATION;
  }
  if (durationDec) {
    durationDec.disabled = currentConfig.round_duration_minutes <= CONFIG_MIN_ROUND_DURATION;
  }
  if (roundsInc) {
    roundsInc.disabled = currentConfig.num_rounds >= CONFIG_MAX_ROUNDS;
  }
  if (roundsDec) {
    roundsDec.disabled = currentConfig.num_rounds <= CONFIG_MIN_ROUNDS;
  }
}

/**
 * Send configuration update to server
 * @param {string} field - Configuration field name
 * @param {number|string} value - New value
 */
function updateConfig(field, value) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    return;
  }

  console.log(`[Host] Sending config update: ${field} = ${value}`);

  sendMessage({
    type: "configure",
    field: field,
    value: value
  });
}

/**
 * Render configuration display from state
 * @param {Object} config - Configuration object from state
 */
function renderConfig(config) {
  if (!config) return;

  // PERFORMANCE FIX: Only update changed fields to reduce DOM manipulation
  if (currentConfig.round_duration_minutes !== config.round_duration_minutes) {
    setText("config-round-duration-value", config.round_duration_minutes);
  }

  if (currentConfig.num_rounds !== config.num_rounds) {
    setText("config-num-rounds-value", config.num_rounds);
  }

  if (currentConfig.location_pack !== config.location_pack) {
    const packSelect = getElement("config-location-pack");
    if (packSelect) {
      packSelect.value = config.location_pack;
    }
  }

  // Update local state after render
  currentConfig = config;

  // Update button states based on new config values
  updateButtonStates();

  console.log('[Host] Configuration rendered:', config);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Send start game request (Story 3.2)
 */
function startGame() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    return;
  }

  console.log('[Host] Sending start_game admin action');

  sendMessage({
    type: 'admin',
    action: 'start_game'
  });
}

/**
 * Initialize host display on page load
 */
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Host] Initializing host display');

  // Story 1.3: Load QR code for lobby display
  // Show lobby section by default
  showPhaseSection('lobby-section');

  // Load QR code immediately for testing
  // In future stories, this will be triggered by game state updates
  loadQRCode();

  // Story 3.1: Initialize configuration controls
  initConfigControls();

  // Story 3.2: Setup START button event listener
  const startBtn = getElement('start-game-btn');
  if (startBtn) {
    startBtn.addEventListener('click', startGame);
  }

  // Story 4.3: Setup NEXT TURN button event listener
  const nextTurnBtn = getElement('next-turn-btn');
  if (nextTurnBtn) {
    nextTurnBtn.addEventListener('click', advanceTurn);
  }

  // Story 2.4: Initialize WebSocket connection
  initWebSocket();
});

/**
 * Send advance turn request to server (Story 4.3: AC5)
 */
function advanceTurn() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    return;
  }

  console.log('[Host] Sending advance_turn admin action');

  sendMessage({
    type: 'admin',
    action: 'advance_turn'
  });
}
