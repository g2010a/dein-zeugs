// Collapsing of top-level sections is handled natively by <details>/<summary>.

document.addEventListener('DOMContentLoaded', function () {
  // Toggle expand/collapse all transcripts
  var toggleBtn = document.getElementById('toggle-all-transcripts');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      var details = document.querySelectorAll('.transcript-details');
      var allOpen = Array.from(details).every(function (d) { return d.open; });
      details.forEach(function (d) { d.open = !allOpen; });
      toggleBtn.textContent = allOpen ? 'Alle aufklappen' : 'Alle zuklappen';
    });
  }

  // Show-more / show-less inside individual transcripts (event delegation)
  document.addEventListener('click', function (e) {
    if (!e.target.classList.contains('transcript-expand-btn')) return;
    var body = e.target.closest('.transcript-body');
    if (!body) return;
    var rest = body.querySelector('.transcript-rest');
    if (!rest) return;
    if (rest.hidden) {
      rest.hidden = false;
      e.target.textContent = 'Weniger anzeigen';
    } else {
      rest.hidden = true;
      e.target.textContent = 'Mehr anzeigen';
    }
  });

  // Auto-open target <details> section when a nav link is clicked
  document.querySelectorAll('.sticky-nav a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function () {
      var el = document.getElementById(link.getAttribute('href').slice(1));
      if (el && el.tagName === 'DETAILS') el.open = true;
    });
  });
});
