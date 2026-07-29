(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("chat-form");
    var input = document.getElementById("chat-input");
    var log = document.getElementById("chat-log");
    var status = document.getElementById("chat-status");
    if (!form || !input || !log) return;

    function addMessage(role, text, productCards) {
      var wrapper = document.createElement("div");
      wrapper.className = "chat-message chat-" + role;

      if (role === "assistant" && window.ASSISTANT_NAME) {
        var name = document.createElement("p");
        name.className = "chat-name";
        name.textContent = window.ASSISTANT_NAME;
        wrapper.appendChild(name);
      }

      if (text) {
        var bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        bubble.textContent = text;
        wrapper.appendChild(bubble);
      }

      (productCards || []).forEach(function (html) {
        var card = document.createElement("div");
        card.className = "product-card-chat-wrap";
        card.innerHTML = html;
        wrapper.appendChild(card);
      });

      log.appendChild(wrapper);
      log.scrollTop = log.scrollHeight;
      return wrapper;
    }

    function setStatus(text) {
      if (!status) return;
      status.textContent = text;
      status.hidden = !text;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var message = input.value.trim();
      if (!message) return;

      addMessage("user", message);
      input.value = "";
      input.disabled = true;
      setStatus("Thinking...");

      fetch(form.action || window.location.pathname.replace(/\/$/, "") + "/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message }),
      })
        .then(function (response) {
          return response.json().then(function (data) {
            return { ok: response.ok, data: data };
          });
        })
        .then(function (result) {
          if (result.ok) {
            addMessage("assistant", result.data.reply, result.data.products);
          } else {
            addMessage("assistant", result.data.error || "Something went wrong - please try again.");
          }
        })
        .catch(function () {
          addMessage("assistant", "Couldn't reach the assistant - check your connection and try again.");
        })
        .finally(function () {
          input.disabled = false;
          setStatus("");
          input.focus();
        });
    });
  });
})();
