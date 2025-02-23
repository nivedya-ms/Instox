// Toggle Chatbot Widget
document.getElementById("chatbot-button").addEventListener("click", function () {
    document.getElementById("chatbot-widget").style.display = "block";
});

document.getElementById("close-chatbot").addEventListener("click", function () {
    document.getElementById("chatbot-widget").style.display = "none";
});

// Chatbot Interaction
document.getElementById("send-message").addEventListener("click", function () {
    const input = document.getElementById("chatbot-input").value;
    if (input.trim() === "") return;

    // Display user message
    const userMessage = document.createElement("div");
    userMessage.className = "message user";
    userMessage.textContent = "You: " + input;
    document.getElementById("chatbot-messages").appendChild(userMessage);

    // Simulate chatbot response
    const botMessage = document.createElement("div");
    botMessage.className = "message bot";
    botMessage.textContent = "Instox: I received your message: " + input;
    document.getElementById("chatbot-messages").appendChild(botMessage);

    // Clear input
    document.getElementById("chatbot-input").value = "";

    // Scroll to bottom
    document.getElementById("chatbot-messages").scrollTop = document.getElementById("chatbot-messages").scrollHeight;
});