/* CrediFlux DS — DataTable ordenable (contrato de project/components/DataTable).
 * Cada <th aria-sort> envuelve su label en <button class="cf-sort">. Tipo con
 * data-type="text|num|date" (default text). El valor de orden sale de
 * td[data-v] si existe; si no, del texto de la celda. Vacíos ("—") al final. */
(function () {
  const ICON = '<svg class="cf-sort__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="18 15 12 9 6 15"/></svg>';
  const MONTHS = { ene:0, feb:1, mar:2, abr:3, may:4, jun:5, jul:6, ago:7, sep:8, oct:9, nov:10, dic:11 };

  function parse(raw, type) {
    const s = (raw || '').trim();
    if (!s || s === '—' || s === '-') return null;
    if (type === 'num') {
      const n = parseFloat(s.replace(/[^0-9.\-]/g, ''));
      return isNaN(n) ? null : n;
    }
    if (type === 'date') {
      if (/^\d{4}-\d{2}-\d{2}/.test(s)) return Date.parse(s);
      const m = s.toLowerCase().match(/(\d{1,2})\D+([a-z]{3})\D+(\d{4})/);
      if (m && m[2] in MONTHS) return new Date(+m[3], MONTHS[m[2]], +m[1]).getTime();
      return null;
    }
    return s;
  }

  function wire(table) {
    const heads = [...table.querySelectorAll('thead th[aria-sort]')];
    const tbody = table.tBodies[0];
    if (!tbody) return;
    // Rows that must stay at the bottom (totals) carry data-fixed.
    heads.forEach(th => {
      if (!th.querySelector('.cf-sort')) {
        th.innerHTML = `<button class="cf-sort" type="button">${th.innerHTML}${ICON}</button>`;
      }
      th.querySelector('.cf-sort').addEventListener('click', () => {
        const dir = th.getAttribute('aria-sort') === 'ascending' ? 'descending' : 'ascending';
        heads.forEach(h => h.setAttribute('aria-sort', 'none'));
        th.setAttribute('aria-sort', dir);
        const idx = [...th.parentElement.children].indexOf(th);
        const type = th.dataset.type || 'text';
        const rows = [...tbody.rows].filter(r => !r.hasAttribute('data-fixed'));
        const fixed = [...tbody.rows].filter(r => r.hasAttribute('data-fixed'));
        rows.sort((a, b) => {
          const ca = a.cells[idx], cb = b.cells[idx];
          const x = parse(ca && (ca.dataset.v ?? ca.textContent), type);
          const y = parse(cb && (cb.dataset.v ?? cb.textContent), type);
          if (x === null && y === null) return 0;
          if (x === null) return 1;   // vacíos al final en ambos sentidos
          if (y === null) return -1;
          const r = type === 'text' ? String(x).localeCompare(String(y), 'es') : x - y;
          return dir === 'ascending' ? r : -r;
        });
        rows.concat(fixed).forEach(r => tbody.appendChild(r));
      });
    });
  }

  document.querySelectorAll('table.cf-table').forEach(wire);
})();
