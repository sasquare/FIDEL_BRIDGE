// Cascading State -> City dropdown for the hero search bar. Depends on
// window.NIGERIA_LOCATIONS (see nigeria-locations.js, loaded first).
// Registered via alpine:init rather than an inline <script>, since the
// CSP only allows 'self' scripts.
document.addEventListener("alpine:init", () => {
  Alpine.data("locationPicker", () => ({
    state: "",
    city: "",

    get states() {
      return Object.keys(window.NIGERIA_LOCATIONS || {}).sort();
    },

    get cities() {
      if (!this.state) return [];
      return window.NIGERIA_LOCATIONS[this.state] || [];
    },

    onStateChange() {
      this.city = "";
    },
  }));
});
