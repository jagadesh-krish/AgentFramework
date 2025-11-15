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
  let isProcessing = false;
  let currentAssistantMessage = null;
  let accumulatedText = '';
  let thinkingStepsContainer = null;

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
      
      // Handle error messages
      if (data.type === 'error') {
        removeThinkingIndicator();
        removeThinkingSteps();
        isProcessing = false;
        sendBtn.disabled = false;
        inputEl.disabled = false;
        console.warn('Error from server:', data.content);
        // Show error to user
        appendMessage('assistant', `⚠️ ${data.content}`);
        return;
      }
      
      // Handle thinking steps
      if (data.type === 'thinking_step') {
        console.log('Received thinking step:', data.step);
        handleThinkingStep(data.step);
        return;
      }
      
      const isStreaming = data.stream === true;
      const isDone = data.done === true;
      
      if (isStreaming) {
        // Handle streaming chunks
        if (isDone) {
          // Final chunk received - streaming complete
          removeThinkingIndicator();
          removeThinkingSteps();
          isProcessing = false;
          sendBtn.disabled = false;
          inputEl.disabled = false;
          
          // Update final message with full content if provided
          const fullContent = data.full_content || accumulatedText;
          if (currentAssistantMessage) {
            currentAssistantMessage.querySelector('.bubble').textContent = fullContent;
          }
          
          accumulatedText = '';
          currentAssistantMessage = null;
          thinkingStepsContainer = null;
          console.log('Streaming complete');
        } else {
          // Streaming chunk - accumulate text
          const chunk = data.content || '';
          accumulatedText += chunk;
          
          // Remove thinking indicator on first chunk (but keep steps visible briefly)
          if (thinkingIndicatorId) {
            // Clear steps first, then remove indicator
            removeThinkingSteps();
            removeThinkingIndicator();
          }
          
          // Create or update assistant message
          if (!currentAssistantMessage) {
            currentAssistantMessage = appendMessage('assistant', accumulatedText);
          } else {
            currentAssistantMessage.querySelector('.bubble').textContent = accumulatedText;
            chatEl.scrollTop = chatEl.scrollHeight;
          }
        }
      } else {
        // Non-streaming response (fallback)
        removeThinkingIndicator();
        removeThinkingSteps();
        isProcessing = false;
        sendBtn.disabled = false;
        inputEl.disabled = false;
        
        // Append assistant message
        appendMessage('assistant', data.content ?? '');
      }
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
    // Remove any existing thinking indicator first
    removeThinkingIndicator();
    
    if (emptyEl) emptyEl.style.display = 'none';

    // Create the thinking indicator row
    const row = document.createElement('div');
    row.className = 'msg assistant thinking';
    row.id = 'thinking-indicator';
    row.setAttribute('data-thinking', 'true');

    // Create role indicator
    const roleEl = document.createElement('div');
    roleEl.className = 'role';
    roleEl.textContent = 'A';

    // Create message bubble
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Create thinking container - make it more compact
    const thinkingContainer = document.createElement('div');
    thinkingContainer.className = 'thinking';
    thinkingContainer.style.display = 'flex';
    thinkingContainer.style.alignItems = 'center';
    thinkingContainer.style.gap = '8px';
    
    // Add animated dots first
    const dotsContainer = document.createElement('div');
    dotsContainer.style.display = 'flex';
    dotsContainer.style.gap = '4px';
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'thinking-dot';
      dotsContainer.appendChild(dot);
    }
    thinkingContainer.appendChild(dotsContainer);
    
    // Add thinking text after dots
    const thinkingText = document.createElement('span');
    thinkingText.className = 'thinking-text';
    thinkingText.textContent = 'AI is thinking...';
    thinkingContainer.appendChild(thinkingText);
    
    // Create container for thinking steps (will be added below the thinking text)
    const stepsList = document.createElement('div');
    stepsList.className = 'thinking-steps-list-inline';
    stepsList.id = 'thinking-steps-list-inline';
    stepsList.style.display = 'none'; // Hide until steps are added
    
    // Assemble the message bubble
    bubble.appendChild(thinkingContainer);
    bubble.appendChild(stepsList);
    row.appendChild(roleEl);
    row.appendChild(bubble);
    
    // Add to chat container
    chatEl.appendChild(row);
    
    // Store reference to steps list
    thinkingStepsContainer = stepsList;
    
    // Scroll to bottom to show the indicator
    chatEl.scrollTop = chatEl.scrollHeight;
    
    thinkingIndicatorId = row.id;
    
    // Force a reflow to ensure animation starts
    void row.offsetHeight;
    
    console.log('Thinking indicator shown');
  }

  function removeThinkingIndicator() {
    const indicator = document.getElementById('thinking-indicator');
    if (indicator) {
      // Add fade out animation
      indicator.style.opacity = '0';
      indicator.style.transition = 'opacity 0.3s ease-out';
      
      setTimeout(() => {
        indicator.remove();
        thinkingIndicatorId = null;
      }, 300);
      
      console.log('Thinking indicator removed');
    } else {
      thinkingIndicatorId = null;
    }
  }

  function handleThinkingStep(step) {
    console.log('Handling thinking step:', step);
    
    // Ensure thinking indicator exists (it should be created when message is sent)
    if (!thinkingIndicatorId) {
      showThinkingIndicator();
    }
    
    // Get or create thinking steps container from the thinking indicator
    if (!thinkingStepsContainer) {
      const indicator = document.getElementById('thinking-indicator');
      if (indicator) {
        const stepsList = indicator.querySelector('.thinking-steps-list-inline');
        if (stepsList) {
          thinkingStepsContainer = stepsList;
        } else {
          // Create it if it doesn't exist
          const bubble = indicator.querySelector('.bubble');
          if (bubble) {
            const stepsList = document.createElement('div');
            stepsList.className = 'thinking-steps-list-inline';
            stepsList.id = 'thinking-steps-list-inline';
            bubble.appendChild(stepsList);
            thinkingStepsContainer = stepsList;
          }
        }
      }
    }
    
    if (!thinkingStepsContainer) {
      console.warn('Could not find thinking steps container');
      return;
    }
    
    // Show the steps list when first step is added
    if (thinkingStepsContainer.style.display === 'none' || thinkingStepsContainer.children.length === 0) {
      thinkingStepsContainer.style.display = 'flex';
    }
    
    // Add step to the list
    const stepEl = document.createElement('div');
    stepEl.className = `thinking-step-inline thinking-step-${step.status}`;
    
    let stepContent = '';
    if (step.type === 'function_call' && step.function_name) {
      stepContent = `
        <div class="thinking-step-icon-inline">🔧</div>
        <div class="thinking-step-content-inline">
          <div class="thinking-step-title-inline">Calling ${step.function_name}</div>
          ${step.arguments && step.arguments !== 'N/A' ? `<div class="thinking-step-details-inline">Arguments: ${step.arguments}</div>` : ''}
          ${step.result ? `<div class="thinking-step-result-inline">Result: ${step.result}</div>` : ''}
        </div>
        <div class="thinking-step-status-inline ${step.status}">${step.status === 'calling' ? '⏳' : '✓'}</div>
      `;
    } else if (step.type === 'function_call' && step.result) {
      // Function result without function name
      stepContent = `
        <div class="thinking-step-icon-inline">✓</div>
        <div class="thinking-step-content-inline">
          <div class="thinking-step-title-inline">Function completed</div>
          <div class="thinking-step-result-inline">Result: ${step.result}</div>
        </div>
        <div class="thinking-step-status-inline completed">✓</div>
      `;
    } else if (step.type === 'ai_thinking') {
      stepContent = `
        <div class="thinking-step-icon-inline">🤖</div>
        <div class="thinking-step-content-inline">
          <div class="thinking-step-title-inline">${step.message || 'Processing...'}</div>
        </div>
        <div class="thinking-step-status-inline ${step.status}">${step.status === 'thinking' ? '⏳' : '✓'}</div>
      `;
    }
    
    if (!stepContent) {
      console.warn('No content generated for thinking step:', step);
      return;
    }
    
    stepEl.innerHTML = stepContent;
    
    // Use function_id if available, otherwise use function_name for matching
    const stepKey = step.function_id || step.function_name;
    
    // Set data attribute for matching
    if (stepKey) {
      stepEl.setAttribute('data-function', stepKey);
    }
    
    // Update existing step if it's the same function
    // For function results, try to find the matching calling step
    if (stepKey) {
      const existingStep = thinkingStepsContainer.querySelector(`[data-function="${stepKey}"]`);
      if (existingStep) {
        // Update the existing step
        existingStep.outerHTML = stepEl.outerHTML;
      } else {
        // New step, add it
        thinkingStepsContainer.appendChild(stepEl);
      }
    } else if (step.status === 'completed' && step.result) {
      // For completed steps without a key, try to find the last "calling" step
      const lastCallingStep = thinkingStepsContainer.querySelector('.thinking-step-calling');
      if (lastCallingStep) {
        // Update the last calling step to show it's completed
        lastCallingStep.outerHTML = stepEl.outerHTML;
      } else {
        // No matching step found, add as new
        thinkingStepsContainer.appendChild(stepEl);
      }
    } else {
      thinkingStepsContainer.appendChild(stepEl);
    }
    
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function removeThinkingSteps() {
    // Clear inline thinking steps from the thinking indicator
    if (thinkingStepsContainer) {
      thinkingStepsContainer.innerHTML = '';
      thinkingStepsContainer = null;
    }
    // Also check if there's a separate container (legacy)
    const container = document.getElementById('thinking-steps-container');
    if (container) {
      container.style.opacity = '0';
      container.style.transition = 'opacity 0.3s ease-out';
      setTimeout(() => {
        container.remove();
      }, 300);
    }
  }

  function sendMessage(text) {
    if (!text || !text.trim()) return;
    
    // Block if already processing
    if (isProcessing) {
      console.log('Message blocked: already processing');
      return;
    }
    
    // Set processing state
    isProcessing = true;
    sendBtn.disabled = true;
    inputEl.disabled = true;
    accumulatedText = '';
    currentAssistantMessage = null;
    thinkingStepsContainer = null;
    
    // Append user message
    appendMessage('user', text.trim());
    
    // Show thinking indicator
    console.log('Sending message, showing indicator');
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
    
    // Block if already processing
    if (isProcessing) {
      return;
    }
    
    inputEl.value = '';
    sendMessage(text);
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
