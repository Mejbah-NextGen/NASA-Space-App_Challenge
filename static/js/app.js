(function () {
  "use strict";

  if (window.lucide) window.lucide.createIcons();

  const navToggle = document.querySelector("[data-nav-toggle]");
  const publicMenu = document.querySelector("[data-public-menu]");
  if (navToggle && publicMenu) {
    navToggle.addEventListener("click", () => {
      const open = publicMenu.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  document.querySelectorAll(".sidebar-nav a").forEach((link) => {
    const path = link.dataset.path || link.getAttribute("href");
    if (path && (window.location.pathname === path || (path !== "/" && window.location.pathname.startsWith(path)))) {
      link.classList.add("active");
      link.setAttribute("aria-current", "page");
    }
  });

  document.addEventListener("click", (event) => {
    document.querySelectorAll("details.action-menu[open]").forEach((details) => {
      if (!details.contains(event.target)) details.removeAttribute("open");
    });
  });

  const featureScroll = document.querySelector("[data-scroll-features]");
  if (featureScroll) {
    featureScroll.addEventListener("click", () => {
      const features = document.querySelector("#feature-navigation");
      if (features) features.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  const drawer = document.querySelector("[data-ai-drawer]");
  const backdrop = document.querySelector("[data-ai-backdrop]");
  const openButtons = document.querySelectorAll("[data-ai-open]");
  const closeButton = document.querySelector("[data-ai-close]");
  const messageBox = document.querySelector("[data-ai-messages]");
  const aiForm = document.querySelector("[data-ai-form]");

  function setDrawer(open) {
    if (!drawer || !backdrop) return;
    drawer.classList.toggle("open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    backdrop.hidden = !open;
    document.body.style.overflow = open ? "hidden" : "";
    if (open) window.setTimeout(() => drawer.querySelector("textarea")?.focus(), 180);
  }

  openButtons.forEach((button) => button.addEventListener("click", () => setDrawer(true)));
  closeButton?.addEventListener("click", () => setDrawer(false));
  backdrop?.addEventListener("click", () => setDrawer(false));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") setDrawer(false); });

  document.querySelectorAll("[data-ai-suggestions] button").forEach((button) => {
    button.addEventListener("click", () => {
      if (!aiForm) return;
      aiForm.elements.message.value = button.textContent.trim();
      aiForm.elements.message.focus();
    });
  });

  function appendMessage(text, role) {
    if (!messageBox) return null;
    const item = document.createElement("div");
    item.className = `ai-message ${role}`;
    item.textContent = text;
    messageBox.appendChild(item);
    messageBox.scrollTop = messageBox.scrollHeight;
    return item;
  }

  aiForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = aiForm.elements.message.value.trim();
    if (!message) return;
    const submit = aiForm.querySelector("button[type=submit]");
    appendMessage(message, "user");
    aiForm.elements.message.value = "";
    submit.disabled = true;
    const pending = appendMessage("Thinking…", "assistant");
    try {
      const response = await fetch(aiForm.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": aiForm.elements.csrfmiddlewaretoken.value },
        body: JSON.stringify({ message }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "The assistant is unavailable right now.");
      pending.textContent = data.response || data.message;
      if (data.mode === "fallback") pending.textContent += "\n\nBuilt-in guidance · no external AI provider was used.";
    } catch (error) {
      pending.classList.add("error");
      pending.textContent = error.message || "The assistant is unavailable right now.";
    } finally {
      submit.disabled = false;
      messageBox.scrollTop = messageBox.scrollHeight;
    }
  });
})();
