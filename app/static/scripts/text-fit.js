/**
 * Wraps truncated text cells and scrolls horizontally when content overflows.
 */
const TEXT_FIT_SELECTOR = [
  ".inv-primary",
  ".inv-tag",
  ".inv-body",
  ".inv-meta",
  ".card-title",
  ".card-meta",
  ".number-box .repo-name",
  ".assignee-name",
  ".issue-label",
  ".feed-repo",
  ".feed-sha",
  ".feed-body",
  ".feed-meta",
  ".feed-status",
  ".milestone-text",
  ".assignment-number",
  ".assignment-repo",
  ".reviewer-name",
].join(",");

const PX_PER_SECOND = 42;
const MIN_DURATION_SEC = 8;
const MARQUEE_GAP_EM = 2;

function initTextFit(root = document) {
  root.querySelectorAll(TEXT_FIT_SELECTOR).forEach((el) => {
    if (el.classList.contains("text-fit-ready") || el.closest(".feed-empty")) {
      return;
    }

    const text = el.textContent.trim();
    if (!text) {
      return;
    }

    el.textContent = "";
    el.classList.add("text-fit", "text-fit-ready");

    const track = document.createElement("span");
    track.className = "text-fit-track";

    const inner = document.createElement("span");
    inner.className = "text-fit-inner";
    inner.textContent = text;
    track.appendChild(inner);
    el.appendChild(track);

    if (inner.scrollWidth <= el.clientWidth + 1) {
      return;
    }

    const clone = document.createElement("span");
    clone.className = "text-fit-inner text-fit-gap";
    clone.setAttribute("aria-hidden", "true");
    clone.textContent = text;
    track.appendChild(clone);

    const duration = Math.max(
      MIN_DURATION_SEC,
      Math.ceil(track.scrollWidth / PX_PER_SECOND)
    );
    el.style.setProperty("--text-fit-duration", `${duration}s`);
    el.classList.add("text-fit-overflow");
  });
}

function scheduleTextFit() {
  requestAnimationFrame(() => {
    initTextFit();
    requestAnimationFrame(initTextFit);
  });
}

window.initTextFit = initTextFit;
document.addEventListener("DOMContentLoaded", scheduleTextFit);
