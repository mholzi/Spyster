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

// Story 7.2: Phase indicator state
let previousPhase = null;
let phaseTransitionTimeout = null;
const PHASE_TRANSITION_DURATION = 2500; // Match CSS animation duration

// Current game state (for QR code generation)
let currentGameState = null;

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

  // Story 3.2 & 7.2: Handle phase-specific rendering
  if (message.type === 'state') {
    const phase = message.phase;

    if (phase === 'LOBBY') {
      renderLobby(message);
    } else if (phase === 'ROLES') {
      renderRoles(message);
    } else if (phase === 'QUESTIONING') {
      renderQuestioning(message);
    } else if (phase === 'VOTE') {
      renderVoting(message);
    } else if (phase === 'REVEAL') {
      renderReveal(message);
    } else if (phase === 'SCORING') {
      renderScoring(message);
    } else if (phase === 'END') {
      // Story 7.2: Update phase indicator for END phase
      showPhaseSection('end-section');
      updatePhaseIndicator('END', message);
    } else if (phase === 'PAUSED') {
      // Story 7.2: Update phase indicator for PAUSED phase
      updatePhaseIndicator('PAUSED', message);
    }
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

  // Store current game state for QR code generation
  currentGameState = state;

  // Show lobby section
  showPhaseSection('lobby-section');

  // Generate QR code with session ID
  if (state.session_id) {
    generateQRCode(state.session_id);
  }

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

  // Story 7.2: Update phase indicator with player count
  updatePhaseIndicator('LOBBY', state);
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

  // Story 7.2: Update phase indicator
  updatePhaseIndicator('ROLES', state);
}

// Story 7.3: Track previous player states for animation detection
let previousPlayerStates = new Map();

/**
 * Render player list with connection status indicators and Remove buttons (Story 2.4 & 2.6 & 7.3)
 * @param {Array} players - Array of player objects with name, connected, is_host, disconnect_duration
 */
function renderPlayerList(players) {
  const playerListEl = getElement('player-list');
  if (!playerListEl) {
    return;
  }

  if (!players || players.length === 0) {
    playerListEl.innerHTML = '<p class="empty-state">Waiting for players to join...</p>';
    previousPlayerStates.clear();
    return;
  }

  // Story 2.6: Minimum disconnect duration before removal allowed
  const MIN_DISCONNECT_FOR_REMOVAL = 60;

  // Story 7.3: Track current player names for detecting removals
  const currentPlayerNames = new Set(players.map(p => p.name));

  // Story 7.3: Animate exiting players before removing
  const existingCards = playerListEl.querySelectorAll('.player-card[data-name]');
  existingCards.forEach(card => {
    const name = card.dataset.name;
    if (!currentPlayerNames.has(name)) {
      card.classList.add('exiting');
      setTimeout(() => card.remove(), 300);
    }
  });

  // Build new player cards
  const newHtml = players.map(player => {
    const statusClass = player.connected ? 'connected' : 'disconnected';
    const statusIndicatorClass = player.connected ? 'status-connected' : 'status-disconnected';
    const statusLabel = player.connected ? 'Connected' : 'Disconnected';
    const hostBadge = player.is_host ? '<span class="host-badge">HOST</span>' : '';

    // Story 7.3: Detect if this is a new player or status changed
    const prevState = previousPlayerStates.get(player.name);
    let animationClass = '';
    if (!prevState) {
      animationClass = 'entering';
    } else if (prevState.connected !== player.connected) {
      animationClass = player.connected ? 'just-connected status-changed' : 'just-disconnected status-changed';
    }

    // Remove button logic (Story 2.6)
    let removeButton = '';
    if (!player.connected && player.disconnect_duration !== null) {
      const duration = typeof player.disconnect_duration === 'number' && !isNaN(player.disconnect_duration)
        ? player.disconnect_duration
        : 0;

      if (duration >= MIN_DISCONNECT_FOR_REMOVAL) {
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
        const secondsRemaining = Math.ceil(MIN_DISCONNECT_FOR_REMOVAL - duration);
        removeButton = `
          <span class="disconnect-timer">
            Remove in ${secondsRemaining}s
          </span>
        `;
      }
    }

    // Get initial for avatar
    const initial = player.name.charAt(0).toUpperCase();

    return `
      <div class="player-card ${statusClass} ${animationClass}"
           data-name="${escapeHtml(player.name)}"
           data-connected="${player.connected}">
        <div class="player-avatar">
          <span class="avatar-initial">${initial}</span>
          <span class="status-ring"></span>
        </div>
        <div class="status-indicator ${statusIndicatorClass}" aria-label="${statusLabel}"></div>
        <div class="player-info">
          <span class="player-name">${escapeHtml(player.name)}</span>
          ${hostBadge}
        </div>
        ${removeButton}
      </div>
    `;
  }).join('');

  // Update DOM
  playerListEl.innerHTML = newHtml;

  // Story 7.3: Update previous states for next render
  previousPlayerStates.clear();
  players.forEach(player => {
    previousPlayerStates.set(player.name, {
      connected: player.connected,
      is_host: player.is_host
    });
  });

  // Story 7.3: Remove animation classes after animation completes
  setTimeout(() => {
    playerListEl.querySelectorAll('.entering, .status-changed, .just-connected, .just-disconnected').forEach(el => {
      el.classList.remove('entering', 'status-changed', 'just-connected', 'just-disconnected');
    });
  }, 800);
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

  // Story 7.2: Update phase indicator with round info
  updatePhaseIndicator('QUESTIONING', state);

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

// Story 7.3: Track gameplay phase player states for animation detection
let previousGameplayPlayerStates = new Map();

/**
 * Update player status grid showing connection status (Story 4.3 & 7.3)
 * Enhanced with animations and TV-optimized styling.
 * @param {Array} players - Array of player objects
 */
function updatePlayerStatusGrid(players) {
  const gridElem = getElement('player-status-grid');
  if (!gridElem || !players || players.length === 0) return;

  // Story 7.3: Track current player names for detecting removals
  const currentPlayerNames = new Set(players.map(p => p.name));

  // Story 7.3: Animate exiting players
  const existingCards = gridElem.querySelectorAll('.player-status-card[data-name]');
  existingCards.forEach(card => {
    const name = card.dataset.name;
    if (!currentPlayerNames.has(name)) {
      card.classList.add('exiting');
      setTimeout(() => card.remove(), 300);
    }
  });

  gridElem.innerHTML = players.map(player => {
    const statusClass = player.connected ? 'connected' : 'disconnected';
    const dotClass = player.connected ? 'online' : 'offline';

    // Story 7.3: Detect new players or status changes for animations
    const prevState = previousGameplayPlayerStates.get(player.name);
    let animationClass = '';
    if (!prevState) {
      animationClass = 'entering';
    } else if (prevState.connected !== player.connected) {
      animationClass = 'status-changed';
    }

    return `
      <div class="player-status-card ${statusClass} ${animationClass}"
           data-name="${escapeHtml(player.name)}"
           data-connected="${player.connected}"
           role="listitem">
        <span class="player-name">${escapeHtml(player.name)}</span>
        <span class="connection-dot ${dotClass}" aria-label="${player.connected ? 'Connected' : 'Disconnected'}"></span>
      </div>
    `;
  }).join('');

  // Story 7.3: Update previous states for next render
  previousGameplayPlayerStates.clear();
  players.forEach(player => {
    previousGameplayPlayerStates.set(player.name, {
      connected: player.connected
    });
  });

  // Story 7.3: Remove animation classes after animation completes
  setTimeout(() => {
    gridElem.querySelectorAll('.entering, .status-changed').forEach(el => {
      el.classList.remove('entering', 'status-changed');
    });
  }, 600);
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
 * Render voting phase with submission tracker (Story 7.4)
 * @param {Object} state - Voting phase state
 */
function renderVoting(state) {
  console.log('[Host] Rendering voting phase:', state);

  // Show vote section
  showPhaseSection('vote-section');

  // Story 7.2: Update phase indicator with vote count
  updatePhaseIndicator('VOTE', state);

  // Story 7.4: Update vote timer
  if (state.vote_time_remaining !== undefined) {
    updateVoteTimer(state.vote_time_remaining);
  }

  // Story 7.4: Update submission tracker
  const votesSubmitted = state.votes_submitted || 0;
  const totalPlayers = state.player_count || state.total_players || 0;
  updateSubmissionTracker(votesSubmitted, totalPlayers);

  // Update status message
  const statusMessage = getElement('vote-status-message');
  if (statusMessage) {
    if (votesSubmitted === totalPlayers && totalPlayers > 0) {
      statusMessage.textContent = 'All votes are in! Revealing soon...';
    } else {
      statusMessage.textContent = 'Waiting for all players to submit their votes...';
    }
  }
}

/**
 * Update vote timer display (Story 7.4)
 * @param {number} timeRemaining - Remaining time in seconds
 */
function updateVoteTimer(timeRemaining) {
  const timerElem = getElement('vote-timer-host');
  if (!timerElem) return;

  const timerValue = timerElem.querySelector('.timer-value');
  if (timerValue) {
    timerValue.textContent = timeRemaining;
  }
}

/**
 * Update submission tracker with progress ring animation (Story 7.4 Task 1)
 * @param {number} votesSubmitted - Number of votes submitted
 * @param {number} totalPlayers - Total players who need to vote
 */
function updateSubmissionTracker(votesSubmitted, totalPlayers) {
  const voteCountEl = getElement('vote-count');
  const voteTotalEl = getElement('vote-total');
  const progressRing = getElement('progress-ring-fill');

  if (voteCountEl) {
    const prevCount = parseInt(voteCountEl.textContent) || 0;
    voteCountEl.textContent = votesSubmitted;

    // Pulse animation on increment
    if (votesSubmitted > prevCount) {
      voteCountEl.classList.add('pulse');
      setTimeout(() => voteCountEl.classList.remove('pulse'), 400);
    }
  }

  if (voteTotalEl) {
    voteTotalEl.textContent = totalPlayers;
  }

  // Update progress ring
  if (progressRing && totalPlayers > 0) {
    const circumference = 326.73; // 2 * PI * 52 (radius)
    const progress = votesSubmitted / totalPlayers;
    const offset = circumference * (1 - progress);
    progressRing.style.strokeDashoffset = offset;

    // Add complete class when all votes are in
    if (votesSubmitted === totalPlayers) {
      progressRing.classList.add('complete');
    } else {
      progressRing.classList.remove('complete');
    }
  }
}

// Story 7.4: Track reveal sequence state
let revealSequenceRunning = false;
let revealSequenceTimeout = null;

/**
 * Render reveal sequence with staged animations (Story 7.4)
 * @param {Object} state - Reveal state
 */
function renderReveal(state) {
  console.log('[Host] Rendering reveal sequence:', state);

  // Show reveal section
  showPhaseSection('reveal-section');

  // Story 7.2: Update phase indicator
  updatePhaseIndicator('REVEAL', state);

  // Build vote cards grid
  if (state.votes) {
    renderVoteCards(state.votes);
  }

  // Run reveal sequence if not already running
  if (!revealSequenceRunning && state.votes) {
    runRevealSequence(state.votes, state.conviction);
  }
}

/**
 * Render vote cards in grid (Story 7.4 Task 2)
 * @param {Array} votes - Array of vote objects
 */
function renderVoteCards(votes) {
  const gridEl = getElement('vote-cards-grid');
  if (!gridEl || !votes) return;

  gridEl.innerHTML = votes.map((vote, index) => {
    const isAbstain = !vote.target || vote.target === 'abstain';
    const confidenceLabel = getConfidenceLabel(vote.confidence);

    return `
      <div class="vote-card ${isAbstain ? 'abstained' : ''}"
           data-voter="${escapeHtml(vote.voter)}"
           data-vote-revealed="false"
           data-bet-revealed="false"
           role="listitem">
        <div class="vote-card-header">
          <span class="voter-name">${escapeHtml(vote.voter)}</span>
          <span class="vote-arrow">→</span>
        </div>
        <div class="vote-target-container">
          <span class="target-placeholder">???</span>
          <span class="target-name">${isAbstain ? 'ABSTAINED' : escapeHtml(vote.target)}</span>
          <span class="confidence-badge" data-level="${vote.confidence || 1}">${confidenceLabel}</span>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Get confidence level label (Story 7.4)
 * @param {number} level - Confidence level (1, 2, or 3)
 * @returns {string} Label text
 */
function getConfidenceLabel(level) {
  switch (level) {
    case 3: return 'ALL IN';
    case 2: return '×2';
    case 1:
    default: return '×1';
  }
}

/**
 * Run staged reveal sequence (Story 7.4 Task 3 & 5)
 * @param {Array} votes - Array of vote objects
 * @param {Object} conviction - Conviction result
 */
async function runRevealSequence(votes, conviction) {
  if (revealSequenceRunning) return;
  revealSequenceRunning = true;

  console.log('[Host] Starting reveal sequence');

  const stageTextEl = getElement('reveal-stage-text');
  const voteCards = document.querySelectorAll('.vote-card');

  try {
    // Step 1: "Votes are in..." text
    showRevealStageText('Votes are in...', stageTextEl);
    await delay(1500);

    // Step 2: Flip votes one by one
    for (let i = 0; i < voteCards.length; i++) {
      const card = voteCards[i];
      card.classList.add('revealing');
      card.setAttribute('data-vote-revealed', 'true');
      await delay(500);
    }

    await delay(1000);

    // Step 3: "Now the bets..." text
    showRevealStageText('Now the bets...', stageTextEl);
    await delay(1500);

    // Step 4: Reveal all bets simultaneously
    voteCards.forEach(card => {
      card.classList.add('bet-revealing');
      card.setAttribute('data-bet-revealed', 'true');
    });
    await delay(2000);

    // Hide stage text
    if (stageTextEl) {
      stageTextEl.classList.remove('visible');
      stageTextEl.classList.add('fade-out');
    }

    await delay(500);

    // Step 5: Show conviction result if available
    if (conviction) {
      showConvictionResult(conviction);
    }

  } catch (error) {
    console.error('[Host] Reveal sequence error:', error);
  } finally {
    revealSequenceRunning = false;
  }
}

/**
 * Show reveal stage text with animation (Story 7.4 Task 3)
 * @param {string} text - Text to display
 * @param {HTMLElement} element - Stage text element
 */
function showRevealStageText(text, element) {
  if (!element) return;

  element.classList.remove('visible', 'fade-out');
  element.textContent = text;

  // Force reflow
  void element.offsetWidth;

  element.classList.add('visible');
}

/**
 * Show conviction result overlay (Story 7.4 Task 4)
 * @param {Object} conviction - Conviction result object
 */
function showConvictionResult(conviction) {
  const overlay = getElement('conviction-overlay');
  const verdictEl = getElement('conviction-verdict');
  const detailsEl = getElement('conviction-details');
  const spyRevealEl = getElement('spy-reveal');
  const spyNameEl = getElement('spy-name');

  if (!overlay || !verdictEl) return;

  // Remove previous classes
  overlay.classList.remove('spy-caught', 'innocent', 'tie', 'spy-wins', 'hidden');

  // Determine verdict type and text
  let verdictText = '';
  let verdictClass = '';
  let detailsText = '';
  let showSpy = false;

  if (conviction.spy_guess_correct) {
    // Spy correctly guessed the location
    verdictText = 'SPY WINS!';
    verdictClass = 'spy-wins';
    detailsText = 'The spy correctly guessed the location!';
    showSpy = true;
  } else if (conviction.is_tie) {
    // Tie vote
    verdictText = 'TIE!';
    verdictClass = 'tie';
    detailsText = 'No one was convicted - the spy survives!';
    showSpy = true;
  } else if (conviction.is_spy === true) {
    // Spy was caught
    verdictText = 'SPY CAUGHT!';
    verdictClass = 'spy-caught';
    detailsText = `${escapeHtml(conviction.convicted_player)} was the spy!`;
    showSpy = false; // Already shown in details
  } else if (conviction.is_spy === false) {
    // Innocent was convicted
    verdictText = 'INNOCENT!';
    verdictClass = 'innocent';
    detailsText = `${escapeHtml(conviction.convicted_player)} was not the spy!`;
    showSpy = true;
  } else {
    // No conviction (abstain majority or other)
    verdictText = 'NO VERDICT';
    verdictClass = 'tie';
    detailsText = 'Not enough votes to convict anyone.';
    showSpy = true;
  }

  // Set content
  verdictEl.textContent = verdictText;
  overlay.classList.add(verdictClass);

  if (detailsEl) {
    detailsEl.textContent = detailsText;
  }

  // Show spy identity if needed
  if (spyRevealEl && spyNameEl && showSpy && conviction.actual_spy) {
    spyNameEl.textContent = conviction.actual_spy;
    spyRevealEl.classList.remove('hidden');
    spyRevealEl.classList.add('visible');
  } else if (spyRevealEl) {
    spyRevealEl.classList.add('hidden');
    spyRevealEl.classList.remove('visible');
  }

  // Show overlay with animation
  overlay.classList.remove('hidden');
  setTimeout(() => overlay.classList.add('visible'), 50);

  console.log('[Host] Conviction result displayed:', verdictText);
}

/**
 * Hide conviction overlay (Story 7.4)
 */
function hideConvictionOverlay() {
  const overlay = getElement('conviction-overlay');
  if (overlay) {
    overlay.classList.remove('visible');
    setTimeout(() => {
      overlay.classList.add('hidden');
      overlay.classList.remove('spy-caught', 'innocent', 'tie', 'spy-wins');
    }, 500);
  }
}

/**
 * Reset reveal sequence state (Story 7.4)
 * Call when transitioning away from reveal phase
 */
function resetRevealSequence() {
  revealSequenceRunning = false;
  if (revealSequenceTimeout) {
    clearTimeout(revealSequenceTimeout);
    revealSequenceTimeout = null;
  }
  hideConvictionOverlay();
}

/**
 * Promise-based delay utility (Story 7.4)
 * @param {number} ms - Milliseconds to delay
 * @returns {Promise} Resolves after delay
 */
function delay(ms) {
  return new Promise(resolve => {
    revealSequenceTimeout = setTimeout(resolve, ms);
  });
}

/**
 * Render scoring/results (placeholder)
 * @param {Object} state - Scoring state
 */
function renderScoring(state) {
  console.log('[Host] Rendering scoring:', state);

  // Show scoring section
  showPhaseSection('scoring-section');

  // Story 7.2: Update phase indicator with round complete info
  updatePhaseIndicator('SCORING', state);

  // TODO: Display leaderboard, round results, NEXT ROUND button
}

// ============================================================================
// STORY 7.2: PHASE INDICATOR FUNCTIONS
// ============================================================================

/**
 * Update phase indicator display with phase-specific content (Task 4.1, 4.2)
 * @param {string} phase - Current phase name
 * @param {Object} data - Phase-specific data for secondary info
 */
function updatePhaseIndicator(phase, data) {
  const indicator = getElement('phase-indicator');
  const phaseName = getElement('phase-name');
  const phaseInfo = getElement('phase-info');

  if (!indicator || !phaseName) return;

  // Update data attribute for CSS styling
  indicator.setAttribute('data-phase', phase);

  // Set phase name
  phaseName.textContent = getPhaseDisplayName(phase);

  // Set phase-specific secondary info (Task 2)
  if (phaseInfo) {
    phaseInfo.textContent = getPhaseInfo(phase, data);
  }

  // Check for phase change and trigger transition (Task 4.3, 4.4)
  if (phase !== previousPhase && previousPhase !== null) {
    showPhaseTransition(phase, data);
  }
  previousPhase = phase;

  // Story 7.5: Update admin bar visibility based on phase
  updateAdminBarVisibility(phase);
}

/**
 * Get display name for phase (Task 2)
 * @param {string} phase - Phase code
 * @returns {string} Display name
 */
function getPhaseDisplayName(phase) {
  const names = {
    'LOBBY': 'LOBBY',
    'ROLES': 'ROLES',
    'QUESTIONING': 'QUESTIONING',
    'VOTE': 'VOTING',
    'REVEAL': 'REVEAL',
    'SCORING': 'RESULTS',
    'END': 'GAME OVER',
    'PAUSED': 'PAUSED'
  };
  return names[phase] || phase;
}

/**
 * Get phase-specific secondary info text (Task 2.1-2.5)
 * @param {string} phase - Current phase
 * @param {Object} data - Phase data
 * @returns {string} Info text
 */
function getPhaseInfo(phase, data) {
  if (!data) return '';

  switch (phase) {
    case 'LOBBY':
      // AC#1: Show "X/10 players"
      const current = data.connected_count || data.player_count || 0;
      const max = data.max_players || MAX_PLAYERS;
      return `${current}/${max} players`;

    case 'QUESTIONING':
      // AC#2: Show "Round X of Y"
      const round = data.round_number || 1;
      const totalRounds = data.total_rounds || data.num_rounds || 5;
      return `Round ${round} of ${totalRounds}`;

    case 'VOTE':
      // AC#3: Show "X/Y voted"
      const voted = data.votes_submitted || 0;
      const total = data.player_count || data.total_players || 0;
      return `${voted}/${total} voted`;

    case 'REVEAL':
      // AC#4: No secondary info
      return '';

    case 'SCORING':
      // AC#5: Show "Round X Complete"
      const completedRound = data.round_number || 1;
      return `Round ${completedRound} Complete`;

    case 'END':
      return 'Final Results';

    case 'PAUSED':
      return 'Waiting for host...';

    default:
      return '';
  }
}

/**
 * Show phase transition overlay with animation (Task 3.1-3.4, 4.4)
 * @param {string} phase - New phase
 * @param {Object} data - Phase data
 */
function showPhaseTransition(phase, data) {
  const overlay = getElement('phase-transition-overlay');
  const textEl = getElement('phase-transition-text');

  if (!overlay || !textEl) return;

  // Clear any existing transition
  if (phaseTransitionTimeout) {
    clearTimeout(phaseTransitionTimeout);
    overlay.classList.remove('active');
    overlay.classList.add('hidden');
  }

  // Get transition text and type
  const { text, type } = getTransitionContent(phase, data);

  // Set content and type
  textEl.textContent = text;
  overlay.setAttribute('data-type', type);

  // Show overlay and trigger animation
  overlay.classList.remove('hidden');
  // Force reflow to restart animation
  void overlay.offsetWidth;
  overlay.classList.add('active');

  console.log('[Host] Phase transition:', text, '(type:', type, ')');

  // Auto-dismiss after animation completes (Task 3.4)
  phaseTransitionTimeout = setTimeout(() => {
    overlay.classList.remove('active');
    overlay.classList.add('hidden');
  }, PHASE_TRANSITION_DURATION);
}

/**
 * Get transition overlay content based on phase change (Task 3.3)
 * @param {string} phase - New phase
 * @param {Object} data - Phase data
 * @returns {{text: string, type: string}} Transition content
 */
function getTransitionContent(phase, data) {
  switch (phase) {
    case 'QUESTIONING':
      const round = data?.round_number || 1;
      return { text: `ROUND ${round}`, type: 'round' };

    case 'VOTE':
      return { text: 'VOTE CALLED', type: 'vote' };

    case 'REVEAL':
      return { text: 'REVEALING...', type: 'reveal' };

    case 'SCORING':
      // Check conviction result if available
      if (data?.conviction?.is_spy === true) {
        return { text: 'SPY CAUGHT!', type: 'spy-caught' };
      } else if (data?.conviction?.is_spy === false) {
        return { text: 'INNOCENT!', type: 'innocent' };
      }
      return { text: 'RESULTS', type: 'reveal' };

    case 'END':
      return { text: 'GAME OVER', type: 'end' };

    case 'PAUSED':
      return { text: 'PAUSED', type: 'vote' };

    case 'ROLES':
      return { text: 'ROLES ASSIGNED', type: 'round' };

    default:
      return { text: phase, type: 'round' };
  }
}

/**
 * Update vote submission count during VOTE phase (Task 4.5)
 * Called when vote count changes during voting phase
 * @param {number} votesSubmitted - Number of votes submitted
 * @param {number} totalPlayers - Total players who need to vote
 */
function updateVoteSubmissionCount(votesSubmitted, totalPlayers) {
  const phaseInfo = getElement('phase-info');
  const indicator = getElement('phase-indicator');

  if (!phaseInfo || !indicator) return;

  // Only update if in VOTE phase
  if (indicator.getAttribute('data-phase') === 'VOTE') {
    phaseInfo.textContent = `${votesSubmitted}/${totalPlayers} voted`;
  }
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
// QR CODE GENERATION (Story 1.3)
// ============================================================================

// Cache for QR code to avoid regeneration
let cachedQRUrl = null;

/**
 * Generate and display QR code client-side
 * Uses QRCode.js library for generation (no server dependency)
 * @param {string} sessionId - The game session ID
 */
function generateQRCode(sessionId) {
  const qrContainer = getElement('qr-code-container');
  const joinUrlText = getElement('join-url-text');

  if (!sessionId) {
    console.warn('[Host] No session ID available for QR code');
    if (joinUrlText) {
      joinUrlText.textContent = 'Waiting for session...';
      joinUrlText.classList.add('error');
    }
    return;
  }

  // Construct join URL from current host
  const joinUrl = `${window.location.origin}/api/spyster/player?session=${sessionId}`;

  // Skip if URL hasn't changed
  if (cachedQRUrl === joinUrl) {
    return;
  }

  try {
    if (qrContainer) {
      // Clear previous QR code
      qrContainer.innerHTML = '';

      // Check if QRCode library is loaded
      if (typeof QRCode !== 'undefined') {
        new QRCode(qrContainer, {
          text: joinUrl,
          width: 300,
          height: 300,
          colorDark: '#000000',
          colorLight: '#ffffff',
          correctLevel: QRCode.CorrectLevel.M
        });
        console.log('[Host] QR code generated successfully');
      } else {
        console.error('[Host] QRCode library not loaded');
        qrContainer.innerHTML = '<p class="error">QR code library not loaded</p>';
      }

      cachedQRUrl = joinUrl;
    }

    // Set join URL text
    if (joinUrlText) {
      joinUrlText.textContent = joinUrl;
      joinUrlText.classList.remove('error');
    }
  } catch (error) {
    console.error('[Host] Failed to generate QR code:', error);

    if (qrContainer) {
      qrContainer.innerHTML = '<p class="error">Failed to generate QR code</p>';
    }

    if (joinUrlText) {
      joinUrlText.textContent = 'Failed to generate QR code';
      joinUrlText.classList.add('error');
    }
  }
}

/**
 * Legacy function for backward compatibility
 * Now generates QR code from current game state session ID
 */
async function loadQRCode() {
  // Get session ID from current game state
  if (currentGameState && currentGameState.session_id) {
    generateQRCode(currentGameState.session_id);
  } else {
    console.warn('[Host] No game state available for QR code');
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

  // Story 7.5: Initialize admin controls
  initAdminControls();

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

// ============================================================================
// STORY 7.5: ADMIN CONTROLS
// ============================================================================

// Track game pause state
let isPaused = false;
let currentPhase = 'LOBBY';

/**
 * Initialize admin control bar and event handlers (Story 7.5 Task 5.1)
 */
function initAdminControls() {
  console.log('[Host] Initializing admin controls');

  // Toggle button - expand/collapse admin bar
  const toggleBtn = getElement('admin-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', toggleAdminBar);
  }

  // Skip to Vote button
  const skipVoteBtn = getElement('btn-skip-vote');
  if (skipVoteBtn) {
    skipVoteBtn.addEventListener('click', handleSkipToVote);
  }

  // Next Round button
  const nextRoundBtn = getElement('btn-next-round');
  if (nextRoundBtn) {
    nextRoundBtn.addEventListener('click', handleNextRound);
  }

  // Pause/Resume button
  const pauseBtn = getElement('btn-pause');
  if (pauseBtn) {
    pauseBtn.addEventListener('click', handlePauseResume);
  }

  // End Game button
  const endGameBtn = getElement('btn-end-game');
  if (endGameBtn) {
    endGameBtn.addEventListener('click', showEndGameModal);
  }

  // Modal buttons
  const modalCancel = getElement('modal-cancel');
  if (modalCancel) {
    modalCancel.addEventListener('click', hideConfirmModal);
  }

  const modalConfirm = getElement('modal-confirm');
  if (modalConfirm) {
    modalConfirm.addEventListener('click', handleEndGameConfirm);
  }

  // Modal backdrop click to dismiss
  const modalBackdrop = document.querySelector('.modal-backdrop');
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', hideConfirmModal);
  }

  // Keyboard handling for modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      hideConfirmModal();
    }
  });
}

/**
 * Toggle admin bar expand/collapse (Story 7.5 Task 1.3)
 */
function toggleAdminBar() {
  const adminBar = getElement('admin-bar');
  const toggleBtn = getElement('admin-toggle');

  if (adminBar) {
    adminBar.classList.toggle('collapsed');
    const isExpanded = !adminBar.classList.contains('collapsed');

    if (toggleBtn) {
      toggleBtn.setAttribute('aria-expanded', isExpanded);
    }

    console.log('[Host] Admin bar', isExpanded ? 'expanded' : 'collapsed');
  }
}

/**
 * Update admin bar button visibility based on phase (Story 7.5 Task 5.2)
 * @param {string} phase - Current game phase
 */
function updateAdminBarVisibility(phase) {
  currentPhase = phase;

  const buttons = document.querySelectorAll('.admin-btn[data-phases]');
  buttons.forEach(btn => {
    const phases = btn.dataset.phases.split(',');
    const shouldShow = phases.includes(phase) || phases.includes('*');

    if (shouldShow) {
      btn.classList.remove('hidden');
    } else {
      btn.classList.add('hidden');
    }
  });

  // Update pause button state
  updatePauseButton(phase === 'PAUSED');

  // Show/hide paused overlay
  if (phase === 'PAUSED') {
    showPausedOverlay();
  } else {
    hidePausedOverlay();
  }

  console.log('[Host] Admin bar updated for phase:', phase);
}

/**
 * Update pause button text and styling (Story 7.5 Task 3.3)
 * @param {boolean} paused - Whether game is paused
 */
function updatePauseButton(paused) {
  const pauseBtn = getElement('btn-pause');
  if (!pauseBtn) return;

  isPaused = paused;

  if (paused) {
    pauseBtn.textContent = 'RESUME';
    pauseBtn.classList.add('resume');
    pauseBtn.classList.remove('hidden'); // Always show resume when paused
  } else {
    pauseBtn.textContent = 'PAUSE';
    pauseBtn.classList.remove('resume');
  }
}

/**
 * Handle Skip to Vote button click (Story 7.5 Task 2.1)
 */
function handleSkipToVote() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    return;
  }

  console.log('[Host] Sending skip_to_vote admin action');

  sendMessage({
    type: 'admin',
    action: 'skip_to_vote'
  });
}

/**
 * Handle Next Round button click (Story 7.5 Task 2.4)
 */
function handleNextRound() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    return;
  }

  console.log('[Host] Sending next_round admin action');

  sendMessage({
    type: 'admin',
    action: 'next_round'
  });
}

/**
 * Handle Pause/Resume button click (Story 7.5 Task 3.1, 3.2)
 */
function handlePauseResume() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    return;
  }

  const action = isPaused ? 'resume_game' : 'pause_game';
  console.log(`[Host] Sending ${action} admin action`);

  sendMessage({
    type: 'admin',
    action: action
  });
}

/**
 * Show paused overlay (Story 7.5 Task 3.4)
 */
function showPausedOverlay() {
  const overlay = getElement('paused-overlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.add('visible'), 50);
  }
}

/**
 * Hide paused overlay (Story 7.5 Task 3.4)
 */
function hidePausedOverlay() {
  const overlay = getElement('paused-overlay');
  if (overlay) {
    overlay.classList.remove('visible');
    setTimeout(() => overlay.classList.add('hidden'), 300);
  }
}

/**
 * Show end game confirmation modal (Story 7.5 Task 4.1)
 */
function showEndGameModal() {
  const modal = getElement('confirm-modal');
  if (modal) {
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('visible'), 50);

    // Focus cancel button for keyboard navigation
    const cancelBtn = getElement('modal-cancel');
    if (cancelBtn) {
      cancelBtn.focus();
    }
  }
}

/**
 * Hide confirmation modal (Story 7.5 Task 4.4)
 */
function hideConfirmModal() {
  const modal = getElement('confirm-modal');
  if (modal) {
    modal.classList.remove('visible');
    setTimeout(() => modal.classList.add('hidden'), 300);
  }
}

/**
 * Handle end game confirmation (Story 7.5 Task 4.3)
 */
function handleEndGameConfirm() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[Host] WebSocket not connected');
    hideConfirmModal();
    return;
  }

  console.log('[Host] Sending end_game admin action');

  sendMessage({
    type: 'admin',
    action: 'end_game'
  });

  hideConfirmModal();
}
