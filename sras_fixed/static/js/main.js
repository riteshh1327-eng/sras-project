/**
 * SRAS — Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar Toggle ──────────────────────────────────────────
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const topbarMenuBtn = document.getElementById('topbarMenuBtn');
  const mainContent = document.getElementById('mainContent');

  function toggleSidebar() {
    sidebar.classList.toggle('open');
    // Desktop: collapse width
    if (window.innerWidth > 768) {
      sidebar.classList.toggle('collapsed');
      mainContent.classList.toggle('sidebar-collapsed');
    }
  }

  if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
  if (topbarMenuBtn) topbarMenuBtn.addEventListener('click', toggleSidebar);

  // Close sidebar on outside click (mobile)
  document.addEventListener('click', function (e) {
    if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && e.target !== topbarMenuBtn) {
        sidebar.classList.remove('open');
      }
    }
  });

  // ── Auto-dismiss alerts ─────────────────────────────────────
  setTimeout(function () {
    document.querySelectorAll('.alert').forEach(function (alert) {
      alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 400);
    });
  }, 5000);

  // ── Active nav highlight from URL ──────────────────────────
  // Already handled server-side, but add hover effect
  document.querySelectorAll('.nav-item').forEach(function (item) {
    item.addEventListener('mouseenter', function () {
      if (!this.classList.contains('active')) {
        this.style.paddingLeft = '14px';
      }
    });
    item.addEventListener('mouseleave', function () {
      this.style.paddingLeft = '';
    });
  });

  // ── Confirm delete via data attribute ──────────────────────
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) {
        e.preventDefault();
      }
    });
  });

  // ── Result marks: live validation + Excel-style Enter navigation ──────────
  //
  // When the user presses Enter inside any .marks-input, focus jumps to the
  // same-column input in the NEXT row (skipping disabled/absent rows).
  // This mirrors spreadsheet keyboard behaviour for fast bulk data entry.
  //
  // The inline bulk_entry.html script handles the full bulk-entry table.
  // This global handler covers any other marks table on the site.
  //
  (function initMarksInputs() {
    const inputs = Array.from(document.querySelectorAll('.marks-input'));

    inputs.forEach(function (input, idx) {
      // ── Live validation ────────────────────────────────────────────────
      input.addEventListener('input', function () {
        const max = parseFloat(this.getAttribute('max'));
        const val = parseFloat(this.value);
        if (!isNaN(val) && !isNaN(max)) {
          if (val > max) {
            this.style.borderColor     = '#ef4444';
            this.style.backgroundColor = '#fff5f5';
          } else if (val < 0) {
            this.value = 0;
            this.style.borderColor     = '';
            this.style.backgroundColor = '';
          } else {
            this.style.borderColor     = '';
            this.style.backgroundColor = '';
          }
        }
      });

      // ── Excel-style Enter key: jump to next row, same column ──────────
      // Strategy: find all inputs that share the same column index inside
      // their respective rows (td position), then advance to the next one.
      input.addEventListener('keydown', function (e) {
        if (e.key !== 'Enter') return;
        e.preventDefault();

        // Determine this input's column index within its row
        const td  = this.closest('td');
        const tr  = this.closest('tr');
        if (!td || !tr) return;

        const tdIndex = Array.from(tr.children).indexOf(td);

        // Walk forward through all marks-inputs on the page
        for (let i = idx + 1; i < inputs.length; i++) {
          const next   = inputs[i];
          if (next.disabled) continue;

          const nextTr = next.closest('tr');
          const nextTd = next.closest('td');
          if (!nextTr || !nextTd) continue;

          // Prefer same column; if not found keep scanning
          const nextCol = Array.from(nextTr.children).indexOf(nextTd);
          if (nextCol === tdIndex) {
            next.focus();
            next.select();
            next.closest('tr')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            return;
          }
        }

        // Fallback: if no same-column match found, advance to next input
        for (let i = idx + 1; i < inputs.length; i++) {
          if (!inputs[i].disabled) {
            inputs[i].focus();
            inputs[i].select();
            break;
          }
        }
      });
    });
  }());

  // ── File input: show filename ──────────────────────────────
  document.querySelectorAll('input[type="file"]').forEach(function (input) {
    input.addEventListener('change', function () {
      const label = this.closest('.form-group')?.querySelector('.form-hint');
      if (label && this.files.length > 0) {
        const name = this.files[0].name;
        const size = (this.files[0].size / 1024).toFixed(1);
        label.innerHTML = `<i class="fas fa-file-check" style="color:#16a34a"></i> ${name} (${size} KB)`;
      }
    });
  });

  // ── Smooth scroll for anchor links ──────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Table row click to highlight ───────────────────────────
  document.querySelectorAll('.data-table tbody tr').forEach(function (row) {
    row.style.cursor = 'default';
  });

});

// ── CSS for sidebar collapsed state ────────────────────────────
const style = document.createElement('style');
style.textContent = `
  .sidebar.collapsed { width: 72px; }
  .sidebar.collapsed .nav-label,
  .sidebar.collapsed .logo-text,
  .sidebar.collapsed .nav-item span { display: none; }
  .sidebar.collapsed .nav-item { justify-content: center; padding: 9px; }
  .sidebar.collapsed .sidebar-logo { justify-content: center; }
  .main-content.sidebar-collapsed { margin-left: 72px; }
`;
document.head.appendChild(style);
