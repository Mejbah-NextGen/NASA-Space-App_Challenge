(function () {
  "use strict";

  if (window.lucide) window.lucide.createIcons();

  const navToggle = document.querySelector("[data-nav-toggle]");
  const publicMenu = document.querySelector("[data-public-menu]");
  const compactPublicNavigation = window.matchMedia("(max-width: 1199px)");

  function setPublicMenu(open, restoreFocus = true) {
    if (!navToggle || !publicMenu) return;
    const shouldOpen = compactPublicNavigation.matches && open;
    publicMenu.classList.toggle("open", shouldOpen);
    publicMenu.inert = compactPublicNavigation.matches && !shouldOpen;
    navToggle.setAttribute("aria-expanded", String(shouldOpen));
    if (!shouldOpen && restoreFocus && compactPublicNavigation.matches) navToggle.focus();
  }

  function syncPublicNavigation() {
    if (!navToggle || !publicMenu) return;
    if (compactPublicNavigation.matches) setPublicMenu(false, false);
    else {
      publicMenu.classList.remove("open");
      publicMenu.inert = false;
      navToggle.setAttribute("aria-expanded", "false");
    }
  }

  if (navToggle && publicMenu) {
    navToggle.addEventListener("click", () => {
      setPublicMenu(!publicMenu.classList.contains("open"), false);
    });
    publicMenu.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setPublicMenu(false, false)));
    compactPublicNavigation.addEventListener("change", syncPublicNavigation);
    syncPublicNavigation();
  }

  document.querySelectorAll(".sidebar-nav a").forEach((link) => {
    const path = link.dataset.path || link.getAttribute("href");
    if (path && (window.location.pathname === path || (path !== "/" && window.location.pathname.startsWith(path)))) {
      link.classList.add("active");
      link.setAttribute("aria-current", "page");
    }
  });

  document.addEventListener("click", (event) => {
    if (publicMenu?.classList.contains("open") && !publicMenu.contains(event.target) && !navToggle?.contains(event.target)) {
      setPublicMenu(false, false);
    }
    document.querySelectorAll("details.action-menu[open]").forEach((details) => {
      if (!details.contains(event.target)) details.removeAttribute("open");
    });
  });

  const workspaceNavigation = document.querySelector("[data-workspace-navigation]");
  const workspaceNavBackdrop = document.querySelector("[data-workspace-nav-backdrop]");
  const workspaceNavToggles = document.querySelectorAll("[data-workspace-nav-toggle]");
  const desktopWorkspaceNavigation = window.matchMedia("(min-width: 1200px)");
  let workspaceNavigationOpener = null;

  function setWorkspaceNavigation(open, restoreFocus = true) {
    if (!workspaceNavigation || !workspaceNavBackdrop) return;
    const shouldOpen = !desktopWorkspaceNavigation.matches && open;
    workspaceNavigation.classList.toggle("open", shouldOpen);
    workspaceNavigation.inert = !desktopWorkspaceNavigation.matches && !shouldOpen;
    workspaceNavigation.setAttribute("aria-hidden", String(!desktopWorkspaceNavigation.matches && !shouldOpen));
    workspaceNavBackdrop.hidden = !shouldOpen;
    workspaceNavToggles.forEach((button) => button.setAttribute("aria-expanded", String(shouldOpen)));
    document.body.classList.toggle("workspace-nav-open", shouldOpen);
    if (shouldOpen) workspaceNavigation.querySelector("a")?.focus();
    else if (restoreFocus && workspaceNavigationOpener) workspaceNavigationOpener.focus();
  }

  workspaceNavToggles.forEach((button) => {
    button.addEventListener("click", () => {
      workspaceNavigationOpener = button;
      setWorkspaceNavigation(!workspaceNavigation?.classList.contains("open"), false);
    });
  });
  workspaceNavBackdrop?.addEventListener("click", () => setWorkspaceNavigation(false));
  workspaceNavigation?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setWorkspaceNavigation(false, false));
  });
  desktopWorkspaceNavigation.addEventListener("change", () => setWorkspaceNavigation(false, false));
  setWorkspaceNavigation(false, false);

  const drawer = document.querySelector("[data-ai-drawer]");
  const backdrop = document.querySelector("[data-ai-backdrop]");
  const openButtons = document.querySelectorAll("[data-ai-open]");
  const closeButton = document.querySelector("[data-ai-close]");
  const messageBox = document.querySelector("[data-ai-messages]");
  const aiForm = document.querySelector("[data-ai-form]");
  let drawerOpener = null;

  function setDrawer(open, restoreFocus = true) {
    if (!drawer || !backdrop) return;
    drawer.classList.toggle("open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    drawer.inert = !open;
    openButtons.forEach((button) => button.setAttribute("aria-expanded", String(open)));
    backdrop.hidden = !open;
    document.body.style.overflow = open ? "hidden" : "";
    if (open) window.setTimeout(() => drawer.querySelector("textarea")?.focus(), 180);
    else if (restoreFocus && drawerOpener) drawerOpener.focus();
  }

  openButtons.forEach((button) => button.addEventListener("click", () => {
    drawerOpener = button;
    setDrawer(true, false);
  }));
  closeButton?.addEventListener("click", () => setDrawer(false));
  backdrop?.addEventListener("click", () => setDrawer(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setDrawer(false);
      setWorkspaceNavigation(false);
      setPublicMenu(false);
    }
    if (event.key === "Tab") {
      const activeContainer = drawer?.classList.contains("open")
        ? drawer
        : workspaceNavigation?.classList.contains("open")
          ? workspaceNavigation
          : null;
      if (!activeContainer) return;
      const focusable = Array.from(activeContainer.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )).filter((element) => !element.inert && element.getAttribute("aria-hidden") !== "true");
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

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
