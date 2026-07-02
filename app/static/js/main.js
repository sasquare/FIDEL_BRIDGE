// FidelBridge global front-end behaviour.
// Mobile navigation is handled declaratively via Alpine.js in navbar.html.

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const targetId = link.getAttribute("href");
      if (targetId.length > 1) {
        const target = document.querySelector(targetId);
        if (target) {
          event.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    });
  });
});

// Give every form submission visible feedback and stop accidental double
// submits (e.g. impatient double-clicks on a slow connection). Deferred
// with setTimeout so the button is only disabled *after* the browser has
// already captured its value for the outgoing request.
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || form.dataset.noLoadingState) return;

  const submitter = event.submitter || form.querySelector('[type="submit"]');
  if (!submitter || submitter.disabled) return;

  window.setTimeout(() => {
    submitter.disabled = true;
    submitter.classList.add("opacity-70", "cursor-not-allowed");
    if ("value" in submitter) {
      submitter.value = "Please wait…";
    } else {
      submitter.textContent = "Please wait…";
    }
  }, 0);
});
