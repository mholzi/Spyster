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

    // Story 5.1: Vote state
    this.selectedVoteTarget = null;

    // Story 5.2: Confidence betting state (default to 1 per AC4)
    this.selectedConfidence = 1;

    // Story 5.3: Vote submission state
    this.hasVoted = false;

    // Story 5.4: Spy location guess state
    this.isSpy = false;
    this.selectedLocation = null;
    this.spyActionTaken = false;
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
    this.ws.onclose = (event) => this.onClose(event);
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
   * @param {CloseEvent} event - WebSocket close event
   */
  onClose(event) {
    console.log('[Player] WebSocket closed:', event.code, event.reason);
    this.connectionState = 'disconnected';
    this.updateConnectionUI();
    this.stopHeartbeat(); // Story 2.4: Stop heartbeat on disconnect

    // Don't reconnect if session was replaced by a new connection (code 4001)
    // This prevents infinite reconnect loops when multiple tabs/windows are open
    if (event.code === 4001) {
      console.log('[Player] Session replaced by new connection - not reconnecting');
      this.showError('Session replaced. Another device/tab connected with same name.');
      return;
    }

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

    // Story 5.1: Handle VOTE phase
    if (state.phase === 'VOTE') {
      this.handleVotePhase(state);
    }

    // Story 5.6: Handle REVEAL phase
    if (state.phase === 'REVEAL') {
      this.handleRevealPhase(state);
    }

    // Story 6.5: Handle SCORING phase
    if (state.phase === 'SCORING') {
      this.handleScoringPhase(state);
    }

    // Story 6.7: Handle END phase
    if (state.phase === 'END') {
      this.handleEndPhase(state);
    }
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

    // Story 8-3: Announce phase transition for screen readers (AC6)
    announceToScreenReader('Questioning phase started. Ask and answer questions to find the spy.', 'assertive');
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

    // Story 8-3: Announce timer at key intervals for screen readers (AC5)
    const announceAt = [60, 30, 10, 5, 3, 2, 1];
    if (announceAt.includes(seconds)) {
      const message = seconds === 1
        ? '1 second remaining'
        : `${seconds} seconds remaining`;
      announceToScreenReader(message, seconds <= 10 ? 'assertive' : 'polite');
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
   * Handle VOTE phase state update (Story 5.1)
   * @param {Object} state - Game state with players and vote data
   */
  handleVotePhase(state) {
    // Hide all other views
    const views = ['join-view', 'lobby-view', 'roles-loading-view', 'role-view', 'questioning-view', 'reveal-view', 'scoring-view'];
    views.forEach(viewId => {
      const view = document.getElementById(viewId);
      if (view) view.style.display = 'none';
    });

    // Show vote view
    const voteView = document.getElementById('vote-view');
    if (voteView) {
      voteView.style.display = 'flex';
    }

    // Show vote caller notification if available (from Story 4.5)
    if (state.vote_caller) {
      this.showVoteCallerNotification(state.vote_caller);
    }

    // Render player cards (AC1: Display grid of player cards)
    this.renderPlayerCards(state);

    // Update timer display
    if (state.timer) {
      this.updateVoteTimer(state.timer.remaining);
    }

    // Update vote tracker
    if (state.votes_submitted !== undefined && state.total_voters !== undefined) {
      this.updateVoteTracker(state.votes_submitted, state.total_voters);
    }

    // Story 5.2: Setup confidence betting
    this.setupConfidenceListeners();
    this.resetConfidence(); // Default to 1 per AC4

    // Story 5.3: Setup vote submission
    this.setupSubmitVoteListener();
    this.hasVoted = false;
    this.selectedVoteTarget = null;

    // Story 5.3: Check if player already voted (reconnect scenario)
    if (state.has_voted) {
      this.lockVoteUI();
    }

    // Story 5.4: Setup spy mode if player is spy (AC1, AC4)
    this.isSpy = state.is_spy || false;
    this.spyActionTaken = state.can_guess_location === false;

    const spyToggle = document.getElementById('spy-mode-toggle');
    if (spyToggle) {
      // AC4: Only spy sees the toggle
      spyToggle.style.display = this.isSpy ? 'block' : 'none';
    }

    // AC2: Render location list for spy
    if (this.isSpy && state.location_list) {
      this.renderLocationList(state.location_list);
      this.setupSpyModeListeners();
      this.setupSubmitGuessListener();
    }

    // Story 8-3: Announce phase transition for screen readers (AC6)
    announceToScreenReader('Voting phase started. Select a player you suspect is the spy.', 'assertive');
  }

  /**
   * Show vote caller notification (Story 5.1)
   * @param {string} callerName - Name of player who called vote
   */
  showVoteCallerNotification(callerName) {
    const notification = document.getElementById('vote-notification');
    if (!notification) return;

    notification.textContent = `${this.escapeHtml(callerName)} called a vote!`;
    notification.style.display = 'block';

    // Auto-hide after 3 seconds
    setTimeout(() => {
      notification.style.display = 'none';
    }, 3000);
  }

  /**
   * Render player cards grid (Story 5.1: AC1, AC2, AC3)
   * @param {Object} state - Game state with players array
   */
  renderPlayerCards(state) {
    const grid = document.getElementById('player-cards-grid');
    if (!grid) return;

    // Clear existing cards
    grid.innerHTML = '';

    // Get players from state (AC1: excluding themselves)
    const players = state.players || [];
    const selfName = this.playerName;

    players.forEach(player => {
      // Skip self - player cannot vote for themselves
      if (player.name === selfName) return;

      const card = this.createPlayerCard(player);
      grid.appendChild(card);
    });

    // Restore selection if player was previously selected
    if (this.selectedVoteTarget) {
      const selectedCard = grid.querySelector(`[data-player-name="${this.selectedVoteTarget}"]`);
      if (selectedCard && !selectedCard.disabled) {
        selectedCard.classList.add('player-card--selected');
        selectedCard.setAttribute('aria-checked', 'true');
      } else {
        // Clear selection if target no longer valid
        this.selectedVoteTarget = null;
        this.updateSubmitButton();
      }
    }
  }

  /**
   * Create a player card element (Story 5.1: AC1, AC5)
   * @param {Object} player - Player data {name, connected}
   * @returns {HTMLElement} Button element for player card
   */
  createPlayerCard(player) {
    const card = document.createElement('button');
    card.className = 'player-card';
    card.setAttribute('type', 'button');
    card.setAttribute('role', 'radio');
    card.setAttribute('aria-checked', 'false');
    card.setAttribute('data-player-name', player.name);

    // Card content with avatar and name
    const initial = player.name.charAt(0).toUpperCase();
    card.innerHTML = `
      <div class="player-card-avatar">
        <span class="player-initial">${this.escapeHtml(initial)}</span>
      </div>
      <div class="player-card-name">${this.escapeHtml(player.name)}</div>
    `;

    // Click handler for selection (AC2: tap to select)
    card.addEventListener('click', () => this.selectVoteTarget(player.name));

    // Handle disconnected players (AC5: disabled state)
    if (!player.connected) {
      card.classList.add('player-card--disabled');
      card.disabled = true;
      card.setAttribute('aria-disabled', 'true');
    }

    return card;
  }

  /**
   * Select a vote target (Story 5.1: AC2, AC3)
   * @param {string} playerName - Name of player to vote for
   */
  selectVoteTarget(playerName) {
    // AC3: Clear previous selection
    document.querySelectorAll('.player-card').forEach(card => {
      card.classList.remove('player-card--selected');
      card.setAttribute('aria-checked', 'false');
    });

    // AC2: Select new target
    const selectedCard = document.querySelector(`[data-player-name="${playerName}"]`);
    if (selectedCard) {
      selectedCard.classList.add('player-card--selected');
      selectedCard.setAttribute('aria-checked', 'true');
    }

    this.selectedVoteTarget = playerName;

    // Update submit button state
    this.updateSubmitButton();

    // Announce selection for screen readers
    this.announceSelection(playerName);

    console.log('[Player] Vote target selected:', playerName);
  }

  /**
   * Update submit button based on selection (Story 5.1)
   */
  updateSubmitButton() {
    const submitBtn = document.getElementById('submit-vote-btn');
    if (!submitBtn) return;

    if (this.selectedVoteTarget) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'LOCK IT IN';
    } else {
      submitBtn.disabled = true;
      submitBtn.textContent = 'SELECT A PLAYER';
    }
  }

  /**
   * Announce selection to screen readers (Story 5.1: Accessibility)
   * @param {string} playerName - Selected player name
   */
  announceSelection(playerName) {
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      announcer.textContent = `Selected ${playerName}`;
    }
  }

  /**
   * Select confidence level (Story 5.2: AC3, AC4, AC5)
   * @param {number} confidence - Confidence level (1, 2, or 3)
   */
  selectConfidence(confidence) {
    // Validate confidence value
    if (![1, 2, 3].includes(confidence)) {
      console.error('[Player] Invalid confidence value:', confidence);
      return;
    }

    // Update all buttons (radio group single-select behavior)
    document.querySelectorAll('.confidence-btn').forEach(btn => {
      const btnConfidence = parseInt(btn.dataset.confidence, 10);
      const isSelected = btnConfidence === confidence;

      btn.classList.toggle('confidence-btn--selected', isSelected);
      btn.setAttribute('aria-checked', isSelected.toString());
    });

    this.selectedConfidence = confidence;
    console.log('[Player] Confidence selected:', confidence);

    // Announce selection for screen readers
    const labels = { 1: 'Safe', 2: 'Bold', 3: 'All In' };
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      announcer.textContent = `Confidence set to ${labels[confidence]}`;
    }

    // Provide haptic feedback on mobile (if available)
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
  }

  /**
   * Reset confidence selection to default (Story 5.2: AC4)
   */
  resetConfidence() {
    this.selectConfidence(1);
  }

  /**
   * Get current vote data for submission (Story 5.2)
   * @returns {Object} Vote data with target and confidence
   */
  getVoteData() {
    return {
      target: this.selectedVoteTarget,
      confidence: this.selectedConfidence
    };
  }

  /**
   * Setup confidence button event listeners (Story 5.2)
   */
  setupConfidenceListeners() {
    document.querySelectorAll('.confidence-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const confidence = parseInt(e.currentTarget.dataset.confidence, 10);
        this.selectConfidence(confidence);
      });
    });
  }

  /**
   * Setup submit vote button listener (Story 5.3)
   */
  setupSubmitVoteListener() {
    const submitBtn = document.getElementById('submit-vote-btn');
    if (submitBtn && !submitBtn._hasListener) {
      submitBtn.addEventListener('click', () => this.submitVote());
      submitBtn._hasListener = true;
    }
  }

  /**
   * Submit vote to server (Story 5.3: AC1)
   */
  submitVote() {
    // Prevent double submission
    if (this.hasVoted) {
      console.log('[Player] Already voted');
      return;
    }

    // Validate selection
    if (!this.selectedVoteTarget) {
      console.warn('[Player] No vote target selected');
      return;
    }

    // Send vote message
    const voteData = {
      type: 'vote',
      target: this.selectedVoteTarget,
      confidence: this.selectedConfidence || 1
    };

    this.sendMessage(voteData);
    console.log('[Player] Vote submitted:', voteData);

    // Update UI immediately (optimistic)
    this.lockVoteUI();
  }

  /**
   * Lock vote UI after submission (Story 5.3: AC1)
   */
  lockVoteUI() {
    this.hasVoted = true;

    // Disable submit button and show locked state
    const submitBtn = document.getElementById('submit-vote-btn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'LOCKED ✓';
      submitBtn.classList.add('btn-locked');
    }

    // Disable player cards
    document.querySelectorAll('.player-card').forEach(card => {
      card.classList.add('player-card--locked');
      card.disabled = true;
    });

    // Disable confidence buttons
    document.querySelectorAll('.confidence-btn').forEach(btn => {
      btn.classList.add('confidence-btn--locked');
      btn.disabled = true;
    });

    // Announce for screen readers
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      announcer.textContent = 'Vote locked in';
    }

    console.log('[Player] Vote UI locked');
  }

  /**
   * Setup spy mode tab listeners (Story 5.4: AC1)
   */
  setupSpyModeListeners() {
    const voteTab = document.getElementById('spy-vote-tab');
    const guessTab = document.getElementById('spy-guess-tab');

    if (voteTab && !voteTab._hasListener) {
      voteTab.addEventListener('click', () => this.setSpyMode('vote'));
      voteTab._hasListener = true;
    }

    if (guessTab && !guessTab._hasListener) {
      guessTab.addEventListener('click', () => this.setSpyMode('guess'));
      guessTab._hasListener = true;
    }
  }

  /**
   * Switch between vote and guess panels (Story 5.4: AC1, AC2)
   * @param {string} mode - 'vote' or 'guess'
   */
  setSpyMode(mode) {
    const voteTab = document.getElementById('spy-vote-tab');
    const guessTab = document.getElementById('spy-guess-tab');
    const votePanel = document.getElementById('vote-panel');
    const guessPanel = document.getElementById('guess-panel');
    const confidenceSection = document.getElementById('confidence-section');
    const voteActions = document.querySelector('#vote-view > .vote-actions');

    if (mode === 'vote') {
      // Update tabs
      voteTab?.classList.add('spy-mode-tab--active');
      voteTab?.setAttribute('aria-selected', 'true');
      guessTab?.classList.remove('spy-mode-tab--active');
      guessTab?.setAttribute('aria-selected', 'false');

      // Show vote panel, hide guess panel
      if (votePanel) votePanel.style.display = 'block';
      if (guessPanel) guessPanel.style.display = 'none';
      if (confidenceSection) confidenceSection.style.display = 'block';
      if (voteActions) voteActions.style.display = 'block';
    } else if (mode === 'guess') {
      // Update tabs
      guessTab?.classList.add('spy-mode-tab--active');
      guessTab?.setAttribute('aria-selected', 'true');
      voteTab?.classList.remove('spy-mode-tab--active');
      voteTab?.setAttribute('aria-selected', 'false');

      // Show guess panel, hide vote panel
      if (votePanel) votePanel.style.display = 'none';
      if (guessPanel) guessPanel.style.display = 'block';
      if (confidenceSection) confidenceSection.style.display = 'none';
      if (voteActions) voteActions.style.display = 'none';
    }

    console.log('[Player] Spy mode set to:', mode);
  }

  /**
   * Render location list for spy (Story 5.4: AC2)
   * @param {Array} locations - Array of {id, name} objects
   */
  renderLocationList(locations) {
    const list = document.getElementById('location-list');
    if (!list) return;

    list.innerHTML = '';

    locations.forEach(location => {
      const item = document.createElement('button');
      item.className = 'location-item';
      item.setAttribute('type', 'button');
      item.setAttribute('role', 'radio');
      item.setAttribute('aria-checked', 'false');
      item.setAttribute('data-location-id', location.id);

      item.innerHTML = `<span class="location-name">${this.escapeHtml(location.name)}</span>`;

      item.addEventListener('click', () => this.selectLocation(location.id));
      list.appendChild(item);
    });

    console.log('[Player] Location list rendered:', locations.length, 'locations');
  }

  /**
   * Select a location for spy guess (Story 5.4: AC2)
   * @param {string} locationId - Location ID to select
   */
  selectLocation(locationId) {
    // Clear previous selection
    document.querySelectorAll('.location-item').forEach(item => {
      item.classList.remove('location-item--selected');
      item.setAttribute('aria-checked', 'false');
    });

    // Select new location
    const selectedItem = document.querySelector(`[data-location-id="${locationId}"]`);
    if (selectedItem) {
      selectedItem.classList.add('location-item--selected');
      selectedItem.setAttribute('aria-checked', 'true');
    }

    this.selectedLocation = locationId;

    // Update submit button
    this.updateGuessButton();

    // Announce for screen readers
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      const locationName = selectedItem?.textContent || locationId;
      announcer.textContent = `Selected ${locationName}`;
    }

    console.log('[Player] Location selected:', locationId);
  }

  /**
   * Update guess button based on selection (Story 5.4)
   */
  updateGuessButton() {
    const submitBtn = document.getElementById('submit-guess-btn');
    if (!submitBtn) return;

    if (this.selectedLocation) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'CONFIRM GUESS';
    } else {
      submitBtn.disabled = true;
      submitBtn.textContent = 'SELECT A LOCATION';
    }
  }

  /**
   * Setup submit guess button listener (Story 5.4)
   */
  setupSubmitGuessListener() {
    const submitBtn = document.getElementById('submit-guess-btn');
    if (submitBtn && !submitBtn._hasListener) {
      submitBtn.addEventListener('click', () => this.submitLocationGuess());
      submitBtn._hasListener = true;
    }
  }

  /**
   * Submit location guess (Story 5.4: AC3)
   */
  submitLocationGuess() {
    // Prevent double submission or submission without selection
    if (!this.selectedLocation || this.spyActionTaken) {
      console.log('[Player] Cannot submit guess - no selection or already acted');
      return;
    }

    // Send spy_guess message
    this.sendMessage({
      type: 'spy_guess',
      location_id: this.selectedLocation
    });

    console.log('[Player] Spy guess submitted:', this.selectedLocation);

    // Lock UI (AC5: mutual exclusivity)
    this.lockSpyGuessUI();
  }

  /**
   * Lock spy guess UI after submission (Story 5.4: AC3, AC5)
   */
  lockSpyGuessUI() {
    this.spyActionTaken = true;

    // Disable submit button
    const submitBtn = document.getElementById('submit-guess-btn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'GUESS LOCKED ✓';
      submitBtn.classList.add('btn-locked');
    }

    // Disable location items
    document.querySelectorAll('.location-item').forEach(item => {
      item.disabled = true;
      item.classList.add('location-item--locked');
    });

    // Disable spy mode tabs
    const voteTab = document.getElementById('spy-vote-tab');
    const guessTab = document.getElementById('spy-guess-tab');
    if (voteTab) voteTab.disabled = true;
    if (guessTab) guessTab.disabled = true;

    // Announce for screen readers
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      announcer.textContent = 'Location guess locked in';
    }

    console.log('[Player] Spy guess UI locked');
  }

  /**
   * Update vote tracker display (Story 5.3: AC2)
   * @param {number} submitted - Votes submitted count
   * @param {number} total - Total voters count
   */
  updateVoteTrackerSubmissions(submitted, total) {
    const tracker = document.getElementById('vote-tracker');
    if (!tracker) return;

    tracker.textContent = `${submitted}/${total} voted`;
    tracker.setAttribute('aria-valuenow', submitted);
    tracker.setAttribute('aria-valuemax', total);

    // Visual feedback when all voted
    if (submitted >= total) {
      tracker.classList.add('vote-tracker--complete');
    } else {
      tracker.classList.remove('vote-tracker--complete');
    }
  }

  /**
   * Update vote timer display with urgency states (Story 5.1 + 5.5)
   * @param {number} seconds - Remaining seconds
   */
  updateVoteTimer(seconds) {
    const timerElement = document.getElementById('vote-timer');
    if (!timerElement) return;

    // Format as M:SS
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    timerElement.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;

    // Update ARIA for screen readers
    timerElement.setAttribute('aria-valuenow', seconds);

    // Get timer container for styling
    const timerDisplay = timerElement.closest('.timer-display') || timerElement.parentElement;

    // Remove all urgency classes first
    timerElement.classList.remove('warning', 'critical');
    if (timerDisplay) {
      timerDisplay.classList.remove('timer-normal', 'timer-warning', 'timer-urgent');
    }

    // Apply urgency state (Story 5.5: AC2)
    if (seconds > 20) {
      if (timerDisplay) timerDisplay.classList.add('timer-normal');
    } else if (seconds > 10) {
      timerElement.classList.add('warning');
      if (timerDisplay) timerDisplay.classList.add('timer-warning');
    } else {
      timerElement.classList.add('critical');
      if (timerDisplay) timerDisplay.classList.add('timer-urgent');
    }

    // Announce urgency changes for screen readers (Story 5.5: AC6)
    if (seconds === 20 && !this._announced20) {
      this.announceToScreenReader('20 seconds remaining');
      this._announced20 = true;
    } else if (seconds === 10 && !this._announced10) {
      this.announceToScreenReader('10 seconds remaining - hurry!');
      this._announced10 = true;
    } else if (seconds === 5 && !this._announced5) {
      this.announceToScreenReader('5 seconds!');
      this._announced5 = true;
    }

    // Reset announcement flags on new vote phase
    if (seconds > 55) {
      this._announced20 = false;
      this._announced10 = false;
      this._announced5 = false;
    }

    // Handle timer expiry notification (Story 5.5: AC3, AC4)
    if (seconds <= 0 && !this.hasVoted && !this.spyActionTaken) {
      this.showAbstainNotification();
    }
  }

  /**
   * Announce message to screen readers (Story 5.5)
   * @param {string} message - Message to announce
   */
  announceToScreenReader(message) {
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      announcer.textContent = message;
    }
  }

  /**
   * Show abstain notification when timer expires (Story 5.5: AC3)
   */
  showAbstainNotification() {
    const notification = document.getElementById('vote-notification');
    if (notification) {
      notification.textContent = 'Time expired - you abstained from voting';
      notification.classList.add('notification--warning');
      notification.style.display = 'block';
    }
  }

  // ==========================================================================
  // STORY 5.6 & 5.7: REVEAL PHASE METHODS
  // ==========================================================================

  /**
   * Hide all game views (Story 5.6, 6.5, 6.7)
   */
  hideAllViews() {
    const views = [
      'join-view', 'lobby-view', 'roles-loading-view', 'role-view',
      'questioning-view', 'vote-view', 'reveal-view', 'scoring-view', 'end-view'
    ];
    views.forEach(viewId => {
      const view = document.getElementById(viewId);
      if (view) view.style.display = 'none';
    });
  }

  /**
   * Handle reveal phase (Story 5.6)
   * @param {Object} state - Game state object
   */
  handleRevealPhase(state) {
    // Hide all other views
    this.hideAllViews();

    const revealView = document.getElementById('reveal-view');
    if (revealView) {
      revealView.style.display = 'block';
    }

    // Story 5.7: Show conviction banner with score change
    this.showConvictionBanner(state);

    // Render vote cards
    if (state.votes) {
      this.renderVoteCards(state.votes);
    }

    // Show spy guess result if applicable
    if (state.spy_guess && state.spy_guess.guessed) {
      this.renderSpyGuessResult(state.spy_guess);
    }

    // Show convicted player
    if (state.vote_results) {
      this.renderConvictionResult(state.vote_results);
    }

    // Show actual spy
    if (state.actual_spy) {
      const spyEl = document.getElementById('actual-spy');
      if (spyEl) {
        spyEl.textContent = this.escapeHtml(state.actual_spy);

        // Highlight if current player is spy
        if (state.actual_spy === this.playerName) {
          spyEl.classList.add('reveal-spy-name--self');
        }
      }
    }

    // Show location
    if (state.location) {
      const locationEl = document.getElementById('actual-location');
      if (locationEl) {
        const locationName = typeof state.location === 'object'
          ? state.location.name
          : state.location;
        locationEl.textContent = this.escapeHtml(locationName || 'Unknown');
      }
    }

    // Start auto-transition countdown
    this.startScoringCountdown();

    console.log('[Player] Reveal phase displayed');
  }

  /**
   * Show conviction banner with outcome and score change (Story 5.7)
   * @param {Object} state - Game state with spy_caught, round_scores, etc.
   */
  showConvictionBanner(state) {
    const banner = document.getElementById('conviction-banner');
    const messageEl = document.getElementById('conviction-message');
    const detailEl = document.getElementById('conviction-detail');
    const scoreEl = document.getElementById('score-change');

    if (!banner) return;

    // Determine conviction outcome
    const convicted = state.vote_results?.convicted;
    const actualSpy = state.actual_spy;
    const spyCaught = state.spy_caught;

    // Remove existing variant classes
    banner.classList.remove(
      'conviction-banner--caught',
      'conviction-banner--innocent',
      'conviction-banner--none',
      'conviction-banner--spy-guess'
    );

    // Handle spy guess case (Story 5.7: AC4)
    if (state.spy_guess?.guessed) {
      banner.classList.add('conviction-banner--spy-guess');
      if (state.spy_guess.correct) {
        messageEl.textContent = 'Spy Guessed Correctly!';
        detailEl.textContent = `${this.escapeHtml(actualSpy)} identified the location`;
      } else {
        messageEl.textContent = 'Spy Guessed Wrong!';
        detailEl.textContent = `${this.escapeHtml(actualSpy)} failed to identify the location`;
      }
    } else if (convicted) {
      // Conviction case
      if (spyCaught) {
        // AC1: Spy was caught
        banner.classList.add('conviction-banner--caught');
        messageEl.textContent = 'Spy Caught!';
        detailEl.textContent = `${this.escapeHtml(convicted)} was the spy`;
      } else {
        // AC2: Innocent convicted
        banner.classList.add('conviction-banner--innocent');
        messageEl.textContent = 'Wrong Person!';
        detailEl.textContent = `${this.escapeHtml(convicted)} was innocent`;
      }
    } else {
      // AC5: No conviction (vote not unanimous - like real Spyfall)
      banner.classList.add('conviction-banner--none');
      messageEl.textContent = 'Spy Survives!';
      detailEl.textContent = 'Vote was not unanimous';
    }

    // Show player's score change (AC3)
    if (state.round_scores && this.playerName) {
      const myScore = state.round_scores[this.playerName];
      if (myScore) {
        const points = myScore.points || 0;
        if (points > 0) {
          scoreEl.textContent = `+${points}`;
          scoreEl.className = 'score-change score-positive';
        } else if (points < 0) {
          scoreEl.textContent = `${points}`;
          scoreEl.className = 'score-change score-negative';
        } else {
          scoreEl.textContent = '0';
          scoreEl.className = 'score-change score-neutral';
        }

        // Show breakdown details for debugging
        if (myScore.breakdown && myScore.breakdown.length > 0) {
          const breakdownText = myScore.breakdown
            .map(b => {
              if (b.type === 'vote') {
                return b.correct ? 'Correct vote' : 'Wrong vote';
              } else if (b.type === 'double_agent') {
                return 'Double Agent Bonus!';
              } else if (b.type === 'location_guess') {
                return b.correct ? 'Correct guess' : 'Wrong guess';
              }
              return b.type;
            })
            .join(', ');
          console.log('[Player] Score breakdown:', breakdownText);
        }
      } else {
        scoreEl.textContent = '';
        scoreEl.className = 'score-change';
      }
    }

    // Show banner with animation
    banner.style.display = 'block';
    banner.classList.add('conviction-banner--visible');

    // Announce for screen readers
    this.announceToScreenReader(messageEl.textContent);

    console.log('[Player] Conviction banner displayed:', {
      convicted,
      spyCaught,
      myScore: state.round_scores?.[this.playerName]
    });
  }

  /**
   * Render vote cards grid (Story 5.6: AC2)
   * @param {Array} votes - Array of vote objects
   */
  renderVoteCards(votes) {
    const grid = document.getElementById('reveal-votes-grid');
    if (!grid) return;

    grid.innerHTML = '';

    votes.forEach(vote => {
      const card = document.createElement('div');
      card.className = 'reveal-vote-card';

      if (vote.abstained) {
        card.classList.add('reveal-vote-card--abstained');
        card.innerHTML = `
          <div class="vote-voter">${this.escapeHtml(vote.voter)}</div>
          <div class="vote-arrow">→</div>
          <div class="vote-target vote-abstained">Abstained</div>
        `;
      } else {
        // Add confidence styling
        const confidenceClass = vote.confidence === 3
          ? 'confidence-all-in'
          : `confidence-${vote.confidence}`;
        card.classList.add(confidenceClass);

        const confidenceLabel = vote.confidence === 3 ? 'ALL IN' : vote.confidence;

        card.innerHTML = `
          <div class="vote-voter">${this.escapeHtml(vote.voter)}</div>
          <div class="vote-arrow">→</div>
          <div class="vote-target">${this.escapeHtml(vote.target || 'No target')}</div>
          <div class="vote-confidence">${confidenceLabel}</div>
        `;
      }

      grid.appendChild(card);
    });

    console.log('[Player] Vote cards rendered:', votes.length);
  }

  /**
   * Render spy guess result (Story 5.6: AC3)
   * @param {Object} spyGuess - Spy guess data
   */
  renderSpyGuessResult(spyGuess) {
    const container = document.getElementById('spy-guess-result');
    if (!container) return;

    container.style.display = 'block';

    const locationEl = document.getElementById('spy-guess-location');
    const outcomeEl = document.getElementById('spy-guess-outcome');

    if (locationEl) {
      locationEl.textContent = spyGuess.location_id;
    }

    if (outcomeEl) {
      if (spyGuess.correct) {
        outcomeEl.textContent = 'CORRECT!';
        outcomeEl.className = 'reveal-outcome reveal-outcome--correct';
      } else {
        outcomeEl.textContent = 'WRONG!';
        outcomeEl.className = 'reveal-outcome reveal-outcome--wrong';
      }
    }
  }

  /**
   * Render conviction result (Story 5.6: AC4)
   * @param {Object} voteResults - Vote results data
   */
  renderConvictionResult(voteResults) {
    const playerEl = document.getElementById('convicted-player');
    const countEl = document.getElementById('conviction-count');

    if (playerEl) {
      if (voteResults.convicted) {
        playerEl.textContent = this.escapeHtml(voteResults.convicted);
      } else {
        playerEl.textContent = 'No one convicted';
      }
    }

    if (countEl && voteResults.max_votes > 0) {
      countEl.textContent = `${voteResults.max_votes} vote${voteResults.max_votes > 1 ? 's' : ''}`;
    }
  }

  /**
   * Start countdown to scoring phase (Story 5.6)
   */
  startScoringCountdown() {
    const countdownEl = document.getElementById('scoring-countdown');
    let seconds = 5;

    // Clear any existing countdown
    if (this._scoringCountdownInterval) {
      clearInterval(this._scoringCountdownInterval);
    }

    this._scoringCountdownInterval = setInterval(() => {
      seconds--;
      if (countdownEl) {
        countdownEl.textContent = seconds.toString();
      }

      if (seconds <= 0) {
        clearInterval(this._scoringCountdownInterval);
        this._scoringCountdownInterval = null;
        // Server will transition to SCORING
      }
    }, 1000);
  }

  // ==========================================================================
  // STORY 6.5: SCORING PHASE METHODS
  // ==========================================================================

  /**
   * Handle SCORING phase state update (Story 6.5)
   * @param {Object} state - Game state with standings and round info
   */
  handleScoringPhase(state) {
    this.hideAllViews();

    const scoringView = document.getElementById('scoring-view');
    if (scoringView) {
      scoringView.style.display = 'block';
    }

    // Update round number
    this.updateRoundInfo(state);

    // Show personal score change
    this.showPersonalScore(state);

    // Render leaderboard
    this.renderLeaderboard(state.standings);

    // Start countdown to next round
    if (state.scoring_timer !== undefined) {
      this.startNextRoundCountdown(state.scoring_timer);
    }

    console.log('[Player] Scoring phase displayed');
  }

  /**
   * Show personal score prominently (Story 6.5: AC4)
   * @param {Object} state - Game state with standings
   */
  showPersonalScore(state) {
    const standings = state.standings || [];
    const myStanding = standings.find(s => s.is_self);

    if (!myStanding) return;

    const totalEl = document.getElementById('player-total-score');
    const changeEl = document.getElementById('player-round-change');

    if (totalEl) {
      totalEl.textContent = myStanding.score;
    }

    if (changeEl) {
      const change = myStanding.round_change || 0;
      const sign = change >= 0 ? '+' : '';
      changeEl.textContent = `${sign}${change}`;
      changeEl.className = `round-change ${change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'}`;
    }
  }

  /**
   * Render leaderboard list (Story 6.5: AC2, AC3)
   * @param {Array} standings - Array of player standings
   */
  renderLeaderboard(standings) {
    const list = document.getElementById('leaderboard-list');
    if (!list || !standings) return;

    list.innerHTML = '';

    standings.forEach((player, index) => {
      const rank = index + 1;
      const item = document.createElement('div');
      item.className = `leaderboard-item ${player.is_self ? 'leaderboard-item--self' : ''}`;

      // Top 3 styling
      if (rank <= 3) {
        item.classList.add(`leaderboard-item--rank-${rank}`);
      }

      const changeSign = (player.round_change || 0) >= 0 ? '+' : '';
      const changeClass = (player.round_change || 0) > 0 ? 'positive' : (player.round_change || 0) < 0 ? 'negative' : 'neutral';

      item.innerHTML = `
        <span class="leaderboard-rank">${rank}</span>
        <span class="leaderboard-name">${this.escapeHtml(player.name)}</span>
        <span class="leaderboard-score">${player.score}</span>
        <span class="leaderboard-change ${changeClass}">${changeSign}${player.round_change || 0}</span>
      `;

      list.appendChild(item);
    });
  }

  /**
   * Update round information display (Story 6.5)
   * @param {Object} state - Game state with round info
   */
  updateRoundInfo(state) {
    const roundEl = document.getElementById('scoring-round-number');
    if (roundEl && state.round_number) {
      roundEl.textContent = state.round_number;
    }
  }

  /**
   * Start countdown to next round (Story 6.5: AC6)
   * @param {number} seconds - Remaining seconds
   */
  startNextRoundCountdown(seconds) {
    const countdownEl = document.getElementById('scoring-countdown-value');
    const timerContainer = document.getElementById('next-round-timer');

    if (!countdownEl) return;

    // Show timer container
    if (timerContainer) {
      timerContainer.style.display = 'block';
    }

    // Clear any existing countdown
    if (this._nextRoundCountdownInterval) {
      clearInterval(this._nextRoundCountdownInterval);
    }

    let remaining = Math.ceil(seconds);
    countdownEl.textContent = remaining.toString();

    this._nextRoundCountdownInterval = setInterval(() => {
      remaining--;
      countdownEl.textContent = remaining.toString();

      if (remaining <= 0) {
        clearInterval(this._nextRoundCountdownInterval);
        this._nextRoundCountdownInterval = null;
        // Server will transition to next phase
      }
    }, 1000);
  }

  // ==========================================================================
  // STORY 6.7: END PHASE METHODS
  // ==========================================================================

  /**
   * Handle END phase state update (Story 6.7)
   * @param {Object} state - Game state with final standings and winner
   */
  handleEndPhase(state) {
    this.hideAllViews();

    const endView = document.getElementById('end-view');
    if (endView) {
      endView.style.display = 'block';
    }

    // Show winner
    this.showWinner(state);

    // Render final leaderboard
    this.renderFinalLeaderboard(state.standings || state.final_standings);

    // Show game stats if available
    if (state.game_stats) {
      this.showGameStats(state.game_stats);
    }

    console.log('[Player] End phase displayed');
  }

  /**
   * Show winner display (Story 6.7: AC1)
   * @param {Object} state - Game state with winner info
   */
  showWinner(state) {
    const nameEl = document.getElementById('winner-name');
    const scoreEl = document.getElementById('winner-score');
    const winnerCard = document.getElementById('winner-display');

    if (!nameEl || !state.winner) return;

    nameEl.textContent = this.escapeHtml(state.winner.name);

    if (scoreEl) {
      scoreEl.textContent = `${state.winner.score} points`;
    }

    // Highlight if current player won
    if (winnerCard && state.winner.name === this.playerName) {
      winnerCard.classList.add('winner-card--self');
    }

    // Handle tie (Story 6.7: AC2)
    if (state.winner.is_tie) {
      nameEl.textContent = state.winner.tied_players
        .map(p => this.escapeHtml(p))
        .join(' & ');
      if (winnerCard) {
        winnerCard.classList.add('winner-card--tie');
      }
    }
  }

  /**
   * Render final leaderboard (Story 6.7)
   * @param {Array} standings - Final standings array
   */
  renderFinalLeaderboard(standings) {
    const list = document.getElementById('final-leaderboard-list');
    if (!list || !standings) return;

    list.innerHTML = '';

    standings.forEach((player, index) => {
      const rank = index + 1;
      const item = document.createElement('div');
      item.className = `leaderboard-item ${player.is_self ? 'leaderboard-item--self' : ''}`;

      // Top 3 styling
      if (rank <= 3) {
        item.classList.add(`leaderboard-item--rank-${rank}`);
      }

      item.innerHTML = `
        <span class="leaderboard-rank">${rank}</span>
        <span class="leaderboard-name">${this.escapeHtml(player.name)}</span>
        <span class="leaderboard-score">${player.score}</span>
      `;

      list.appendChild(item);
    });
  }

  /**
   * Show game statistics (Story 6.7: optional)
   * @param {Object} stats - Game statistics
   */
  showGameStats(stats) {
    const statsContainer = document.getElementById('game-stats');
    const statsContent = document.getElementById('game-stats-content');

    if (!statsContainer || !statsContent) return;

    statsContainer.style.display = 'block';

    const statsHTML = [];

    if (stats.total_rounds) {
      statsHTML.push(`<div class="stat-item">Rounds played: ${stats.total_rounds}</div>`);
    }
    if (stats.spies_caught !== undefined) {
      statsHTML.push(`<div class="stat-item">Spies caught: ${stats.spies_caught}</div>`);
    }
    if (stats.perfect_guesses !== undefined) {
      statsHTML.push(`<div class="stat-item">Perfect spy guesses: ${stats.perfect_guesses}</div>`);
    }

    statsContent.innerHTML = statsHTML.join('');
  }

  /**
   * Update vote tracker display (Story 5.1)
   * @param {number} submitted - Votes submitted count
   * @param {number} total - Total voters count
   */
  updateVoteTracker(submitted, total) {
    const tracker = document.getElementById('vote-tracker');
    if (!tracker) return;

    tracker.textContent = `${submitted}/${total} voted`;
    tracker.setAttribute('aria-valuenow', submitted);
    tracker.setAttribute('aria-valuemax', total);
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
// STORY 8-3: KEYBOARD NAVIGATION SUPPORT
// ============================================================================

/**
 * Setup keyboard navigation for interactive elements (Story 8-3: AC2)
 * Enables arrow key navigation and Enter/Space activation for:
 * - Player cards in vote phase
 * - Confidence buttons
 * - Location items for spy guess
 */
function setupKeyboardNavigation() {
  console.log('[Player] Setting up keyboard navigation');

  // Global keyboard handler for navigation
  document.addEventListener('keydown', (event) => {
    const activeElement = document.activeElement;

    // Handle Enter/Space on focusable game elements
    if (event.key === 'Enter' || event.key === ' ') {
      if (activeElement.matches('.player-card, .confidence-btn, .location-item, .spy-mode-tab')) {
        event.preventDefault();
        activeElement.click();
        return;
      }
    }

    // Arrow key navigation within groups
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      // Find the parent container and all focusable siblings
      const containers = [
        { selector: '.player-cards-grid', items: '.player-card:not([disabled])' },
        { selector: '.confidence-buttons', items: '.confidence-btn:not([disabled])' },
        { selector: '.location-list', items: '.location-item:not([disabled])' },
        { selector: '.spy-mode-options', items: '.spy-mode-tab:not([disabled])' }
      ];

      for (const { selector, items } of containers) {
        const container = activeElement.closest(selector);
        if (container) {
          const focusableItems = Array.from(container.querySelectorAll(items));
          const currentIndex = focusableItems.indexOf(activeElement);

          if (currentIndex === -1) continue;

          let nextIndex = currentIndex;
          const isGrid = selector === '.player-cards-grid';
          const columnsPerRow = isGrid ? getGridColumns(container) : 1;

          switch (event.key) {
            case 'ArrowRight':
              nextIndex = Math.min(currentIndex + 1, focusableItems.length - 1);
              break;
            case 'ArrowLeft':
              nextIndex = Math.max(currentIndex - 1, 0);
              break;
            case 'ArrowDown':
              nextIndex = Math.min(currentIndex + columnsPerRow, focusableItems.length - 1);
              break;
            case 'ArrowUp':
              nextIndex = Math.max(currentIndex - columnsPerRow, 0);
              break;
          }

          if (nextIndex !== currentIndex && focusableItems[nextIndex]) {
            event.preventDefault();
            focusableItems[nextIndex].focus();
          }
          return;
        }
      }
    }

    // Escape key to deselect/cancel
    if (event.key === 'Escape') {
      // Blur current element if it's a game control
      if (activeElement.matches('.player-card, .confidence-btn, .location-item')) {
        activeElement.blur();
      }
    }
  });
}

/**
 * Get number of columns in a CSS grid container
 * @param {HTMLElement} container - Grid container element
 * @returns {number} Number of columns
 */
function getGridColumns(container) {
  const computedStyle = window.getComputedStyle(container);
  const gridTemplateColumns = computedStyle.getPropertyValue('grid-template-columns');
  // Count the number of column values (e.g., "1fr 1fr" = 2 columns)
  const columns = gridTemplateColumns.split(' ').filter(col => col.trim()).length;
  return Math.max(columns, 1);
}

/**
 * Announce message to screen readers via live region (Story 8-3: AC4)
 * @param {string} message - Message to announce
 * @param {string} priority - 'polite' or 'assertive'
 */
function announceToScreenReader(message, priority = 'polite') {
  // Find or create the live region
  let liveRegion = document.getElementById('sr-announcements');
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'sr-announcements';
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    document.body.appendChild(liveRegion);
  }

  // Set priority if different
  liveRegion.setAttribute('aria-live', priority);

  // Clear and set message (triggers announcement)
  liveRegion.textContent = '';
  setTimeout(() => {
    liveRegion.textContent = message;
  }, 100);
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

  // Story 8-3: Setup keyboard navigation
  setupKeyboardNavigation();

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
