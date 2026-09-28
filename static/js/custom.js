// =========================================================
// Spa Relax - JS general
// Va en static/js/custom.js
// Se carga DESPUES de bootstrap.bundle.min.js en base.html
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

  // 1. Marca como "active" el link del navbar que corresponde
  //    a la página actual, comparando con la URL del navegador.
  //    Util porque el sitio no usa un framework de frontend,
  //    solo Django + Bootstrap.
  const rutaActual = window.location.pathname;
  document.querySelectorAll(".navbar-spa .nav-link").forEach(function (link) {
    const rutaLink = link.getAttribute("href");
    if (rutaLink && rutaActual.startsWith(rutaLink) && rutaLink !== "/") {
      link.classList.add("active");
    }
  });

  // 2. Activa los tooltips de Bootstrap en toda la app
  //    (por ejemplo, para mostrar detalles de una terapia al pasar el mouse)
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // 3. Confirmación simple antes de acciones sensibles
  //    (ej: botón "Nueva asignación" o "Agregar cita" en los paneles)
  document.querySelectorAll(".confirmar-accion").forEach(function (boton) {
    boton.addEventListener("click", function (e) {
      const ok = confirm("¿Confirmas esta acción?");
      if (!ok) {
        e.preventDefault();
      }
    });
  });

});
