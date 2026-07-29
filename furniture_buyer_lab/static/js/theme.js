(function () {
  var STORAGE_KEY = "theme";
  var root = document.documentElement;

  var SUN_SVG =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/>' +
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';

  var MOON_SVG =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg>';

  function isDarkNow() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "light") return false;
    if (explicit === "dark") return true;
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementById("theme-toggle");
    if (!button) return;

    function updateIcon() {
      var dark = isDarkNow();
      if (button.classList.contains("profile-menu-item")) {
        var icon = dark ? SUN_SVG : MOON_SVG;
        var label = dark ? "Light mode" : "Dark mode";
        button.innerHTML = icon + "<span>" + label + "</span>";
      } else {
        button.innerHTML = dark ? MOON_SVG : SUN_SVG;
      }
      button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    }

    updateIcon();

    button.addEventListener("click", function () {
      var next = isDarkNow() ? "light" : "dark";
      localStorage.setItem(STORAGE_KEY, next);
      root.setAttribute("data-theme", next);
      updateIcon();
    });

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (!localStorage.getItem(STORAGE_KEY)) updateIcon();
      });
    }
  });
})();
