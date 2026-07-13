document.addEventListener('DOMContentLoaded', function() {
    // 1. Theme Toggle Logic
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            if (document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            }
        });
    }

    // 2. Sidebar Toggle Logic (Desktop)
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebarOffcanvas = document.getElementById('sidebarOffcanvas');
    const sidebarIcon = document.getElementById('sidebarToggleIcon');

    function applySidebarState(isCollapsed) {
        if (!sidebarOffcanvas || !sidebarIcon) return;
        
        if (isCollapsed && window.innerWidth >= 992) {
            sidebarOffcanvas.style.width = '80px';
            document.querySelectorAll('.sidebar-text').forEach(el => el.style.display = 'none');
            sidebarIcon.classList.remove('bi-chevron-bar-left');
            sidebarIcon.classList.add('bi-chevron-bar-right');
        } else {
            sidebarOffcanvas.style.width = '260px';
            document.querySelectorAll('.sidebar-text').forEach(el => el.style.display = '');
            sidebarIcon.classList.remove('bi-chevron-bar-right');
            sidebarIcon.classList.add('bi-chevron-bar-left');
        }
    }

    // Initial state
    const isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    applySidebarState(isSidebarCollapsed);

    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            const currentlyCollapsed = sidebarOffcanvas.style.width === '80px';
            const newState = !currentlyCollapsed;
            localStorage.setItem('sidebarCollapsed', newState);
            applySidebarState(newState);
        });
    }

    // Handle resize to fix styling if crossing breakpoints
    window.addEventListener('resize', () => {
        applySidebarState(localStorage.getItem('sidebarCollapsed') === 'true');
    });

    // 3. Initialize Toasts
    var toastElList = [].slice.call(document.querySelectorAll('.toast'))
    var toastList = toastElList.map(function (toastEl) {
      return new bootstrap.Toast(toastEl, {})
    });
    toastList.forEach(toast => toast.show());
});
