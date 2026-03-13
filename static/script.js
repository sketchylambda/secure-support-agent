async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const message = inputField.value.trim();
    if (!message) return;

    // Add User Message to UI
    appendMessage(message, "user");
    inputField.value = "";

    try {
        // Send data to Python FastAPI backend
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        // Add AI Response to UI
        appendMessage(data.reply, "ai");

        // Update the Live Dashboard dynamically!
        document.getElementById("m-total").innerText = data.metrics.total;
        document.getElementById("m-blocked").innerText = data.metrics.blocked;
        document.getElementById("m-redacted").innerText = data.metrics.redacted;

    } catch (error) {
        appendMessage("System Error: Connection to secure backend failed.", "ai");
    }
}

function appendMessage(text, sender) {
    const chatHistory = document.getElementById("chat-history");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;
    msgDiv.innerText = text;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight; 
}

// Allow pressing "Enter" to send
document.getElementById("user-input").addEventListener("keypress", function(event) {
    if (event.key === "Enter") sendMessage();
});