const chatBox = document.getElementById("chat-box");
const answerInput = document.getElementById("answer-input");
const sendBtn = document.getElementById("send-btn");
const themeToggle = document.getElementById("theme-toggle");
const resetChatBtn = document.getElementById("reset-chat");
const downloadPdfBtn = document.getElementById("download-pdf");
const theme = document.body;

let lastAskedQuestion = ""; // 🔹 Son soruyu takip etmek için değişken

// ✅ Sohbeti Yükle
function loadConversation() {
    fetch("/get_conversation")
        .then(response => response.json())
        .then(data => {
            chatBox.innerHTML = "";

            let lastQuestion = ""; // 🔹 Son soruyu takip etmek için değişken
            data.forEach(item => {
                if (item.question !== lastQuestion) {
                    console.log("Önceki Konuşmadan Gelen Soru:", item.question); // Debugging Log
                    addMessage(item.question, "bot-message");
                }
                addMessage(item.answer, "user-message");
                lastQuestion = item.question; // Son soruyu kaydet
            });

            // 🔹 Eğer önceki sohbet yoksa, yeni soru iste
            if (data.length === 0) {
                console.log("Önceki sohbet yok, yeni soru isteniyor.");
                askNextQuestion();
            }
        });
}

// ✅ Yeni Soru İste
function askNextQuestion() {
    fetch("/get_question")
        .then(response => response.json())
        .then(data => {
            console.log("Yeni Soru İstendi:", data.question); // Debugging Log

            if (data.question && data.question !== lastAskedQuestion) {
                addMessage(data.question, "bot-message");
                lastAskedQuestion = data.question; // 🔹 Son soruyu güncelle
            } else {
                console.log("Aynı soru tekrar gelmedi:", data.question);
            }
        });
}

// ✅ Mesaj Ekle
function addMessage(text, className) {
    let messageDiv = document.createElement("div");
    messageDiv.className = `message ${className} fade-in`;
    messageDiv.innerText = text;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ✅ Mesaj Gönderme
sendBtn.addEventListener("click", () => {
    let answer = answerInput.value.trim();
    if (answer !== "") {
        addMessage(answer, "user-message");
        fetch("/submit_answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer: answer })
        }).then(() => {
            answerInput.value = "";
            askNextQuestion();
        });
    }
});

// ✅ Enter Tuşu ile Gönderme
answerInput.addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendBtn.click();
    }
});

// ✅ Sohbeti Sıfırla
resetChatBtn.addEventListener("click", function () {
    fetch("/reset_chat", { method: "POST" }).then(() => location.reload());
});

// ✅ PDF İndir
downloadPdfBtn.addEventListener("click", function () {
    fetch("/download_pdf", { method: "GET" })
        .then(response => response.blob())
        .then(blob => {
            const link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = "sohbet.pdf";
            link.click();
        });
});

// ✅ Dark/Light Mode
themeToggle.addEventListener("click", function () {
    if (theme.classList.contains("dark-mode")) {
        theme.classList.remove("dark-mode");
        theme.classList.add("light-mode");
        themeToggle.textContent = "🌙 Dark Mode";
    } else {
        theme.classList.remove("light-mode");
        theme.classList.add("dark-mode");
        themeToggle.textContent = "☀️ Light Mode";
    }
});

// ✅ Sayfa Yüklendiğinde
window.onload = function () {
    loadConversation(); // 🔹 Sadece geçmiş konuşmaları yükle
};