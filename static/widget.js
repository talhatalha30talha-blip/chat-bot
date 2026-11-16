(function () {
  if (window.__RAG_WIDGET_LOADED__) return;
  window.__RAG_WIDGET_LOADED__ = true;

  const currentScript = document.currentScript || (function () {
    const scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  })();

  const API_BASE = currentScript && currentScript.src
    ? new URL(currentScript.src).origin
    : window.location.origin;

  const STORAGE_THREAD_KEY = "rag_widget_thread_id";
  const STORAGE_HISTORY_KEY = "rag_widget_chat_history";

  const urlParams = new URLSearchParams(window.location.search);
  const setupQueryRequested = urlParams.get("chatbot_setup") === "1";

  let threadId = localStorage.getItem(STORAGE_THREAD_KEY);
  if (!threadId) {
    threadId = "widget_" + Math.random().toString(36).substring(2, 11);
    localStorage.setItem(STORAGE_THREAD_KEY, threadId);
  }

  function loadSavedMessages() {
    try {
      const raw = localStorage.getItem(STORAGE_HISTORY_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (_) {}
    return [];
  }

  function saveMessages(messages) {
    try {
      localStorage.setItem(STORAGE_HISTORY_KEY, JSON.stringify(messages));
    } catch (_) {}
  }

  const host = document.createElement("div");
  host.id = "rag-chat-widget-host";
  document.body.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });

  let widgetState = {
    isOpen: setupQueryRequested,
    isConfigured: false,
    forceSetup: setupQueryRequested,
    botName: "AI Assistant",
    companyName: "",
    welcomeMessage: "Hi there! How can I help you today?",
    primaryColor: "#2563eb",
    isStreaming: false,
    messages: loadSavedMessages(),
  };

  function formatMarkdown(text) {
    const rawLines = (text || "").split(/\r?\n/);
    const output = [];
    let inList = false;

    const inlineFormat = (str) =>
      str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(
          /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
          '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );

    for (let rawLine of rawLines) {
      const trimmed = rawLine.trim();

      if (/^\|?[\s:-]+\|[\s|:-]*$/.test(trimmed)) {
        continue;
      }

      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        if (inList) {
          output.push("</ul>");
          inList = false;
        }
        const cells = trimmed
          .slice(1, -1)
          .split("|")
          .map((c) => c.trim())
          .filter(Boolean);
        if (cells.length > 0) {
          output.push(`<p style="margin:4px 0;">${inlineFormat(cells.join(" — "))}</p>`);
        }
        continue;
      }

      const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/);
      if (bulletMatch) {
        if (!inList) {
          output.push('<ul style="margin:6px 0;padding-left:18px;">');
          inList = true;
        }
        output.push(`<li style="margin-bottom:3px;">${inlineFormat(bulletMatch[1])}</li>`);
        continue;
      }

      if (inList) {
        output.push("</ul>");
        inList = false;
      }

      if (trimmed === "") {
        continue;
      }

      output.push(`<p style="margin:4px 0;">${inlineFormat(trimmed)}</p>`);
    }

    if (inList) {
      output.push("</ul>");
    }

    return output.join("");
  }

  function renderMessagesHTML() {
    const welcomeHTML = `<div class="msg bot">${formatMarkdown(widgetState.welcomeMessage)}</div>`;
    const historyHTML = widgetState.messages
      .map((m) =>
        m.role === "user"
          ? `<div class="msg user">${formatMarkdown(m.text)}</div>`
          : `<div class="msg bot">${formatMarkdown(m.text)}</div>`
      )
      .join("");
    return welcomeHTML + historyHTML;
  }

  function render() {
    const color = widgetState.primaryColor || "#2563eb";
    const showSetup = !widgetState.isConfigured || widgetState.forceSetup;

    shadow.innerHTML = `
      <style>
        :host {
          all: initial;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        * {
          box-sizing: border-box;
        }
        .launcher {
          position: fixed;
          bottom: 22px;
          right: 22px;
          width: 58px;
          height: 58px;
          border-radius: 50%;
          background: ${color};
          color: #ffffff;
          border: none;
          cursor: pointer;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2147483647;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .launcher:hover {
          transform: scale(1.06);
          box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
        }
        .setup-badge {
          position: absolute;
          top: -2px;
          right: -2px;
          width: 15px;
          height: 15px;
          background: #f59e0b;
          border: 2px solid #fff;
          border-radius: 50%;
        }
        .window {
          position: fixed;
          bottom: 92px;
          right: 22px;
          width: 380px;
          max-width: calc(100vw - 32px);
          height: 540px;
          max-height: calc(100vh - 115px);
          background: #ffffff;
          border-radius: 16px;
          box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
          display: ${widgetState.isOpen ? "flex" : "none"};
          flex-direction: column;
          overflow: hidden;
          z-index: 2147483647;
          border: 1px solid #e5e7eb;
        }
        .header {
          background: ${color};
          color: #ffffff;
          padding: 14px 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .header-title {
          font-size: 15px;
          font-weight: 600;
          margin: 0;
        }
        .header-sub {
          font-size: 11px;
          opacity: 0.88;
          margin-top: 2px;
        }
        .header-actions {
          display: flex;
          gap: 6px;
        }
        .icon-btn {
          background: rgba(255, 255, 255, 0.18);
          border: none;
          color: #fff;
          width: 28px;
          height: 28px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
        }
        .icon-btn:hover {
          background: rgba(255, 255, 255, 0.3);
        }

        /* Setup Wizard Styles */
        .setup-body {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          background: #f9fafb;
          font-size: 13px;
          color: #1f2937;
        }
        .setup-intro {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1e40af;
          padding: 10px 12px;
          border-radius: 10px;
          margin-bottom: 12px;
          font-size: 12px;
          line-height: 1.4;
        }
        .field {
          margin-bottom: 11px;
        }
        .field label {
          display: block;
          font-weight: 600;
          margin-bottom: 4px;
          font-size: 12px;
          color: #374151;
        }
        .field input[type="text"],
        .field input[type="password"],
        .field textarea {
          width: 100%;
          padding: 8px 10px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 13px;
          font-family: inherit;
          background: #fff;
        }
        .field textarea {
          resize: vertical;
          min-height: 62px;
        }
        .row-2 {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }
        .setup-btn {
          width: 100%;
          padding: 10px;
          background: ${color};
          color: #fff;
          border: none;
          border-radius: 10px;
          font-weight: 600;
          font-size: 13px;
          cursor: pointer;
          margin-top: 4px;
        }
        .setup-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .status-msg {
          margin-top: 8px;
          font-size: 12px;
          text-align: center;
          color: #dc2626;
        }

        /* Chat UI Styles */
        .messages {
          flex: 1;
          overflow-y: auto;
          padding: 14px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          background: #f9fafb;
        }
        .msg {
          max-width: 84%;
          padding: 10px 13px;
          border-radius: 14px;
          font-size: 13.5px;
          line-height: 1.45;
          word-wrap: break-word;
        }
        .msg.bot {
          align-self: flex-start;
          background: #ffffff;
          color: #111827;
          border: 1px solid #e5e7eb;
          border-bottom-left-radius: 4px;
        }
        .msg.user {
          align-self: flex-end;
          background: ${color};
          color: #ffffff;
          border-bottom-right-radius: 4px;
        }
        .input-bar {
          padding: 10px 12px;
          background: #ffffff;
          border-top: 1px solid #e5e7eb;
          display: flex;
          gap: 8px;
          align-items: center;
        }
        .input-bar input {
          flex: 1;
          padding: 9px 12px;
          border: 1px solid #d1d5db;
          border-radius: 20px;
          font-size: 13.5px;
          outline: none;
        }
        .input-bar input:focus {
          border-color: ${color};
        }
        .send-btn {
          background: ${color};
          color: #fff;
          border: none;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      </style>

      <!-- Floating Bottom-Right Bubble Button -->
      <button class="launcher" id="toggle-btn" aria-label="Open Chat">
        ${!widgetState.isConfigured ? '<span class="setup-badge" title="Setup required"></span>' : ""}
        ${
          widgetState.isOpen
            ? '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
            : '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
        }
      </button>

      <!-- Popup Widget Window -->
      <div class="window" id="chat-window">
        <div class="header">
          <div>
            <div class="header-title">${showSetup ? "Chatbot Knowledge Setup" : widgetState.botName}</div>
            <div class="header-sub">${showSetup ? "Admin Configuration (PIN Required)" : "Online • Ask anything"}</div>
          </div>
          <div class="header-actions">
            ${
              !showSetup && widgetState.messages.length > 0
                ? `<button class="icon-btn" id="new-session-btn" title="Start New Chat">↻</button>`
                : ""
            }
            ${
              widgetState.isConfigured && widgetState.forceSetup
                ? `<button class="icon-btn" id="back-chat-btn" title="Back to Chat">💬</button>`
                : ""
            }
            <button class="icon-btn" id="close-btn" title="Minimize">✕</button>
          </div>
        </div>

        ${
          showSetup
            ? `
          <form class="setup-body" id="setup-form">
            <div class="setup-intro">
              Add your website URLs, documents, or business info below to train your assistant.
            </div>

            <div class="row-2">
              <div class="field">
                <label>Setup PIN *</label>
                <input type="password" id="setup-pin" placeholder="e.g. 1234" required />
              </div>
              <div class="field">
                <label>Brand Color</label>
                <input type="color" id="setup-color" value="${color}" style="width:100%;height:34px;border:1px solid #d1d5db;border-radius:8px;padding:2px;" />
              </div>
            </div>

            <div class="row-2">
              <div class="field">
                <label>Company / Site Name</label>
                <input type="text" id="setup-company" placeholder="Acme Corp" value="${widgetState.companyName}" />
              </div>
              <div class="field">
                <label>Assistant Name</label>
                <input type="text" id="setup-botname" placeholder="Acme AI" value="${widgetState.botName}" />
              </div>
            </div>

            <div class="field">
              <label>Website URLs (one per line)</label>
              <textarea id="setup-urls" placeholder="https://yourwebsite.com&#10;https://yourwebsite.com/services"></textarea>
            </div>

            <div class="field">
              <label>Upload Documents (PDF, TXT, MD, CSV)</label>
              <input type="file" id="setup-files" multiple accept=".pdf,.txt,.md,.csv" />
            </div>

            <div class="field">
              <label>Additional Info / FAQs (Optional)</label>
              <textarea id="setup-text" placeholder="Paste business hours, pricing, contact info, or custom notes..."></textarea>
            </div>

            <button type="submit" class="setup-btn" id="setup-submit">Save & Train Chatbot</button>
            <div class="status-msg" id="setup-status"></div>
          </form>
        `
            : `
          <div class="messages" id="messages-box">
            ${renderMessagesHTML()}
          </div>
          <form class="input-bar" id="chat-form">
            <input type="text" id="chat-input" placeholder="Type your message..." autocomplete="off" />
            <button type="submit" class="send-btn" id="send-btn" aria-label="Send">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </form>
        `
        }
      </div>
    `;

    attachEvents();

    const messagesBox = shadow.getElementById("messages-box");
    if (messagesBox && widgetState.isOpen) {
      messagesBox.scrollTop = messagesBox.scrollHeight;
    }
  }

  function attachEvents() {
    const toggleBtn = shadow.getElementById("toggle-btn");
    const closeBtn = shadow.getElementById("close-btn");
    const backChatBtn = shadow.getElementById("back-chat-btn");
    const newSessionBtn = shadow.getElementById("new-session-btn");

    if (toggleBtn) {
      toggleBtn.onclick = () => {
        widgetState.isOpen = !widgetState.isOpen;
        render();
      };
    }

    if (closeBtn) {
      closeBtn.onclick = () => {
        widgetState.isOpen = false;
        render();
      };
    }

    if (backChatBtn) {
      backChatBtn.onclick = () => {
        widgetState.forceSetup = false;
        render();
      };
    }

    if (newSessionBtn) {
      newSessionBtn.onclick = () => {
        threadId = "widget_" + Math.random().toString(36).substring(2, 11);
        localStorage.setItem(STORAGE_THREAD_KEY, threadId);
        widgetState.messages = [];
        saveMessages([]);
        render();
      };
    }

    const setupForm = shadow.getElementById("setup-form");
    if (setupForm) {
      setupForm.onsubmit = async (e) => {
        e.preventDefault();
        const submitBtn = shadow.getElementById("setup-submit");
        const statusEl = shadow.getElementById("setup-status");

        const formData = new FormData();
        formData.append("pin", shadow.getElementById("setup-pin").value);
        formData.append("primary_color", shadow.getElementById("setup-color").value);
        formData.append("company_name", shadow.getElementById("setup-company").value || "our company");
        formData.append("bot_name", shadow.getElementById("setup-botname").value || "AI Assistant");
        formData.append("urls", shadow.getElementById("setup-urls").value);
        formData.append("raw_text", shadow.getElementById("setup-text").value);

        const filesInput = shadow.getElementById("setup-files");
        for (let i = 0; i < filesInput.files.length; i++) {
          formData.append("files", filesInput.files[i]);
        }

        submitBtn.disabled = true;
        submitBtn.textContent = "Training Chatbot... Please wait";
        statusEl.style.color = "#2563eb";
        statusEl.textContent = "Scraping & indexing your data into vector store...";

        try {
          const res = await fetch(`${API_BASE}/setup`, {
            method: "POST",
            body: formData,
          });
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || "Setup failed");
          }

          await fetchStatus();
          widgetState.forceSetup = false;
          render();
        } catch (err) {
          statusEl.style.color = "#dc2626";
          statusEl.textContent = err.message;
          submitBtn.disabled = false;
          submitBtn.textContent = "Save & Train Chatbot";
        }
      };
    }

    const chatForm = shadow.getElementById("chat-form");
    if (chatForm) {
      chatForm.onsubmit = async (e) => {
        e.preventDefault();
        if (widgetState.isStreaming) return;

        const inputEl = shadow.getElementById("chat-input");
        const sendBtn = shadow.getElementById("send-btn");
        const messagesBox = shadow.getElementById("messages-box");
        const userText = inputEl.value.trim();
        if (!userText) return;

        // Secret admin command to open reconfiguration screen (still PIN-protected)
        if (userText === "/setup") {
          inputEl.value = "";
          widgetState.forceSetup = true;
          render();
          return;
        }

        inputEl.value = "";
        widgetState.isStreaming = true;
        sendBtn.disabled = true;

        widgetState.messages.push({ role: "user", text: userText });
        saveMessages(widgetState.messages);

        const userDiv = document.createElement("div");
        userDiv.className = "msg user";
        userDiv.textContent = userText;
        messagesBox.appendChild(userDiv);

        const botDiv = document.createElement("div");
        botDiv.className = "msg bot";
        botDiv.textContent = "...";
        messagesBox.appendChild(botDiv);
        messagesBox.scrollTop = messagesBox.scrollHeight;

        let fullReply = "";

        try {
          const response = await fetch(`${API_BASE}/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userText, thread_id: threadId }),
          });

          if (!response.ok || !response.body) {
            throw new Error("Connection error");
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n\n");
            buffer = lines.pop();

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") continue;
                try {
                  const parsed = JSON.parse(payload);
                  if (parsed.token) {
                    fullReply += parsed.token;
                    botDiv.innerHTML = formatMarkdown(fullReply);
                    messagesBox.scrollTop = messagesBox.scrollHeight;
                  }
                } catch (_) {}
              }
            }
          }

          if (fullReply) {
            widgetState.messages.push({ role: "bot", text: fullReply });
            saveMessages(widgetState.messages);
          }
        } catch (err) {
          const errText = "Sorry, something went wrong connecting to the assistant.";
          botDiv.textContent = errText;
          widgetState.messages.push({ role: "bot", text: errText });
          saveMessages(widgetState.messages);
        } finally {
          widgetState.isStreaming = false;
          sendBtn.disabled = false;
          inputEl.focus();
        }
      };
    }
  }

  async function fetchStatus() {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (res.ok) {
        const data = await res.json();
        widgetState.isConfigured = Boolean(data.is_configured);
        widgetState.botName = data.bot_name || "AI Assistant";
        widgetState.companyName = data.company_name || "";
        widgetState.welcomeMessage = data.welcome_message || "Hi there! How can I help you today?";
        widgetState.primaryColor = data.primary_color || "#2563eb";
      }
    } catch (e) {
      console.warn("Widget status check failed:", e);
    }
  }

  fetchStatus().then(() => render());
})();