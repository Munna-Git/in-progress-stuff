
const form = document.getElementById('chat-form');
const input = document.getElementById('query-input');
const chatContainer = document.getElementById('chat-container');

// State
let isProcessing = false;

// Auto-scroll to bottom
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Create message element
function createMessage(role, content, metadata = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Parse markdown for assistant, plain text for user
    if (role === 'assistant') {
        bubble.innerHTML = window.marked ? marked.parse(content) : content.replace(/\n/g, '<br>');
        
        // Add metadata if available
        if (metadata) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'metadata';
            
            // Confidence
            if (metadata.confidence) {
                const conf = Math.round(metadata.confidence * 100);
                const confSpan = document.createElement('span');
                confSpan.textContent = `Confidence: ${conf}%`;
                metaDiv.appendChild(confSpan);
            }
            
            // Products
            if (metadata.products_used && metadata.products_used.length > 0) {
                const prodSpan = document.createElement('span');
                prodSpan.textContent = `Products: ${metadata.products_used.length}`;
                prodSpan.title = metadata.products_used.join(', ');
                metaDiv.appendChild(prodSpan);
            }
            
            bubble.appendChild(metaDiv);
        }
    } else {
        bubble.textContent = content;
    }
    
    msgDiv.appendChild(bubble);
    return msgDiv;
}

// Show typing indicator
function showTyping() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant typing';
    msgDiv.id = 'typing-indicator';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `
        <div class="typing-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;
    
    msgDiv.appendChild(bubble);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

// Remove typing indicator
function removeTyping() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

// Handle submit
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = input.value.trim();
    if (!query || isProcessing) return;
    
    // UI Updates
    input.value = '';
    isProcessing = true;
    chatContainer.appendChild(createMessage('user', query));
    scrollToBottom();
    showTyping();
    
    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        if (!response.ok) throw new Error('API request failed');
        
        const data = await response.json();
        
        removeTyping();
        chatContainer.appendChild(createMessage('assistant', data.answer, data));
        
    } catch (error) {
        console.error('Error:', error);
        removeTyping();
        chatContainer.appendChild(createMessage('assistant', 'Sorry, I encountered an error connecting to the engine.'));
    } finally {
        isProcessing = false;
        scrollToBottom();
    }
});
