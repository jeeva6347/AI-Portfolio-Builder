/**
 * Preview Sync Engine for AI Portfolio Builder (Phase 4.1)
 * Loaded inside live preview iframe to enable:
 * - Direct inline text editing (contenteditable)
 * - Section selection outlines
 * - Bi-directional click & scroll synchronization
 * - Right-click context menu event dispatching
 */

(function () {
    let activeElement = null;

    // Field mapping selectors for common portfolio fields across themes
    const FIELD_SELECTORS = [
        { selector: '[data-field="personal.name"], .hero-name, .profile-name, h1', field: 'name', section: 'personal' },
        { selector: '[data-field="personal.title"], .hero-title, .job-title', field: 'title', section: 'personal' },
        { selector: '[data-field="personal.tagline"], .hero-tagline', field: 'tagline', section: 'personal' },
        { selector: '[data-field="personal.about"], .about-text, .bio-description', field: 'about', section: 'about' },
        { selector: '[data-field="contact.email"], .contact-email', field: 'contact_email', section: 'contact' },
        { selector: '[data-field="contact.phone"], .contact-phone', field: 'contact_phone', section: 'contact' },
        { selector: '[data-field="footer.copyright"], .copyright-text', field: 'footer_copyright', section: 'settings' }
    ];

    document.addEventListener('DOMContentLoaded', () => {
        setupInteractiveElements();
        setupContextMenuHandler();
        setupParentMessageListener();
    });

    function setupInteractiveElements() {
        // Find sections
        const sections = document.querySelectorAll('section, header, footer, .portfolio-section, [data-section-id]');
        sections.forEach(sec => {
            sec.style.transition = 'outline 0.2s ease, box-shadow 0.2s ease';
            
            // Hover highlight
            sec.addEventListener('mouseenter', (e) => {
                if (window.previewMode === 'locked') return;
                if (sec !== activeElement) {
                    sec.style.outline = '2px dashed #93c5fd';
                    sec.style.outlineOffset = '-2px';
                }
            });

            sec.addEventListener('mouseleave', (e) => {
                if (sec !== activeElement) {
                    sec.style.outline = 'none';
                }
            });

            // Click selection
            sec.addEventListener('click', (e) => {
                if (window.previewMode === 'locked') return;
                e.stopPropagation();
                selectSection(sec);
            });
        });

        // Setup inline contenteditable fields
        FIELD_SELECTORS.forEach(item => {
            const nodes = document.querySelectorAll(item.selector);
            nodes.forEach(node => {
                if (window.previewMode === 'preview' || window.previewMode === 'locked') return;
                
                node.contentEditable = 'true';
                node.style.cursor = 'text';
                node.dataset.boundField = item.field;
                node.dataset.boundSection = item.section;

                node.addEventListener('focus', () => {
                    node.style.outline = '2px solid #3b82f6';
                    node.style.borderRadius = '4px';
                });

                node.addEventListener('input', () => {
                    const textVal = node.innerText || node.textContent;
                    window.parent.postMessage({
                        type: 'INLINE_TEXT_UPDATE',
                        field: item.field,
                        value: textVal
                    }, '*');
                });

                node.addEventListener('blur', () => {
                    node.style.outline = 'none';
                });
            });
        });
    }

    function selectSection(sec) {
        // Clear previous outline
        if (activeElement) {
            activeElement.style.outline = 'none';
        }

        activeElement = sec;
        sec.style.outline = '2px solid #3b82f6';
        sec.style.outlineOffset = '-2px';

        // Deduce section ID
        let sectionId = sec.id || sec.dataset.sectionId || 'personal';
        if (sectionId.includes('hero') || sectionId.includes('home')) sectionId = 'personal';
        else if (sectionId.includes('about') || sectionId.includes('bio')) sectionId = 'about';
        else if (sectionId.includes('skill')) sectionId = 'skills';
        else if (sectionId.includes('project') || sectionId.includes('work')) sectionId = 'projects';
        else if (sectionId.includes('exp') || sectionId.includes('career')) sectionId = 'experience';
        else if (sectionId.includes('edu')) sectionId = 'education';
        else if (sectionId.includes('cert')) sectionId = 'certificates';
        else if (sectionId.includes('service') || sectionId.includes('review') || sectionId.includes('testimonial')) sectionId = 'services';
        else if (sectionId.includes('contact')) sectionId = 'contact';
        else if (sectionId.includes('footer')) sectionId = 'settings';

        window.parent.postMessage({
            type: 'SELECT_SECTION',
            sectionId: sectionId,
            elementTagName: sec.tagName.toLowerCase()
        }, '*');
    }

    function setupContextMenuHandler() {
        document.addEventListener('contextmenu', (e) => {
            if (window.previewMode === 'locked') return;
            const targetSection = e.target.closest('section, header, footer, .portfolio-section, [data-section-id]');
            if (targetSection) {
                e.preventDefault();
                selectSection(targetSection);

                window.parent.postMessage({
                    type: 'OPEN_CONTEXT_MENU',
                    x: e.clientX,
                    y: e.clientY,
                    sectionId: targetSection.id || 'personal'
                }, '*');
            }
        });
    }

    function setupParentMessageListener() {
        window.addEventListener('message', (event) => {
            const data = event.data;
            if (!data || !data.type) return;

            if (data.type === 'HIGHLIGHT_SECTION') {
                const secId = data.sectionId;
                let target = document.getElementById(secId) || document.querySelector(`[data-section-id="${secId}"]`) || document.querySelector(`.${secId}`);
                
                if (!target) {
                    // Fallback search
                    const allSecs = Array.from(document.querySelectorAll('section, header, footer'));
                    target = allSecs.find(s => (s.id && s.id.includes(secId)) || (s.className && s.className.includes(secId)));
                }

                if (target) {
                    if (activeElement) activeElement.style.outline = 'none';
                    activeElement = target;
                    target.style.outline = '2px solid #3b82f6';
                    target.style.outlineOffset = '-2px';
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            } else if (data.type === 'SET_PREVIEW_MODE') {
                window.previewMode = data.mode; // 'edit', 'preview', 'locked'
            }
        });
    }
})();
