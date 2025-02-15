function updateFilters(type, value) {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set(type, value);
    window.location.search = urlParams.toString();
}

function toggleChat(chatId) {
    const content = document.getElementById(`chat-content-${chatId}`);
    if (content.style.display === 'none') {
        content.style.display = 'block';
    } else {
        content.style.display = 'none';
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
    });
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.innerHTML = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
} 