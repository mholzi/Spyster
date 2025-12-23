/**
 * Session Management Extension for Player Client (Story 2.3)
 * Handles token-based session restoration and URL management
 */

/**
 * Initialize player client with session management
 */
function initPlayerSession() {
  if (!window.playerClient) {
    console.error('[Player] PlayerClient not found');
    return;
  }

  // Add session properties
  playerClient.token = null;
  playerClient.playerName = null;
  playerClient.isHost = false;

  // Check for existing session token in URL
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');

  if (token) {
    // Attempt reconnection with token
    playerClient.token = token;
    connectWithToken(token);
  } else {
    // Show join screen
    showJoinScreen();
    // Connect for new session
    playerClient.connect();
  }
}

/**
 * Connect to WebSocket with session token
 * @param {string} token - Session token
 */
function connectWithToken(token) {
  playerClient.connectionState = 'connecting';
  playerClient.updateConnectionUI();

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/api/spyster/ws?token=${token}`;

  console.log('[Player] Connecting with token:', token.substring(0, 8) + '...');

  playerClient.ws = new WebSocket(wsUrl);

  playerClient.ws.onopen = () => {
    playerClient.onOpen();
  };

  playerClient.ws.onmessage = (event) => {
    handleSessionMessage(event);
  };

  playerClient.ws.onerror = (error) => {
    playerClient.onError(error);
  };

  playerClient.ws.onclose = () => {
    handleCloseWithToken();
  };
}

/**
 * Handle WebSocket close with token reconnection
 */
function handleCloseWithToken() {
  console.log('[Player] WebSocket closed');
  playerClient.connectionState = 'disconnected';
  playerClient.updateConnectionUI();
  playerClient.stopHeartbeat();

  if (playerClient.token) {
    // Attempt reconnection with same token
    if (playerClient.reconnectAttempts < playerClient.maxReconnectAttempts) {
      const delay = playerClient.reconnectDelay * Math.pow(2, playerClient.reconnectAttempts);
      console.log('[Player] Reconnecting with token in ' + delay + 'ms');

      setTimeout(() => {
        playerClient.reconnectAttempts++;
        connectWithToken(playerClient.token);
      }, delay);
    } else {
      console.error('[Player] Max reconnection attempts reached');
      playerClient.showError('Connection lost. Please reload the page.');
    }
  }
}

/**
 * Handle incoming WebSocket messages with session support
 * @param {MessageEvent} event - WebSocket message event
 */
function handleSessionMessage(event) {
  let message;
  try {
    message = JSON.parse(event.data);
  } catch (err) {
    console.error('[Player] Failed to parse server message:', err);
    return;
  }

  const messageType = message.type;

  // Handle session-specific messages
  if (messageType === 'session_restored') {
    handleSessionRestored(message);
    return;
  }

  if (messageType === 'join_confirmed') {
    handleJoinConfirmed(message);
    return;
  }

  if (messageType === 'error') {
    // Check for session errors
    if (message.code === 'INVALID_TOKEN' || message.code === 'SESSION_EXPIRED') {
      // Clear token and show join screen
      playerClient.token = null;
      window.history.replaceState({}, '', '/api/spyster/player');
      showJoinScreen();
    }
    playerClient.handleError(message);
    return;
  }

  if (messageType === 'state') {
    handleGameStateUpdate(message);
    return;
  }

  // Call original handler for other messages
  playerClient.onMessage(event);
}

/**
 * Handle session restored message
 * @param {Object} message - Session restored message
 */
function handleSessionRestored(message) {
  playerClient.playerName = message.name;
  playerClient.token = message.token;
  playerClient.isHost = message.is_host;
  console.log('[Player] Session restored: ' + playerClient.playerName);
  hideJoinScreen();
}

/**
 * Handle join confirmed message
 * @param {Object} message - Join confirmed message
 */
function handleJoinConfirmed(message) {
  playerClient.playerName = message.name;
  playerClient.token = message.token;
  playerClient.isHost = message.is_host;
  // Update URL with token
  window.history.replaceState({}, '', message.redirect_url);
  console.log('[Player] Joined as: ' + playerClient.playerName);
  hideJoinScreen();
}

/**
 * Join game with name
 * @param {string} name - Player name
 * @param {boolean} isHost - Whether this is the host
 */
function joinGame(name, isHost) {
  isHost = isHost || false;

  if (!playerClient.ws || playerClient.ws.readyState !== WebSocket.OPEN) {
    // Connect without token
    playerClient.connect();
    // Wait for connection then send join
    const openHandler = function() {
      playerClient.sendMessage({
        type: 'join',
        name: name,
        is_host: isHost
      });
      playerClient.ws.removeEventListener('open', openHandler);
    };
    playerClient.ws.addEventListener('open', openHandler);
  } else {
    // Already connected, send join
    playerClient.sendMessage({
      type: 'join',
      name: name,
      is_host: isHost
    });
  }
}

/**
 * Show join screen
 */
function showJoinScreen() {
  const joinScreen = document.getElementById('join-screen');
  const gameScreen = document.getElementById('game-screen');
  if (joinScreen) joinScreen.style.display = 'block';
  if (gameScreen) gameScreen.style.display = 'none';
}

/**
 * Hide join screen
 */
function hideJoinScreen() {
  const joinScreen = document.getElementById('join-screen');
  const gameScreen = document.getElementById('game-screen');
  if (joinScreen) joinScreen.style.display = 'none';
  if (gameScreen) gameScreen.style.display = 'block';
}

// Initialize session management when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Wait a bit for playerClient to be initialized
  setTimeout(() => {
    initPlayerSession();
  }, 100);
});
