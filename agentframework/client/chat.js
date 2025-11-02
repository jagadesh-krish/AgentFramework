'use strict';

(function () {
  const chatEl = document.getElementById('chat');
  const emptyEl = document.getElementById('empty');
  const formEl = document.getElementById('composer');
  const inputEl = document.getElementById('input');
  const sendBtn = document.getElementById('send');
  const statusEl = document.getElementById('status');

  /**
   * State
   */
  let ws = null;
  let connected = false;
  let thinkingIndicatorId = null;

  function wsUrl() {
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    return proto + '//' + loc.host + '/ws/chat';
  }

  function setStatus(text, isConnected = false) {
    const indicator = statusEl.querySelector('.status-indicator');
    if (indicator) {
      if (isConnected) {
        indicator.classList.add('connected');
      } else {
        indicator.classList.remove('connected');
      }
    }
    
    // Update text node (skip indicator and existing text)
    let textNode = null;
    for (let i = 0; i < statusEl.childNodes.length; i++) {
      const node = statusEl.childNodes[i];
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
        textNode = node;
        break;
      }
    }
    
    if (textNode) {
      textNode.textContent = ' ' + text;
    } else {
      // Add text node after indicator
      if (indicator && indicator.nextSibling) {
        indicator.nextSibling.textContent = ' ' + text;
      } else {
        statusEl.appendChild(document.createTextNode(' ' + text));
      }
    }
  }

  function connect() {
    try {
      ws = new WebSocket(wsUrl());
    } catch (e) {
      setStatus('Failed to create WebSocket');
      return;
    }

    setStatus('Connecting…');

    ws.onopen = () => {
      connected = true;
      setStatus('Connected', true);
      sendBtn.disabled = false;
    };

    ws.onclose = () => {
      connected = false;
      setStatus('Disconnected');
      sendBtn.disabled = false;
    };

    ws.onerror = () => {
      setStatus('Connection error');
    };

    ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (e) {
        data = { content: String(event.data) };
      }
      
      console.log('Message received:', data);
      
      // Remove thinking indicator if it exists
      removeThinkingIndicator();
      
      // Append assistant message
      appendMessage('assistant', data.content ?? '');
    };
  }

  function ensureConnected() {
    if (!ws || ws.readyState === WebSocket.CLOSED) connect();
  }

  function appendMessage(role, text, messageId = null) {
    if (emptyEl) emptyEl.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'msg ' + role;
    if (messageId) {
      row.setAttribute('data-msg-id', messageId);
    }

    const roleEl = document.createElement('div');
    roleEl.className = 'role';
    roleEl.textContent = role === 'user' ? 'U' : 'A';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    row.appendChild(roleEl);
    row.appendChild(bubble);
    chatEl.appendChild(row);
    chatEl.scrollTop = chatEl.scrollHeight;
    
    return row;
  }

  function showThinkingIndicator() {
    // Remove any existing thinking indicator
    removeThinkingIndicator();
    
    if (emptyEl) emptyEl.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'msg assistant thinking';
    row.id = 'thinking-indicator';

    const roleEl = document.createElement('div');
    roleEl.className = 'role';
    roleEl.textContent = 'A';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    const thinkingContainer = document.createElement('div');
    thinkingContainer.className = 'thinking';
    
    // Add dots first
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'thinking-dot';
      thinkingContainer.appendChild(dot);
    }
    
    // Add text after dots
    const thinkingText = document.createElement('span');
    thinkingText.className = 'thinking-text';
    thinkingText.textContent = 'Thinking...';
    thinkingContainer.appendChild(thinkingText);
    
    bubble.appendChild(thinkingContainer);
    row.appendChild(roleEl);
    row.appendChild(bubble);
    chatEl.appendChild(row);
    chatEl.scrollTop = chatEl.scrollHeight;
    
    thinkingIndicatorId = row.id;
    
    // Debug: log to console to verify it's showing
    console.log('Thinking indicator shown');
  }

  function removeThinkingIndicator() {
    const indicator = document.getElementById('thinking-indicator');
    if (indicator) {
      indicator.remove();
      thinkingIndicatorId = null;
      console.log('Thinking indicator removed');
    }
  }

  function sendMessage(text) {
    if (!text || !text.trim()) return;
    
    // Append user message
    appendMessage('user', text.trim());
    
    // Show thinking indicator
    showThinkingIndicator();

    ensureConnected();

    const payload = JSON.stringify({ type: 'TextMessage', content: text.trim() });

    const trySend = () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(payload);
      } else if (ws && ws.readyState === WebSocket.CONNECTING) {
        setTimeout(trySend, 60);
      } else {
        connect();
        setTimeout(trySend, 200);
      }
    };

    trySend();
  }

  formEl.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = inputEl.value;
    if (!text || !text.trim()) return;
    
    inputEl.value = '';
    sendBtn.disabled = true;
    sendMessage(text);
    
    // Re-enable button after a short delay
    setTimeout(() => {
      sendBtn.disabled = !connected;
    }, 300);
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      formEl.requestSubmit();
    }
  });

  // Auto-resize textarea
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  });

  // Initial connect
  connect();
})();
