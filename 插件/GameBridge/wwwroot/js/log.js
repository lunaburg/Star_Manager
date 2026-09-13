const ActivityLog = {
    maxEntries: 50,

    push(message) {
        const body = document.getElementById("log-console-body");
        if (!body) return;

        const now = new Date();
        const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

        const entry = document.createElement("div");
        entry.className = "log-entry";
        entry.innerHTML = `<span class="log-time">${time}</span><span class="log-msg">${escapeHtml(message)}</span>`;

        body.insertBefore(entry, body.firstChild);

        while (body.children.length > this.maxEntries) {
            body.removeChild(body.lastChild);
        }
    }
};