/* Smart Queue Management System - JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    const menuToggle = document.getElementById('menu-toggle');
    const wrapper = document.getElementById('wrapper');
    const sidebar = document.getElementById('sidebar');

    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('show');
            } else {
                wrapper.classList.toggle('toggled');
            }
        });
    }

    // Close sidebar on mobile when clicking outside
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('show')) {
            if (!sidebar.contains(e.target) && e.target !== menuToggle) {
                sidebar.classList.remove('show');
            }
        }
    });

    // Dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const htmlRoot = document.getElementById('html-root');

    if (darkModeToggle && htmlRoot) {
        // Load saved preference
        const savedTheme = localStorage.getItem('sq-theme') || 'light';
        htmlRoot.setAttribute('data-bs-theme', savedTheme);
        updateDarkModeIcon(savedTheme);

        darkModeToggle.addEventListener('click', function() {
            const currentTheme = htmlRoot.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlRoot.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('sq-theme', newTheme);
            updateDarkModeIcon(newTheme);
        });
    }

    function updateDarkModeIcon(theme) {
        if (!darkModeToggle) return;
        const icon = darkModeToggle.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
        }
    }

    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Auto-hide sidebar on mobile
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && sidebar) {
            sidebar.classList.remove('show');
        }
    });

    // SocketIO for real-time updates
    if (typeof io !== 'undefined') {
        const socket = io();

        socket.on('connect', function() {
            console.log('SocketIO connected');
        });

        socket.on('disconnect', function() {
            console.log('SocketIO disconnected');
        });

        // Browser notifications
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }

        socket.on('ticket_called', function(data) {
            if (data.message) {
                showBrowserNotification('Your Turn!', data.message);
            }
        });

        socket.on('position_update', function(data) {
            // Position updates handled in page-specific JS
        });
    }

    // Browser notification helper
    window.showBrowserNotification = function(title, body) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, { body: body, icon: '/static/images/icon.png' });
        }
    };
});
