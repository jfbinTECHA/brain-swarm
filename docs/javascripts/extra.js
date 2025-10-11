// Brain Swarm Documentation Custom JavaScript

// Enhanced search functionality
document.addEventListener('DOMContentLoaded', function() {
    // Add copy-to-clipboard functionality to code blocks
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(function(codeBlock) {
        const pre = codeBlock.parentNode;
        const button = document.createElement('button');
        button.className = 'md-clipboard md-icon';
        button.title = 'Copy to clipboard';
        button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>';

        button.addEventListener('click', function() {
            const text = codeBlock.textContent;
            navigator.clipboard.writeText(text).then(function() {
                button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
                setTimeout(function() {
                    button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>';
                }, 2000);
            });
        });

        pre.appendChild(button);
    });

    // Enhanced table of contents interaction
    const tocLinks = document.querySelectorAll('.md-nav__link');
    tocLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            // Smooth scroll to section
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add loading animation for external links
    const externalLinks = document.querySelectorAll('a[href^="http"]');
    externalLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            if (!this.href.includes(window.location.hostname)) {
                // Add loading indicator
                const indicator = document.createElement('span');
                indicator.innerHTML = ' 🔗';
                indicator.style.opacity = '0.7';
                this.appendChild(indicator);

                // Remove after 2 seconds
                setTimeout(function() {
                    if (indicator.parentNode) {
                        indicator.parentNode.removeChild(indicator);
                    }
                }, 2000);
            }
        });
    });

    // Enhanced search with keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+K or Cmd+K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.md-search__input');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('.md-search__input');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.value = '';
                searchInput.blur();
            }
        }
    });

    // Add version info to footer
    const footer = document.querySelector('.md-footer');
    if (footer) {
        const versionInfo = document.createElement('div');
        versionInfo.className = 'md-footer__version';
        versionInfo.innerHTML = `
            <span class="md-footer__version__label">Brain Swarm v1.0.0</span>
            <span class="md-footer__version__date">Last updated: ${new Date().toLocaleDateString()}</span>
        `;
        footer.appendChild(versionInfo);
    }

    // Add interactive elements to admonitions
    const admonitions = document.querySelectorAll('.admonition');
    admonitions.forEach(function(admonition) {
        const title = admonition.querySelector('.admonition-title');
        if (title) {
            title.addEventListener('click', function() {
                admonition.classList.toggle('admonition--expanded');
            });
        }
    });

    // Performance monitoring for docs
    if ('performance' in window && 'PerformanceObserver' in window) {
        // Monitor Largest Contentful Paint
        const lcpObserver = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            console.log('LCP:', lastEntry.startTime);
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

        // Monitor First Input Delay
        const fidObserver = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            entries.forEach((entry) => {
                console.log('FID:', entry.processingStart - entry.startTime);
            });
        });
        fidObserver.observe({ entryTypes: ['first-input'] });
    }

    // Add syntax highlighting for inline code
    const inlineCodes = document.querySelectorAll('code:not(pre code)');
    inlineCodes.forEach(function(code) {
        if (code.textContent.includes('.')) {
            // Likely a method or property
            code.classList.add('highlight');
        }
    });

    // Enhanced Mermaid diagram interaction
    const mermaidDiagrams = document.querySelectorAll('.mermaid');
    mermaidDiagrams.forEach(function(diagram) {
        diagram.addEventListener('click', function() {
            this.classList.toggle('mermaid-expanded');
        });
    });

    // Add print-friendly styles
    const style = document.createElement('style');
    style.textContent = `
        @media print {
            .md-clipboard, .md-search, .md-nav, .md-sidebar {
                display: none !important;
            }
            .md-main__inner {
                margin: 0 !important;
                max-width: none !important;
            }
            pre {
                white-space: pre-wrap;
                word-wrap: break-word;
            }
        }
    `;
    document.head.appendChild(style);
});

// Service worker for offline documentation access
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// Analytics (optional - only if enabled)
if (typeof gtag !== 'undefined') {
    // Track page views
    gtag('config', 'GA_MEASUREMENT_ID', {
        page_title: document.title,
        page_location: window.location.href
    });

    // Track search queries
    const searchInput = document.querySelector('.md-search__input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                if (searchInput.value.length > 2) {
                    gtag('event', 'search', {
                        search_term: searchInput.value
                    });
                }
            }, 1000);
        });
    }
}