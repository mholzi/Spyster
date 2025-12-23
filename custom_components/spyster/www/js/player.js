/**
 * Spyster Player UI JavaScript
 * Handles WebSocket connection and game state rendering for player phone interface
 */

// ============================================================================
// WEBSOCKET CONNECTION
// ============================================================================

/**
 * PlayerClient class - manages WebSocket connection and UI state
 */
class PlayerClient {
  constructor() {
    this.ws = null;
    this.connectionState = 'disconnected'; // disconnected, connecting, connected, error
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000; // 2 seconds, exponential backoff
    this.connectionId = null;
    this.serverVersion = null;
    this.heartbeatTimer = null; // Story 2.4: Heartbeat timer
    this.HEARTBEAT_INTERVAL = 10000; // Story 2.4: 10 seconds (matches const.py)

    // Story 2.2: Player session state
    this.playerName = null;
    this.sessionToken = null;
    this.isInGame = false;

    // Story 4.4: Timer state
    this.timerInterval = null;
  }

  /**
   * Initialize WebSocket connection to game server (Story 2.1 & 2.5)
   */
  connect() {
    this.connectionState = 'connecting';
    this.updateConnectionUI();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl = `${protocol}//${window.location.host}/api/spyster/ws`;

    // Story 2.5: Check for session token in URL or storage
    const token = this.getSessionToken();
    if (token) {
      wsUrl += `?token=${token}`;
      console.log('[Player] Reconnecting with token:', '***' + token.substring(token.length - 4));
    } else {
      console.log('[Player] Connecting to WebSocket:', wsUrl);
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => this.onOpen();
    this.ws.onmessage = (event) => this.onMessage(event);
    this.ws.onerror = (error) => this.onError(error);
    this.ws.onclose = () => this.onClose();
  }

  /**
   * Get session token from URL or sessionStorage (Story 2.5)
   * @returns {string|null} Session token
   */
  getSessionToken() {
    // Check URL parameters first
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');
    if (tokenFromUrl) {
      this.sessionToken = tokenFromUrl;
      sessionStorage.setItem('spyster_token', tokenFromUrl);
      return tokenFromUrl;
    }

    // Check sessionStorage
    const tokenFromStorage = sessionStorage.getItem('spyster_token');
    if (tokenFromStorage) {
      this.sessionToken = tokenFromStorage;
      return tokenFromStorage;
    }

    return null;
  }

  /**
   * Handle WebSocket open event
   */
  onOpen() {
    this.connectionState = 'connected';
    this.reconnectAttempts = 0;
    this.updateConnectionUI();
    console.log('[Player] WebSocket connected');
    this.startHeartbeat(); // Story 2.4: Start heartbeat on connection
  }

  /**
   * Handle incoming WebSocket messages
   * @param {MessageEvent} event - WebSocket message event
   */
  onMessage(event) {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (err) {
      console.error('[Player] Failed to parse server message:', err);
      return;
    }

    const messageType = message.type;

    if (messageType === 'error') {
      this.handleError(message);
      return;
    }

    // Route to specific handlers
    switch (messageType) {
      case 'welcome':
        this.handleWelcome(message);
        break;
      case 'session_restored': // Story 2.5
        this.handleSessionRestored(message);
        break;
      case 'join_success': // Story 2.2 - Server sends 'join_success'
        this.handleJoinSuccess(message);
        break;
      case 'state':
        this.handleStateUpdate(message);
        break;
      case 'ack':
        console.log('[Player] Server acknowledged:', message.received);
        break;
      default:
        console.warn('[Player] Unknown message type:', messageType);
    }
  }

  /**
   * Handle WebSocket error
   * @param {Event} event - WebSocket error event
   */
  onError(event) {
    console.error('[Player] WebSocket error:', event);
    this.connectionState = 'error';
    this.updateConnectionUI();
  }

  /**
   * Handle WebSocket close event
   */
  onClose() {
    console.log('[Player] WebSocket closed');
    this.connectionState = 'disconnected';
    this.updateConnectionUI();
    this.stopHeartbeat(); // Story 2.4: Stop heartbeat on disconnect

    // Attempt reconnection with exponential backoff
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
      console.log(`[Player] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, delay);
    } else {
      console.error('[Player] Max reconnection attempts reached');
      this.showError('Connection lost. Please reload the page.');
    }
  }

  /**
   * Handle welcome message from server
   * @param {Object} message - Welcome message
   */
  handleWelcome(message) {
    console.log('[Player] Connected to server:', message.connection_id);
    this.connectionId = message.connection_id;
    this.serverVersion = message.server_version;
  }

  /**
   * Handle error message from server
   * @param {Object} message - Error message
   */
  handleError(message) {
    console.error('[Player] Server error:', message.code, message.message);

    // Story 2.5: Handle session expiration
    if (message.code === 'SESSION_EXPIRED' || message.code === 'INVALID_TOKEN') {
      // Clear session token
      this.sessionToken = null;
      sessionStorage.removeItem('spyster_token');
      // Remove token from URL
      const url = new URL(window.location);
      url.searchParams.delete('token');
      window.history.replaceState({}, '', url);
      // Show error and return to join screen
      this.showError(message.message);
      this.isInGame = false;
      return;
    }

    // Handle connection limit - don't attempt reconnection
    if (message.code === 'CONNECTION_LIMIT') {
      this.maxReconnectAttempts = 0; // Stop reconnection attempts
      this.showError(message.message);
      return;
    }

    // Display error to user
    this.showError(message.message);

    // Story 2.2: Re-enable join form for retryable errors
    if (message.code === 'GAME_ALREADY_STARTED') {
      // Disable join button permanently
      const joinButton = document.getElementById('join-button');
      if (joinButton) {
        joinButton.textContent = 'Game In Progress';
        joinButton.disabled = true;
      }
    } else {
      // Re-enable form for retry
      const nameInput = document.getElementById('player-name-input');
      const joinButton = document.getElementById('join-button');
      if (nameInput) nameInput.disabled = false;
      if (joinButton) joinButton.disabled = false;
    }
  }

  /**
   * Handle session restored message (Story 2.5)
   * @param {Object} message - Session restored message
   */
  handleSessionRestored(message) {
    console.log('[Player] Session restored:', message.name);

    this.playerName = message.name;
    this.sessionToken = message.token;
    this.isInGame = true;

    // Update URL with token
    const url = new URL(window.location);
    url.searchParams.set('token', this.sessionToken);
    window.history.replaceState({}, '', url);

    // Store in sessionStorage
    sessionStorage.setItem('spyster_token', this.sessionToken);

    // Show lobby (server will send state update)
    this.showLobby();
  }

  /**
   * Handle join success message (Story 2.2)
   * @param {Object} message - Join success message
   */
  handleJoinSuccess(message) {
    console.log('[Player] Join successful:', message.player_name);

    // FIXED: Use correct field names from server response
    this.playerName = message.player_name;
    this.sessionToken = message.session_token;
    this.isInGame = true;

    // Store session token in URL and sessionStorage for mobile browser compatibility
    const url = new URL(window.location);
    url.searchParams.set('token', this.sessionToken);
    window.history.replaceState({}, '', url);
    sessionStorage.setItem('spyster_token', this.sessionToken);

    // Switch to lobby view
    this.showLobby();
  }

  /**
   * Handle state update from server (Story 2.2 + Story 3.5 + Story 4.4)
   * @param {Object} state - Game state
   */
  handleStateUpdate(state) {
    console.log('[Player] State update:', state);

    if (state.phase === 'LOBBY') {
      this.updatePlayerList(state.players || []);
      this.updatePlayerCount(state.player_count || 0);

      // Story 3.1: Update configuration display
      if (state.config) {
        this.renderConfigDisplay(state.config);
      }
    }

    // Story 3.5: Handle ROLES phase
    if (state.phase === 'ROLES') {
      this.handleRolesPhase(state);
    }

    // Story 4.4: Handle QUESTIONING phase
    if (state.phase === 'QUESTIONING') {
      this.handleQuestioningPhase(state);
      // Story 4.2: Update timer display on every state broadcast (NFR5)
      if (state.timer) {
        this.startTimerDisplay(state.timer);
      }
    }

    // TODO: Handle other phases in future stories
  }

  /**
   * Handle ROLES phase state update (Story 3.2 & 3.5)
   * @param {Object} state - Game state with role_data
   */
  handleRolesPhase(state) {
    // Story 3.2: If role_data not yet available, show loading state
    if (!state.role_data) {
      this.showRoleLoading();  // Use existing method
      return;
    }

    // Story 3.5: Role data available, show role view
    this.showRoleView();

    // Render role display based on role_data
    if (state.role_data) {
      this.renderRoleDisplay(state.role_data);
    } else {
      // Show loading state if role_data not yet available
      this.showRoleLoading();
    }
  }

  /**
   * Show role view and hide other views (Story 3.5)
   */
  showRoleView() {
    const joinView = document.getElementById('join-view');
    const lobbyView = document.getElementById('lobby-view');
    const rolesLoadingView = document.getElementById('roles-loading-view');
    const roleView = document.getElementById('role-view');

    if (joinView) joinView.style.display = 'none';
    if (lobbyView) lobbyView.style.display = 'none';
    if (rolesLoadingView) rolesLoadingView.style.display = 'none';
    if (roleView) roleView.style.display = 'block';
  }

  /**
   * Show loading state during role assignment (Story 3.2 & 3.5: AC4)
   */
  showRoleLoading() {
    const joinView = document.getElementById('join-view');
    const lobbyView = document.getElementById('lobby-view');
    const rolesLoadingView = document.getElementById('roles-loading-view');
    const roleView = document.getElementById('role-view');

    if (joinView) joinView.style.display = 'none';
    if (lobbyView) lobbyView.style.display = 'none';
    if (roleView) roleView.style.display = 'none';
    if (rolesLoadingView) rolesLoadingView.style.display = 'block';

    // No need to render into roleView - using dedicated roles-loading-view container
    // This prevents duplicate loading states and maintains proper ARIA structure
  }

  /**
   * Render role display with spy parity (Story 3.5: AC1, AC2, AC3)
   * @param {Object} roleData - Per-player role information
   */
  renderRoleDisplay(roleData) {
    const roleView = document.getElementById('role-view');
    if (!roleView) return;

    // Prevent flicker - only update if data is complete (Story 3.5: AC4)
    if (!roleData || roleData.is_spy === undefined) {
      this.showRoleLoading();
      return;
    }

    if (roleData.is_spy) {
      this.renderSpyView(roleView, roleData);
    } else {
      this.renderInnocentView(roleView, roleData);
    }

    // Smooth fade-in transition (Story 3.5: AC4)
    roleView.classList.add('fade-in');
  }

  /**
   * Render non-spy role view (Story 3.5: AC1)
   * @param {HTMLElement} container
   * @param {Object} roleData - {location, role, hint, other_roles}
   */
  renderInnocentView(container, roleData) {
    const otherRolesHTML = roleData.other_roles
      .map(role => `<li>${this.escapeHtml(role)}</li>`)
      .join('');

    container.innerHTML = `
      <div class="role-display" data-role-type="innocent" role="region" aria-label="Your role assignment">
        <div class="role-display__header">
          <h2 class="role-display__location" aria-live="polite">${this.escapeHtml(roleData.location)}</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Your Role:</p>
          <h3 class="role-display__role-name">${this.escapeHtml(roleData.role)}</h3>
          <p class="role-display__hint">${this.escapeHtml(roleData.hint)}</p>
        </div>
        <div class="role-display__other-roles">
          <h4 class="role-display__list-title">Other Roles at This Location:</h4>
          <ul class="role-display__role-list">
            ${otherRolesHTML}
          </ul>
        </div>
      </div>
    `;
  }

  /**
   * Render spy role view (Story 3.5: AC2, AC3)
   * CRITICAL: IDENTICAL STRUCTURE to innocent view for spy parity
   * @param {HTMLElement} container
   * @param {Object} roleData - {possible_locations}
   */
  renderSpyView(container, roleData) {
    const locationsHTML = roleData.possible_locations
      .map(location => `<li>${this.escapeHtml(location)}</li>`)
      .join('');

    container.innerHTML = `
      <div class="role-display" data-role-type="spy" role="region" aria-label="Your role assignment">
        <div class="role-display__header">
          <h2 class="role-display__location role-display__location--spy" aria-live="polite">YOU ARE THE SPY</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Your Mission:</p>
          <h3 class="role-display__role-name">Blend In</h3>
          <p class="role-display__hint">Discover the location without revealing yourself</p>
        </div>
        <div class="role-display__other-roles">
          <h4 class="role-display__list-title">Possible Locations:</h4>
          <ul class="role-display__role-list">
            ${locationsHTML}
          </ul>
        </div>
      </div>
    `;
  }

  /**
   * Handle QUESTIONING phase state update (Story 4.4)
   * @param {Object} state - Game state with role_data and timer
   */
  handleQuestioningPhase(state) {
    // Prevent flicker - only update if data is complete
    if (!state.role_data || state.role_data.is_spy === undefined) {
      this.showLoadingState();
      return;
    }

    // Hide all other views
    const views = ['join-view', 'lobby-view', 'roles-loading-view', 'role-view', 'voting-view', 'reveal-view', 'scoring-view'];
    views.forEach(viewId => {
      const view = document.getElementById(viewId);
      if (view) view.style.display = 'none';
    });

    // Build role display HTML
    const roleDisplayHTML = state.role_data.is_spy
      ? this.buildSpyRoleDisplay(state.role_data)
      : this.buildInnocentRoleDisplay(state.role_data);

    // Get or create questioning view container in main content
    const mainContent = document.getElementById('main-content');
    if (!mainContent) return;

    // Remove existing questioning view if it exists
    let questioningView = document.getElementById('questioning-view');
    if (questioningView) {
      questioningView.remove();
    }

    // Story 4.3: Get turn info for display
    const turnInfoHTML = state.current_turn
      ? `<div id="turn-info-player" class="turn-info-compact card" style="margin-bottom: var(--space-lg); padding: var(--space-md); text-align: center;">
          <span id="questioner-name-player" class="name-highlight">${this.escapeHtml(state.current_turn.questioner.name)}</span>
          <span class="turn-text" style="color: var(--color-text-secondary); padding: 0 var(--space-sm);">asks</span>
          <span id="answerer-name-player" class="name-highlight">${this.escapeHtml(state.current_turn.answerer.name)}</span>
        </div>`
      : '';

    // Create new questioning view
    const viewHTML = `
      <div id="questioning-view" class="questioning-view">
        <!-- Timer Header -->
        <div class="timer-header">
          <div class="timer-display">
            <span class="timer-label">Time Remaining</span>
            <span class="timer-value" id="round-timer">--:--</span>
          </div>
        </div>

        <!-- Turn Info (Story 4.3) -->
        ${turnInfoHTML}

        <!-- Role Information -->
        <div class="role-info-container">
          ${roleDisplayHTML}
        </div>

        <!-- Call Vote Button -->
        <div class="vote-action">
          <button class="btn btn-primary" id="call-vote-btn">
            Call Vote
          </button>
        </div>
      </div>
    `;

    mainContent.insertAdjacentHTML('beforeend', viewHTML);

    // Start timer display
    if (state.timer !== undefined) {
      this.startTimerDisplay(state.timer);
    }

    // Attach event listeners
    this.attachQuestioningEventListeners();
  }

  /**
   * Build non-spy role display HTML (Story 4.4)
   * @param {Object} roleData - {location, role, hint, other_roles}
   * @returns {string} HTML string
   */
  buildInnocentRoleDisplay(roleData) {
    const otherRolesHTML = (roleData.other_roles || [])
      .map(role => `<li>${this.escapeHtml(role)}</li>`)
      .join('');

    return `
      <div class="role-display" data-role-type="innocent">
        <div class="role-display__header">
          <h2 class="role-display__location">${this.escapeHtml(roleData.location)}</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Your Role:</p>
          <h3 class="role-display__role-name">${this.escapeHtml(roleData.role)}</h3>
        </div>
        <div class="role-display__other-roles">
          <h4 class="role-display__list-title">Other Roles at This Location:</h4>
          <ul class="role-display__role-list">
            ${otherRolesHTML}
          </ul>
        </div>
      </div>
    `;
  }

  /**
   * Build spy role display HTML (Story 4.4)
   * CRITICAL: IDENTICAL STRUCTURE to innocent for spy parity
   * @param {Object} roleData - {possible_locations}
   * @returns {string} HTML string
   */
  buildSpyRoleDisplay(roleData) {
    const locationsHTML = (roleData.possible_locations || [])
      .map(location => `<li>${this.escapeHtml(location)}</li>`)
      .join('');

    return `
      <div class="role-display" data-role-type="spy">
        <div class="role-display__header">
          <h2 class="role-display__location role-display__location--spy">YOU ARE THE SPY</h2>
        </div>
        <div class="role-display__content">
          <p class="role-display__your-role">Possible Locations:</p>
        </div>
        <div class="role-display__other-roles">
          <ul class="role-display__role-list">
            ${locationsHTML}
          </ul>
        </div>
      </div>
    `;
  }

  /**
   * Show loading state (Story 4.4)
   */
  showLoadingState() {
    // Hide all views
    const views = ['join-view', 'lobby-view', 'role-view', 'questioning-view', 'voting-view', 'reveal-view', 'scoring-view'];
    views.forEach(viewId => {
      const view = document.getElementById(viewId);
      if (view) view.style.display = 'none';
    });

    // Show roles loading view
    const rolesLoadingView = document.getElementById('roles-loading-view');
    if (rolesLoadingView) {
      rolesLoadingView.style.display = 'block';
    }
  }

  /**
   * Start real-time timer display (Story 4.4)
   * @param {number} remainingSeconds - Initial timer value from server
   */
  startTimerDisplay(timerData) {
    // Story 4.2: Server is source of truth - display server-provided time
    // No client-side countdown needed (NFR5: server broadcasts every 1 second)
    const timerElement = document.getElementById('round-timer');
    if (!timerElement) return;

    // timerData is {name, remaining, total} from server (Story 4.2)
    const remaining = typeof timerData === 'object' ? timerData.remaining : timerData;

    // Update display immediately with server time
    this.updateTimerDisplay(timerElement, remaining);
  }

  /**
   * Update timer display with color states (Story 4.4)
   * @param {HTMLElement} element - Timer display element
   * @param {number} seconds - Remaining seconds
   */
  updateTimerDisplay(element, seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const display = `${minutes}:${secs.toString().padStart(2, '0')}`;

    element.textContent = display;

    // Add warning/critical states
    element.classList.remove('warning', 'critical');
    if (seconds <= 30 && seconds > 10) {
      element.classList.add('warning');
    } else if (seconds <= 10) {
      element.classList.add('critical');
    }
  }

  /**
   * Attach event listeners for questioning phase (Story 4.4)
   */
  attachQuestioningEventListeners() {
    const callVoteBtn = document.getElementById('call-vote-btn');
    if (callVoteBtn) {
      callVoteBtn.addEventListener('click', () => {
        this.handleCallVote();
      });
    }
  }

  /**
   * Handle "Call Vote" button click (Story 4.5)
   */
  handleCallVote() {
    // Disable button to prevent double-tap
    const button = document.getElementById('call-vote-btn');
    if (button) {
      button.disabled = true;
      button.textContent = 'Calling Vote...';
    }

    // Send call_vote message (Story 4.5)
    this.sendMessage({
      type: 'call_vote'
    });
  }

  /**
   * Cleanup timers on phase change (Story 4.4)
   */
  cleanup() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  /**
   * Escape HTML to prevent XSS (Story 3.5: Security)
   * @param {string} text
   * @returns {string}
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Send join request to server (Story 2.2)
   * @param {string} name - Player name
   */
  joinGame(name) {
    // SECURITY: Basic client-side validation (server will also validate)
    // Trim whitespace and validate length (1-20 characters)
    const trimmedName = name.trim();

    if (!trimmedName || trimmedName.length < 1 || trimmedName.length > 20) {
      this.showError('Please enter a name between 1-20 characters');
      return;
    }

    // Reject names with special characters that could enable XSS
    // Must match server-side regex exactly
    if (/[<>"'&;]/.test(trimmedName)) {
      this.showError('Name contains invalid characters');
      return;
    }

    this.sendMessage({
      type: 'join',
      name: trimmedName
    });
  }

  /**
   * Show lobby view (Story 2.2)
   */
  showLobby() {
    const joinView = document.getElementById('join-view');
    const lobbyView = document.getElementById('lobby-view');

    if (joinView) joinView.style.display = 'none';
    if (lobbyView) lobbyView.style.display = 'block';
  }

  /**
   * Update player list in lobby (Story 2.2)
   * @param {Array} players - Array of player objects
   */
  updatePlayerList(players) {
    const playerList = document.getElementById('player-list');
    if (!playerList) return;

    playerList.innerHTML = '';

    players.forEach(player => {
      const li = document.createElement('li');
      li.className = 'player-list-item';
      li.textContent = player.name;

      if (player.name === this.playerName) {
        li.classList.add('you');
      }

      if (!player.connected) {
        li.classList.add('disconnected');
      }

      playerList.appendChild(li);
    });
  }

  /**
   * Update player count display (Story 2.2)
   * @param {number} count - Number of players
   */
  updatePlayerCount(count) {
    const countElement = document.getElementById('lobby-player-count');
    if (countElement) {
      countElement.textContent = `${count} ${count === 1 ? 'player' : 'players'}`;
    }
  }

  /**
   * Render configuration display for players (Story 3.1)
   * @param {Object} config - Configuration object from state
   */
  renderConfigDisplay(config) {
    if (!config) return;

    const durationElement = document.getElementById('config-round-duration-display');
    const roundsElement = document.getElementById('config-num-rounds-display');
    const packElement = document.getElementById('config-location-pack-display');

    if (durationElement) {
      durationElement.textContent = config.round_duration_minutes;
    }

    if (roundsElement) {
      roundsElement.textContent = config.num_rounds;
    }

    if (packElement) {
      packElement.textContent = this.formatLocationPackName(config.location_pack);
    }

    console.log('[Player] Configuration displayed:', config);
  }

  /**
   * Format location pack ID for display (Story 3.1)
   * @param {string} packId - Location pack identifier
   * @returns {string} - Formatted pack name
   */
  formatLocationPackName(packId) {
    // Capitalize first letter
    return packId.charAt(0).toUpperCase() + packId.slice(1);
  }

  /**
   * Display error message in UI
   * @param {string} errorMessage - Error message to display
   */
  showError(errorMessage) {
    // Try error-message first (join view), then error-display (global)
    const errorElement = document.getElementById('error-message') || document.getElementById('error-display');
    if (errorElement) {
      errorElement.textContent = errorMessage;
      errorElement.style.display = 'block';
      if (errorElement.classList) {
        errorElement.classList.add('visible');
      }

      // Auto-hide after 5 seconds
      setTimeout(() => {
        errorElement.style.display = 'none';
        if (errorElement.classList) {
          errorElement.classList.remove('visible');
        }
      }, 5000);
    }
  }

  /**
   * Update connection status UI
   */
  updateConnectionUI() {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;

    const stateMap = {
      'disconnected': { text: 'Disconnected', class: 'status-error' },
      'connecting': { text: 'Connecting...', class: 'status-connecting' },
      'connected': { text: 'Connected', class: 'status-connected' },
      'error': { text: 'Connection Error', class: 'status-error' }
    };

    const state = stateMap[this.connectionState];
    statusElement.textContent = state.text;
    statusElement.className = `connection-status ${state.class}`;
  }

  /**
   * Send message to server via WebSocket
   * @param {Object} message - Message object
   */
  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('[Player] WebSocket not connected');
      this.showError('Not connected to server');
    }
  }

  /**
   * Start sending heartbeat messages to server (Story 2.4)
   */
  startHeartbeat() {
    // Clear any existing heartbeat timer
    this.stopHeartbeat();

    // Send heartbeat every 10 seconds
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({ type: 'heartbeat' });
        // PERFORMANCE FIX: Remove excessive logging (60 msgs/min with 10 players)
      }
    }, this.HEARTBEAT_INTERVAL);
  }

  /**
   * Stop sending heartbeat messages (Story 2.4)
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
      console.log('[Player] Heartbeat stopped');
    }
  }
}

// Global player client instance
let playerClient = null;


// ============================================================================
// STATE RENDERING
// ============================================================================

/**
 * Handle game state updates from server
 * @param {Object} message - Game state message
 */
function handleGameStateUpdate(message) {
  console.log('[Player] Game state update:', message);
  // TODO: Implement state-specific rendering in future stories
  // - Join: Name entry form
  // - Lobby: Waiting for host, player list
  // - Role Reveal: Location + Role OR Spy view
  // - Questioning: Timer, Q&A indicator, CALL VOTE button
  // - Voting: Player grid, bet selector, LOCK IT IN
  // - Reveal: Personal result, points change
  // - Scoring: Leaderboard, next round
}

/**
 * Render join view (placeholder)
 */
function renderJoin() {
  console.log('[Player] Rendering join view');
  // TODO: Display name entry form
}

/**
 * Render lobby state (placeholder)
 * @param {Object} state - Lobby state data
 */
function renderLobby(state) {
  console.log('[Player] Rendering lobby:', state);
  // TODO: Display "Waiting for host...", player list
}

/**
 * Render role reveal (Story 3.5 - IMPLEMENTED)
 * @param {Object} state - Role state
 */
function renderRoleReveal(state) {
  // This function is now handled by PlayerClient.renderRoleDisplay()
  // Called automatically when state.phase === 'ROLES'
  console.log('[Player] Role reveal handled by PlayerClient.handleRolesPhase');
}

/**
 * Render questioning phase (placeholder)
 * @param {Object} state - Questioning phase state
 */
function renderQuestioning(state) {
  console.log('[Player] Rendering questioning phase:', state);
  // TODO: Display timer, Q&A indicator, CALL VOTE button
}

/**
 * Render voting phase (placeholder)
 * @param {Object} state - Voting phase state
 */
function renderVoting(state) {
  console.log('[Player] Rendering voting phase:', state);
  // TODO: Display player grid, bet selector (1/2/ALL IN), LOCK IT IN
}

/**
 * Render reveal sequence (placeholder)
 * @param {Object} state - Reveal state
 */
function renderReveal(state) {
  console.log('[Player] Rendering reveal sequence:', state);
  // TODO: Display personal result, points change
}

/**
 * Render scoring/results (placeholder)
 * @param {Object} state - Scoring state
 */
function renderScoring(state) {
  console.log('[Player] Rendering scoring:', state);
  // TODO: Display leaderboard, round results
}

// ============================================================================
// TOUCH EVENT HANDLERS
// ============================================================================

/**
 * Handle player card tap for voting
 * @param {string} playerId - Selected player ID
 */
function handlePlayerSelect(playerId) {
  console.log('[Player] Player selected:', playerId);
  // TODO: Highlight selected player, enable bet selector
}

/**
 * Handle bet selection (1, 2, or ALL IN)
 * @param {number} betAmount - Confidence bet amount
 */
function handleBetSelect(betAmount) {
  console.log('[Player] Bet selected:', betAmount);
  // TODO: Highlight selected bet, enable LOCK IT IN button
}

/**
 * Handle vote submission
 */
function handleSubmitVote() {
  console.log('[Player] Submitting vote');
  // TODO: Send vote + bet to server, disable further interaction
  // sendMessage({
  //   type: 'vote',
  //   target: selectedPlayer,
  //   confidence: selectedBet
  // });
}

/**
 * Handle CALL VOTE button tap
 */
function handleCallVote() {
  console.log('[Player] Call vote triggered');
  // TODO: Send call_vote message to server
  // sendMessage({ type: 'call_vote' });
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
    console.warn(`[Player] Element not found: ${id}`);
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
 * Add CSS class to element
 * @param {string} id - Element ID
 * @param {string} className - Class name
 */
function addClass(id, className) {
  const element = getElement(id);
  if (element) {
    element.classList.add(className);
  }
}

/**
 * Remove CSS class from element
 * @param {string} id - Element ID
 * @param {string} className - Class name
 */
function removeClass(id, className) {
  const element = getElement(id);
  if (element) {
    element.classList.remove(className);
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize player UI on page load
 */
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Player] Initializing player UI');

  // Initialize player client
  playerClient = new PlayerClient();
  playerClient.connect();

  // Story 2.2: Setup join form handler
  const joinForm = document.getElementById('join-form');
  if (joinForm) {
    joinForm.addEventListener('submit', (event) => {
      event.preventDefault();

      const nameInput = document.getElementById('player-name-input');
      const joinButton = document.getElementById('join-button');
      const playerName = nameInput.value.trim();

      if (!playerName || playerName.length < 1 || playerName.length > 20) {
        playerClient.showError('Please enter a name between 1-20 characters');
        return;
      }

      // Validate no special characters (matches server validation)
      if (/[<>"'&;]/.test(playerName)) {
        playerClient.showError('Name contains invalid characters');
        return;
      }

      // Disable input while waiting for response
      nameInput.disabled = true;
      joinButton.disabled = true;

      // Send join request
      playerClient.joinGame(playerName);
    });
  }
});

// Story 4.4: Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (playerClient) {
    playerClient.cleanup();
  }
});
