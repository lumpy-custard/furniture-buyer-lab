(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var menus = [];

    function setupMenu(triggerId, panelId) {
      var trigger = document.getElementById(triggerId);
      var panel = document.getElementById(panelId);
      if (!trigger || !panel) return;

      function close() {
        panel.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
      }

      function open() {
        menus.forEach(function (menu) {
          if (menu.panel !== panel) menu.close();
        });
        panel.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
      }

      trigger.addEventListener("click", function (event) {
        event.stopPropagation();
        if (panel.hidden) {
          open();
        } else {
          close();
        }
      });

      panel.addEventListener("click", function (event) {
        if (event.target.closest("a.profile-menu-item")) close();
      });

      menus.push({ trigger: trigger, panel: panel, close: close });
    }

    setupMenu("profile-trigger", "profile-panel");
    setupMenu("brand-trigger", "brand-panel");

    document.addEventListener("click", function (event) {
      menus.forEach(function (menu) {
        if (!menu.panel.hidden && !menu.panel.contains(event.target) && event.target !== menu.trigger) {
          menu.close();
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        menus.forEach(function (menu) {
          menu.close();
        });
      }
    });
  });
})();
