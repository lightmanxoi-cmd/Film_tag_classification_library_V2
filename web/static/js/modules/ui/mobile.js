/**
 * 移动端 UI 模块
 */

export function openMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

export function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
}

export function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
        closeMobileSidebar();
    } else {
        openMobileSidebar();
    }
}

export function openMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    if (searchBar) {
        searchBar.classList.add('show');
        const input = document.getElementById('mobileSearchInput');
        if (input) input.focus();
    }
}

export function closeMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    const input = document.getElementById('mobileSearchInput');
    if (searchBar) searchBar.classList.remove('show');
    if (input) input.value = '';
}

export function toggleMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    if (searchBar && searchBar.classList.contains('show')) {
        closeMobileSearch();
    } else {
        openMobileSearch();
    }
}

export function setupScrollHideNavbar() {
    let lastScrollTop = 0;
    const navbar = document.querySelector('.navbar');
    
    if (!navbar) return;
    
    window.addEventListener('scroll', function() {
        if (window.innerWidth <= 768) {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            if (scrollTop > lastScrollTop && scrollTop > 100) {
                navbar.style.transform = 'translateY(-100%)';
            } else {
                navbar.style.transform = 'translateY(0)';
            }
            
            lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
        }
    }, { passive: true });
    
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMobileSidebar();
            closeMobileSearch();
            navbar.style.transform = 'translateY(0)';
        }
    });
}
