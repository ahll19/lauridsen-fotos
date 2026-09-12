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
  // wire. Scoped to photographs so the rest of the page behaves normally.
  var protectedImages = document.querySelectorAll(
    ".protect-images .photo img, .photo--client img, .entry__photos img"
  );

  Array.prototype.forEach.call(protectedImages, function (img) {
    img.addEventListener("contextmenu", function (event) {
      event.preventDefault();
    });
    img.addEventListener("dragstart", function (event) {
      event.preventDefault();
    });
  });
})();
