/*
  The whole of the site's JavaScript: a lightbox, a mobile menu, and copy deterrents.
  No framework, no build step — everything here runs straight from the file.
*/

(function () {
  "use strict";

  // --- Lightbox ------------------------------------------------------------
  // GLightbox handles keyboard, touch and next/prev navigation, which is the reason
  // not to hand-roll one.
  if (window.GLightbox && document.querySelector(".glightbox")) {
    GLightbox({
      selector: ".glightbox",
      touchNavigation: true,
      loop: true,
      openEffect: "fade",
      closeEffect: "fade",
      slideEffect: "fade",
    });
  }

  // --- Mobile navigation ---------------------------------------------------
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      nav.classList.toggle("is-open", !open);
    });
  }

  // --- Copy deterrents -----------------------------------------------------
  // A speed bump, not protection: anyone determined can still read the bytes off the
  // wire, and the lightbox link points at a real image URL they can open directly.
  //
  // Delegated from the document rather than bound to each image at load, because the
  // lightbox builds its own overlay outside the photo grid. Binding per element left
  // that overlay — which shows the *largest* public derivative — unprotected, so the
  // one image worth deterring was the one that was not.
  function isProtected(node) {
    if (!node || node.tagName !== "IMG") {
      return false;
    }
    // Public pages opt in, and that covers every photograph on them, the lightbox
    // included. Client galleries deliberately do not: those photographs belong to the
    // person looking at them, and right-click-save is how many people expect to keep one.
    return (
      document.body.classList.contains("protect-images") ||
      !!node.closest(".entry__photos")
    );
  }

  ["contextmenu", "dragstart"].forEach(function (type) {
    document.addEventListener(
      type,
      function (event) {
        if (isProtected(event.target)) {
          event.preventDefault();
        }
      },
      true
    );
  });
})();
