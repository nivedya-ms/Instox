document.addEventListener('DOMContentLoaded', () => {
    const chatbotButton = document.getElementById('chatbot-button');
    const chatbotWidget = document.getElementById('chatbot-widget');
    const closeButton = document.getElementById('close-chatbot');
    const chatMessages = document.getElementById('chatbot-messages');
    const chatInput = document.getElementById('chatbot-input');
    const sendButton = document.getElementById('send-message');



    if (chatbotButton && chatbotWidget) {
        // Toggle chatbot visibility
        chatbotButton.addEventListener('click', () => {
            chatbotWidget.classList.toggle('active');
        });
    } else {
        console.error('Chatbot button or widget not found!');
    }

    if (closeButton) {
        // Close chatbot widget
        closeButton.addEventListener('click', () => {
            chatbotWidget.classList.remove('active');
        });
    } else {
        console.warn('Close button not found!');
    }


    // Handle message sending
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message
        appendMessage("You: " + message, 'user');
        chatInput.value = '';

        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            if (data.reply) {
                appendMessage("Instox: " + data.reply, 'bot');
            } else if (data.error) {
                appendMessage(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error("Fetch error:", error);
            appendMessage('Failed to connect to chatbot service', 'error');
        }
    }

    // Message event handlers
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Helper function to append messages
    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = `
            <div class="message-content">
                ${text}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});