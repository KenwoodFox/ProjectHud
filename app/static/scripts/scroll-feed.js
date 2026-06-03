/**
 * Duplicates overflowing list content and animates a slow vertical scroll.
 */
function initAutoScroll() {
  const PX_PER_SECOND = 28;
  const MIN_DURATION_SEC = 25;

  document.querySelectorAll("[data-auto-scroll]").forEach((container) => {
    const content = container.querySelector(".auto-scroll-content");
    if (!content || content.querySelector(".feed-empty")) {
      return;
    }

    const items = content.children.length;
    if (items < 2) {
      return;
    }

    requestAnimationFrame(() => {
      if (content.scrollHeight <= container.clientHeight + 8) {
        return;
      }

      const track = document.createElement("div");
      track.className = "auto-scroll-track";
      const clone = content.cloneNode(true);
      clone.setAttribute("aria-hidden", "true");
      track.append(content, clone);

      const duration = Math.max(
        MIN_DURATION_SEC,
        Math.ceil(content.scrollHeight / PX_PER_SECOND)
      );
      container.style.setProperty("--scroll-duration", `${duration}s`);
      container.classList.add("auto-scroll-active");
      container.appendChild(track);
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.initTextFit) {
    window.initTextFit();
  }
  initAutoScroll();
  requestAnimationFrame(() => {
    if (window.initTextFit) {
      window.initTextFit();
    }
  });
});
