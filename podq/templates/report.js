// Collapsing of top-level sections is handled natively by <details>/<summary>.

document.addEventListener('DOMContentLoaded', function () {
  // Expand / collapse all transcripts on the page
  var expandBtn = document.getElementById('expand-all-transcripts');
  var collapseBtn = document.getElementById('collapse-all-transcripts');

  if (expandBtn) {
    expandBtn.addEventListener('click', function () {
      document.querySelectorAll('.transcript-details').forEach(function (d) {
        d.open = true;
      });
    });
  }

  if (collapseBtn) {
    collapseBtn.addEventListener('click', function () {
      document.querySelectorAll('.transcript-details').forEach(function (d) {
        d.open = false;
      });
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
});
