document.addEventListener('DOMContentLoaded', function () {

  // ── 1. Transcript expand/collapse ────────────────────────────────
  var toggleBtn = document.getElementById('toggle-all-transcripts');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      var details = document.querySelectorAll('.transcript-details');
      var allOpen = Array.from(details).every(function (d) { return d.open; });
      details.forEach(function (d) { d.open = !allOpen; });
      toggleBtn.textContent = allOpen ? 'Alle aufklappen' : 'Alle zuklappen';
    });
  }

  document.addEventListener('click', function (e) {
    if (!e.target.classList.contains('transcript-expand-btn')) return;
    var body = e.target.closest('.transcript-body');
    if (!body) return;
    var rest = body.querySelector('.transcript-rest');
    if (!rest) return;
    rest.hidden = !rest.hidden;
    e.target.textContent = rest.hidden ? 'Mehr anzeigen' : 'Weniger anzeigen';
  });

  // ── 2. Auto-open section on nav click ────────────────────────────
  document.querySelectorAll('.sticky-nav a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function () {
      var target = document.querySelector(link.getAttribute('href'));
      if (target && target.tagName === 'DETAILS') target.open = true;
    });
  });

  // ── 3. Search + filter chips ─────────────────────────────────────
  var searchInput = document.getElementById('q');
  var activeFilter = null;
  var activeKeyword = null;

  function itemVisible(el) {
    var q = searchInput ? searchInput.value.trim().toLowerCase() : '';
    if (q) {
      var text = [
        el.getAttribute('data-stem') || '',
        el.getAttribute('data-summary') || '',
        el.getAttribute('data-keywords') || ''
      ].join(' ').toLowerCase();
      if (!text.includes(q)) return false;
    }
    if (activeFilter) {
      if (activeFilter === 'new'    && el.getAttribute('data-section') !== 'processed') return false;
      if (activeFilter === 'aired'  && el.getAttribute('data-section') !== 'aired')     return false;
    }
    if (activeKeyword) {
      var kws = (el.getAttribute('data-keywords') || '').split(',').map(function (k) { return k.trim(); });
      if (!kws.includes(activeKeyword)) return false;
    }
    return true;
  }

  function applyFilters() {
    document.querySelectorAll('[data-stem][data-section]').forEach(function (el) {
      if (el.classList.contains('cluster-header-row')) return;
      el.classList.toggle('item-hidden', !itemVisible(el));
    });
    updateAllQuestionsCount();
    currentPage = 1;
    applyPagination();
  }

  function updateAllQuestionsCount() {
    var tbody = document.getElementById('all-questions-tbody');
    if (!tbody) return;
    var rows = Array.from(tbody.rows).filter(function (r) {
      return !r.classList.contains('cluster-header-row');
    });
    var total = rows.length;
    var visible = rows.filter(function (r) { return !r.classList.contains('item-hidden'); }).length;
    var el = document.getElementById('all-questions-count');
    if (el) el.textContent = visible < total ? '(' + visible + ' von ' + total + ')' : '(' + total + ')';
    var navEl = document.getElementById('nav-all-count');
    if (navEl) navEl.textContent = visible;
  }

  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
    document.addEventListener('keydown', function (e) {
      var tag = document.activeElement ? document.activeElement.tagName : '';
      if (e.key === '/' && tag !== 'INPUT' && tag !== 'SELECT' && tag !== 'TEXTAREA') {
        e.preventDefault();
        searchInput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        searchInput.focus();
      }
      if (e.key === 'Escape' && document.activeElement === searchInput) {
        searchInput.value = '';
        applyFilters();
        searchInput.blur();
      }
    });
  }

  document.querySelectorAll('.filter-btn[data-filter]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var f = btn.getAttribute('data-filter');
      if (activeFilter === f) {
        activeFilter = null;
        btn.classList.remove('filter-btn-active');
      } else {
        document.querySelectorAll('.filter-btn-active').forEach(function (b) { b.classList.remove('filter-btn-active'); });
        activeFilter = f;
        btn.classList.add('filter-btn-active');
      }
      applyFilters();
    });
  });

  // ── 4. Keyword cloud ─────────────────────────────────────────────
  var cloudEl = document.getElementById('keyword-cloud');
  var toggleCloudBtn = document.getElementById('toggle-keyword-cloud');

  if (cloudEl) {
    var kwCount = {};
    document.querySelectorAll('[data-keywords]').forEach(function (el) {
      (el.getAttribute('data-keywords') || '').split(',').forEach(function (k) {
        k = k.trim();
        if (k) kwCount[k] = (kwCount[k] || 0) + 1;
      });
    });
    var kwList = Object.keys(kwCount).sort(function (a, b) { return kwCount[b] - kwCount[a]; }).slice(0, 50);

    if (kwList.length > 0 && toggleCloudBtn) {
      toggleCloudBtn.style.display = '';
      kwList.forEach(function (kw) {
        var btn = document.createElement('button');
        btn.className = 'kw-cloud-btn';
        btn.textContent = kw + ' · ' + kwCount[kw];
        btn.setAttribute('data-kw', kw);
        btn.addEventListener('click', function () { toggleKeyword(kw, btn); });
        cloudEl.appendChild(btn);
      });

      toggleCloudBtn.addEventListener('click', function () {
        var open = cloudEl.style.display !== 'none';
        cloudEl.style.display = open ? 'none' : '';
        toggleCloudBtn.textContent = open ? 'Schlagwörter ▾' : 'Schlagwörter ▴';
      });
    }
  }

  function toggleKeyword(kw, btn) {
    if (activeKeyword === kw) {
      activeKeyword = null;
      if (btn) btn.classList.remove('kw-cloud-btn-active');
    } else {
      if (cloudEl) cloudEl.querySelectorAll('.kw-cloud-btn-active').forEach(function (b) { b.classList.remove('kw-cloud-btn-active'); });
      activeKeyword = kw;
      if (btn) btn.classList.add('kw-cloud-btn-active');
    }
    applyFilters();
  }

  // keyword chip click inside table activates cloud filter
  document.addEventListener('click', function (e) {
    var chip = e.target.closest('.chip-kw');
    if (!chip) return;
    var kw = chip.getAttribute('data-kw');
    if (!kw) return;
    var cloudBtn = null;
    if (cloudEl) {
      Array.from(cloudEl.querySelectorAll('.kw-cloud-btn')).forEach(function (b) {
        if (b.getAttribute('data-kw') === kw) cloudBtn = b;
      });
    }
    if (cloudEl && cloudEl.style.display === 'none' && cloudBtn) {
      cloudEl.style.display = '';
      if (toggleCloudBtn) toggleCloudBtn.textContent = 'Schlagwörter ▴';
    }
    toggleKeyword(kw, cloudBtn);
  });

  // ── 5. Sortable table ────────────────────────────────────────────
  var sortCol = 'novelty';
  var sortDir = 'desc';

  function sortTable() {
    if (groupByCluster) return; // sort disabled while grouped
    var tbody = document.getElementById('all-questions-tbody');
    if (!tbody) return;
    var rows = Array.from(tbody.rows).filter(function (r) {
      return !r.classList.contains('cluster-header-row');
    });
    rows.sort(function (a, b) {
      if (sortCol === 'stem') {
        var av = (a.getAttribute('data-stem') || '').toLowerCase();
        var bv = (b.getAttribute('data-stem') || '').toLowerCase();
        return sortDir === 'asc' ? av.localeCompare(bv, 'de') : bv.localeCompare(av, 'de');
      }
      if (sortCol === 'first-seen' || sortCol === 'analyzed-at') {
        var av = a.getAttribute('data-' + sortCol) || '';
        var bv = b.getAttribute('data-' + sortCol) || '';
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      var av = parseFloat(a.getAttribute('data-' + sortCol) || 0);
      var bv = parseFloat(b.getAttribute('data-' + sortCol) || 0);
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    rows.forEach(function (r) { tbody.appendChild(r); });

    document.querySelectorAll('#all-questions-table th[data-sort]').forEach(function (th) {
      var icon = th.querySelector('.sort-icon');
      th.classList.remove('sort-active', 'sort-asc', 'sort-desc');
      if (th.getAttribute('data-sort') === sortCol) {
        th.classList.add('sort-active', 'sort-' + sortDir);
        if (icon) icon.textContent = sortDir === 'asc' ? '▲' : '▼';
      } else {
        if (icon) icon.textContent = '';
      }
    });
    applyPagination();
  }

  document.querySelectorAll('#all-questions-table th[data-sort]').forEach(function (th) {
    th.addEventListener('click', function () {
      if (groupByCluster) return;
      var col = th.getAttribute('data-sort');
      if (sortCol === col) {
        sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        sortCol = col;
        sortDir = (col === 'stem' || col === 'first-seen' || col === 'analyzed-at') ? 'asc' : 'desc';
      }
      sortTable();
    });
  });
  sortTable();

  // ── 6. Group by cluster ──────────────────────────────────────────
  var groupByCluster = false;
  // CLUSTER_NAMES is injected by the template as a global var

  function removeClusterHeaders() {
    var tbody = document.getElementById('all-questions-tbody');
    if (!tbody) return;
    Array.from(tbody.querySelectorAll('.cluster-header-row')).forEach(function (r) { r.remove(); });
  }

  function applyGroupByCluster() {
    removeClusterHeaders();
    var tbody = document.getElementById('all-questions-tbody');
    if (!tbody) return;

    var rows = Array.from(tbody.rows).filter(function (r) {
      return !r.classList.contains('cluster-header-row');
    });

    var clusterGroups = {};
    var noCluster = [];
    rows.forEach(function (row) {
      var cid = row.getAttribute('data-cluster');
      if (cid) {
        if (!clusterGroups[cid]) clusterGroups[cid] = [];
        clusterGroups[cid].push(row);
      } else {
        noCluster.push(row);
      }
    });

    var clusterNames = (typeof CLUSTER_NAMES !== 'undefined') ? CLUSTER_NAMES : {};

    Object.keys(clusterGroups).forEach(function (cid) {
      var name = clusterNames[cid] || cid;
      var count = clusterGroups[cid].length;
      var headerRow = document.createElement('tr');
      headerRow.className = 'cluster-header-row';
      headerRow.innerHTML = '<td colspan="9" class="cluster-header-cell">&#x1F4CC; ' +
        name + ' <span class="chip">' + count + ' Fragen</span></td>';
      tbody.appendChild(headerRow);
      clusterGroups[cid].forEach(function (r) { tbody.appendChild(r); });
    });

    if (noCluster.length > 0) {
      var singletonRow = document.createElement('tr');
      singletonRow.className = 'cluster-header-row';
      singletonRow.innerHTML = '<td colspan="9" class="cluster-header-cell">Einzelne Fragen <span class="chip">' + noCluster.length + '</span></td>';
      tbody.appendChild(singletonRow);
      noCluster.forEach(function (r) { tbody.appendChild(r); });
    }
  }

  var groupBtn = document.getElementById('btn-group-by-cluster');
  if (groupBtn) {
    groupBtn.addEventListener('click', function () {
      groupByCluster = !groupByCluster;
      groupBtn.classList.toggle('filter-btn-active', groupByCluster);
      if (groupByCluster) {
        applyGroupByCluster();
      } else {
        removeClusterHeaders();
        sortTable();
      }
      applyPagination();
    });
  }

  // ── 7. Pagination ────────────────────────────────────────────────
  var currentPage = 1;
  var pageSize = 25;

  var pageSizeEl = document.getElementById('page-size');
  if (pageSizeEl) {
    pageSizeEl.addEventListener('change', function () {
      pageSize = parseInt(this.value, 10);
      currentPage = 1;
      applyPagination();
    });
  }

  function applyPagination() {
    var tbody = document.getElementById('all-questions-tbody');
    var controls = document.getElementById('pagination-controls');
    if (!tbody || !controls) return;

    var visibleRows = Array.from(tbody.rows).filter(function (r) {
      return !r.classList.contains('item-hidden') && !r.classList.contains('cluster-header-row');
    });
    var total = visibleRows.length;

    if (pageSize === 0) {
      visibleRows.forEach(function (r) { r.classList.remove('page-hidden'); });
      controls.innerHTML = '';
      return;
    }

    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;

    visibleRows.forEach(function (r, i) {
      r.classList.toggle('page-hidden', Math.floor(i / pageSize) + 1 !== currentPage);
    });

    controls.innerHTML = '';

    function pageBtn(label, pg, disabled, active) {
      var b = document.createElement('button');
      b.textContent = label;
      b.className = 'page-btn' + (active ? ' page-btn-active' : '');
      b.disabled = disabled;
      if (!disabled) b.addEventListener('click', function () { currentPage = pg; applyPagination(); });
      controls.appendChild(b);
    }

    function dot() {
      var s = document.createElement('span');
      s.textContent = '…';
      s.className = 'page-ellipsis';
      controls.appendChild(s);
    }

    pageBtn('‹', currentPage - 1, currentPage === 1, false);
    var lo = Math.max(1, currentPage - 2), hi = Math.min(totalPages, currentPage + 2);
    if (lo > 1) { pageBtn('1', 1, false, false); if (lo > 2) dot(); }
    for (var p = lo; p <= hi; p++) pageBtn(String(p), p, false, p === currentPage);
    if (hi < totalPages) { if (hi < totalPages - 1) dot(); pageBtn(String(totalPages), totalPages, false, false); }
    pageBtn('›', currentPage + 1, currentPage === totalPages, false);
  }

  // initial render
  updateAllQuestionsCount();
  applyPagination();
});
