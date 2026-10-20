// Show/hide the small update forms on the Today page.
document.querySelectorAll("[data-toggle]").forEach(function (button) {
  button.addEventListener("click", function () {
    document.querySelectorAll("form.hidden, form.open").forEach(function (f) {
      var show = f.id === button.dataset.toggle && f.classList.contains("hidden");
      f.classList.toggle("hidden", !show);
      f.classList.toggle("open", show);
    });
  });
});
