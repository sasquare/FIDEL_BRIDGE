// Landing page hero slider: autoplay, pause-on-hover, arrows, dots, swipe.
// Registered as an Alpine.js component (see main/index.html: x-data="heroSlider(3)")
// rather than an inline <script>, since the CSP only allows 'self' scripts.
document.addEventListener("alpine:init", () => {
  Alpine.data("heroSlider", (slideCount) => ({
    active: 0,
    total: slideCount,
    timer: null,
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    touchStartX: null,

    init() {
      this.play();
    },

    play() {
      this.stop();
      if (this.reducedMotion) return;
      this.timer = setInterval(() => this.next(), 8000);
    },

    stop() {
      if (this.timer) clearInterval(this.timer);
      this.timer = null;
    },

    next() {
      this.active = (this.active + 1) % this.total;
    },

    prev() {
      this.active = (this.active - 1 + this.total) % this.total;
    },

    goTo(index) {
      this.active = index;
      this.play();
    },

    onTouchStart(event) {
      this.touchStartX = event.changedTouches[0].clientX;
    },

    onTouchEnd(event) {
      if (this.touchStartX === null) return;
      const delta = event.changedTouches[0].clientX - this.touchStartX;
      if (Math.abs(delta) > 40) {
        delta < 0 ? this.next() : this.prev();
        this.play();
      }
      this.touchStartX = null;
    },
  }));
});
