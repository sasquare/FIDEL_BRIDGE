// Lightweight polling for "real-time" chat updates - no websockets needed
// for an MVP message volume. Polls every 4s for messages newer than the
// last one already on the page and appends them without a full reload.
(function () {
  const script = document.currentScript;
  const pollUrl = script.getAttribute("data-poll-url");
  const list = document.getElementById("message-list");
  if (!pollUrl || !list) return;

  function scrollToBottom() {
    list.scrollTop = list.scrollHeight;
  }

  function renderMessage(message) {
    const wrapper = document.createElement("div");
    wrapper.className = "flex " + (message.is_own ? "justify-end" : "justify-start");

    const bubble = document.createElement("div");
    bubble.className =
      "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm " +
      (message.is_own ? "bg-brand-700 text-white" : "bg-slate-100 text-slate-700");

    const body = document.createElement("p");
    body.className = "whitespace-pre-line";
    body.textContent = message.body;

    const timestamp = document.createElement("p");
    timestamp.className =
      "mt-1 text-right text-[10px] " + (message.is_own ? "text-brand-200" : "text-slate-400");
    timestamp.textContent = message.created_at;

    bubble.appendChild(body);
    bubble.appendChild(timestamp);
    wrapper.appendChild(bubble);
    list.appendChild(wrapper);
  }

  function poll() {
    const lastId = list.getAttribute("data-last-id") || "0";
    fetch(pollUrl + "?since=" + lastId, { headers: { Accept: "application/json" } })
      .then((response) => (response.ok ? response.json() : []))
      .then((messages) => {
        if (!messages.length) return;
        messages.forEach(renderMessage);
        list.setAttribute("data-last-id", messages[messages.length - 1].id);
        scrollToBottom();
      })
      .catch(() => {
        /* transient network errors are fine to ignore for a background poll */
      });
  }

  scrollToBottom();
  setInterval(poll, 4000);
})();
