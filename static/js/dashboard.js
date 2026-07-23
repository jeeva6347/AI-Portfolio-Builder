document.addEventListener('DOMContentLoaded', function () {

    // ── 1. Theme Toggle ──────────────────────────────────────────
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            if (document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            }
        });
    }

    // ── 2. Sidebar Collapse Toggle (Desktop only, ≥ 992px) ───────
    const sidebarToggleBtn  = document.getElementById('sidebarToggleBtn');
    const sidebarOffcanvas  = document.getElementById('sidebarOffcanvas');
    const sidebarToggleIcon = document.getElementById('sidebarToggleIcon');

    function setSidebarCollapsed(collapsed) {
        if (window.innerWidth < 992) return; // Never collapse on mobile (offcanvas handles it)

        if (collapsed) {
            document.body.classList.add('sidebar-collapsed');
            if (sidebarToggleIcon) {
                sidebarToggleIcon.classList.remove('bi-chevron-bar-left');
                sidebarToggleIcon.classList.add('bi-chevron-bar-right');
            }
        } else {
            document.body.classList.remove('sidebar-collapsed');
            if (sidebarToggleIcon) {
                sidebarToggleIcon.classList.remove('bi-chevron-bar-right');
                sidebarToggleIcon.classList.add('bi-chevron-bar-left');
            }
        }
    }

    // Restore saved state on load
    const savedCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    setSidebarCollapsed(savedCollapsed);

    // Toggle on button click
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function () {
            const isCollapsed = document.body.classList.contains('sidebar-collapsed');
            const next = !isCollapsed;
            localStorage.setItem('sidebarCollapsed', next);
            setSidebarCollapsed(next);
        });
    }

    // Re-apply on window resize (handles crossing 992px breakpoint)
    window.addEventListener('resize', function () {
        if (window.innerWidth < 992) {
            document.body.classList.remove('sidebar-collapsed');
        } else {
            setSidebarCollapsed(localStorage.getItem('sidebarCollapsed') === 'true');
        }
    });

    // ── 3. Active Nav Link (path prefix matching) ────────────────
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-nav-link').forEach(function (link) {
        const href = link.getAttribute('href');
        if (!href || href === '#') return;
        link.classList.remove('active');
        if (currentPath === href || (href.length > 1 && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    });

    // ── 4. Bootstrap Tooltips (for collapsed sidebar icons) ──────
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
            new bootstrap.Tooltip(el, { trigger: 'hover' });
        });
    }

    // ── 5. Toast Notifications ───────────────────────────────────
    document.querySelectorAll('.toast').forEach(function (toastEl) {
        new bootstrap.Toast(toastEl, {}).show();
    });

    // ── 6. Prevent double-submit on forms ───────────────────────
    document.querySelectorAll('form').forEach(function (form) {
        form.addEventListener('submit', function () {
            const btn = form.querySelector("button[type='submit']");
            if (btn && !btn.classList.contains('no-disable')) {
                if (!form.checkValidity || form.checkValidity()) {
                    setTimeout(function () {
                        btn.disabled = true;
                        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Saving...';
                    }, 50);
                }
            }
        });
    });
});
