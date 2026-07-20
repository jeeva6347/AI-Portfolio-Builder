/**
 * Professional SaaS Visual Builder App Engine (Phase 6.3 UI)
 * Powered by Alpine.js, SortableJS & HTMX.
 * Controls 3-column workspace, inline text sync, component tree, command palette, context menu, version history drawer & diff modal.
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('builderApp', () => ({
        // Sidebar & Panel States
        leftSidebarOpen: true,
        rightSidebarOpen: true,
        activeTab: 'form', // 'form' or 'tree'
        
        // Preview & Edit Modes
        builderMode: 'edit', // 'edit', 'preview', 'locked'
        viewportMode: 'view-desktop', // 'view-desktop', 'view-tablet', 'view-mobile'
        frameZoom: 1.0,

        // Modals & Overlays
        showThemeModal: false,
        showComponentLibraryModal: false,
        showShortcutsModal: false,
        showVersionDrawer: false,
        showCompareModal: false,
        commandPaletteOpen: false,
        commandSearch: '',

        // Version History State
        versionList: [],
        versionDiff: null,
        selectedCompareV1: null,
        selectedCompareV2: null,

        // Context Menu State
        contextMenu: {
            open: false,
            x: 0,
            y: 0,
            sectionId: null
        },

        // Component Selection & Breadcrumbs
        selectedSection: 'personal',
        breadcrumbs: ['Portfolio', 'Personal Info'],

        // Search & Accordions
        sectionSearch: '',
        openSections: {
            personal: true,
            about: false,
            skills: false,
            projects: false,
            experience: false,
            education: false,
            certificates: false,
            services: false,
            contact: false,
            socials: false,
            seo: false,
            settings: false
        },
        hiddenSections: {},

        // Save & Published Status
        saveStatus: 'Saved', // 'Saving...', 'Saved', 'Retrying...', 'Failed'
        isDraftModified: true, // Shows 'You have unpublished changes' banner if true
        lastSavedTime: 'Just now',
        retryCount: 0,

        // Theme Customization (Right Panel)
        primaryColor: '#3b82f6',
        secondaryColor: '#64748b',
        accentColor: '#f59e0b',
        fontFamily: 'Inter',
        borderRadius: '8',
        buttonStyle: 'rounded-pill',
        enableAnimations: true,
        enableGlass: true,
        customCss: '',

        // Toast System
        toasts: [],

        init() {
            this.setupKeyboardShortcuts();
            this.setupAutosaveListener();
            this.setupIframeMessageListener();
            this.setupSortableJS();

            // Close context menu on outside click
            window.addEventListener('click', () => {
                this.contextMenu.open = false;
            });
        },

        // --- VERSION HISTORY UI ACTIONS (Phase 6.3) ---
        openVersionHistoryDrawer() {
            this.showVersionDrawer = true;
            this.loadVersionHistory();
        },

        loadVersionHistory() {
            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const listUrl = form.getAttribute('data-version-list-url');
            if (!listUrl) return;

            fetch(listUrl)
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.versionList = data.versions;
                    }
                })
                .catch(err => console.error("Error loading version history:", err));
        },

        restoreVersion(versionId, versionNumber) {
            if (!confirm(`Are you sure you want to restore Version #${versionNumber}? A new Rollback version will be created.`)) return;

            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const restoreBaseUrl = form.getAttribute('data-version-restore-base-url');
            if (!restoreBaseUrl) return;

            const restoreUrl = `${restoreBaseUrl}${versionId}/restore/`;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(restoreUrl, { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.addToast(data.message, 'success');
                        setTimeout(() => window.location.reload(), 800);
                    } else {
                        this.addToast('Failed to restore version', 'danger');
                    }
                })
                .catch(err => {
                    console.error("Restore error:", err);
                    this.addToast('Failed to restore version', 'danger');
                });
        },

        compareVersions(v1Id, v2Id) {
            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const compareUrl = form.getAttribute('data-version-compare-url');
            if (!compareUrl) return;

            const fd = new FormData();
            fd.append('version_a_id', v1Id);
            fd.append('version_b_id', v2Id);
            fd.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(compareUrl, { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.versionDiff = data.diff;
                        this.showCompareModal = true;
                    }
                })
                .catch(err => console.error("Compare error:", err));
        },

        // --- SECTION SELECTION & BREADCRUMBS ---
        selectSection(sectionId, fieldName = null) {
            this.selectedSection = sectionId;
            this.openSections[sectionId] = true;
            this.updateBreadcrumbs(sectionId);

            const iframe = document.getElementById('userPreviewFrame');
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.postMessage({
                    type: 'HIGHLIGHT_SECTION',
                    sectionId: sectionId
                }, '*');
            }

            const secCard = document.getElementById(`accordion_${sectionId}`);
            if (secCard) {
                secCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        },

        updateBreadcrumbs(sectionId) {
            const labelMap = {
                personal: 'Personal Info',
                about: 'About Biography',
                skills: 'Skills & Stack',
                projects: 'Projects & Work',
                experience: 'Work Experience',
                education: 'Education',
                certificates: 'Certifications',
                services: 'Reviews & Services',
                contact: 'Contact Details',
                socials: 'Social Links',
                seo: 'SEO Settings',
                settings: 'Footer & Settings'
            };
            this.breadcrumbs = ['Portfolio', labelMap[sectionId] || sectionId];
        },

        setBuilderMode(mode) {
            this.builderMode = mode;
            this.addToast(`Switched to ${mode.toUpperCase()} mode`, 'info');
            
            const iframe = document.getElementById('userPreviewFrame');
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.postMessage({
                    type: 'SET_PREVIEW_MODE',
                    mode: mode
                }, '*');
            }
        },

        // --- COMMAND PALETTE (Ctrl+K) ---
        toggleCommandPalette() {
            this.commandPaletteOpen = !this.commandPaletteOpen;
            if (this.commandPaletteOpen) {
                this.commandSearch = '';
                this.$nextTick(() => {
                    const input = document.getElementById('commandPaletteInput');
                    if (input) input.focus();
                });
            }
        },

        executeCommand(cmd) {
            this.commandPaletteOpen = false;
            if (cmd === 'add_project') this.addComponent('projects');
            else if (cmd === 'add_experience') this.addComponent('experience');
            else if (cmd === 'add_skill') this.addComponent('skills');
            else if (cmd === 'change_theme') this.showThemeModal = true;
            else if (cmd === 'shortcuts') this.showShortcutsModal = true;
            else if (cmd === 'versions') this.openVersionHistoryDrawer();
            else if (cmd === 'publish') {
                const btn = document.getElementById('publishBtn');
                if (btn) btn.click();
            }
        },

        // --- CONTEXT MENU ---
        openContextMenu(x, y, sectionId) {
            this.contextMenu.x = Math.min(x, window.innerWidth - 180);
            this.contextMenu.y = Math.min(y, window.innerHeight - 220);
            this.contextMenu.sectionId = sectionId;
            this.contextMenu.open = true;
        },

        // --- AJAX CRUD ACTIONS ---
        addComponent(componentType) {
            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const addUrl = form.getAttribute('data-add-component-url');
            if (!addUrl) return;

            const fd = new FormData();
            fd.append('component_type', componentType);
            fd.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(addUrl, { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.addToast(data.message, 'success');
                        this.refreshPreview();
                        window.location.reload();
                    }
                });
        },

        duplicateItem(itemType, itemId) {
            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const dupUrl = form.getAttribute('data-duplicate-item-url');
            if (!dupUrl) return;

            const fd = new FormData();
            fd.append('item_type', itemType);
            fd.append('item_id', itemId);
            fd.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(dupUrl, { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.addToast('Item duplicated successfully', 'success');
                        window.location.reload();
                    }
                });
        },

        // --- SORTABLE JS REORDERING ---
        setupSortableJS() {
            if (typeof Sortable === 'undefined') return;

            ['projects', 'experiences', 'educations', 'certificates', 'services', 'testimonials'].forEach(listType => {
                const container = document.getElementById(`sortable_${listType}`);
                if (container) {
                    Sortable.create(container, {
                        handle: '.drag-handle',
                        animation: 150,
                        onEnd: (evt) => {
                            const orderIds = Array.from(container.children).map(el => el.dataset.id).filter(Boolean);
                            this.saveOrder(listType, orderIds);
                        }
                    });
                }
            });
        },

        saveOrder(itemType, orderIds) {
            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const reorderUrl = form.getAttribute('data-reorder-url');
            if (!reorderUrl) return;

            const fd = new FormData();
            fd.append('item_type', itemType);
            fd.append('order_ids', JSON.stringify(orderIds));
            fd.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(reorderUrl, { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        this.addToast(`Reordered ${itemType}`, 'success');
                        this.refreshPreview();
                    }
                });
        },

        // --- IFRAME MESSAGE LISTENER ---
        setupIframeMessageListener() {
            window.addEventListener('message', (evt) => {
                const data = evt.data;
                if (!data || !data.type) return;

                if (data.type === 'SELECT_SECTION') {
                    this.selectSection(data.sectionId);
                } else if (data.type === 'INLINE_TEXT_UPDATE') {
                    const fieldInput = document.querySelector(`[name="${data.field}"]`);
                    if (fieldInput) {
                        fieldInput.value = data.value;
                        fieldInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                } else if (data.type === 'OPEN_CONTEXT_MENU') {
                    this.openContextMenu(data.x, data.y, data.sectionId);
                }
            });
        },

        // --- ACCORDION & SEARCH CONTROLS ---
        toggleSection(secKey) {
            this.openSections[secKey] = !this.openSections[secKey];
            if (this.openSections[secKey]) {
                this.selectSection(secKey);
            }
        },

        expandAllSections() {
            Object.keys(this.openSections).forEach(k => this.openSections[k] = true);
        },

        collapseAllSections() {
            Object.keys(this.openSections).forEach(k => this.openSections[k] = false);
        },

        toggleHideSection(secKey) {
            this.hiddenSections[secKey] = !this.hiddenSections[secKey];
            this.addToast(this.hiddenSections[secKey] ? `Hidden ${secKey}` : `Restored ${secKey}`, 'info');
        },

        matchesSearch(secName, keywords = []) {
            if (!this.sectionSearch.trim()) return true;
            const q = this.sectionSearch.toLowerCase();
            if (secName.toLowerCase().includes(q)) return true;
            return keywords.some(k => k.toLowerCase().includes(q));
        },

        // --- VIEWPORT & CANVAS ZOOM ---
        setViewport(mode) {
            this.viewportMode = mode;
            this.frameZoom = 1.0;
            this.applyFrameZoom();
        },

        zoomIn() {
            this.frameZoom = Math.min(1.5, this.frameZoom + 0.1);
            this.applyFrameZoom();
        },

        zoomOut() {
            this.frameZoom = Math.max(0.4, this.frameZoom - 0.1);
            this.applyFrameZoom();
        },

        resetZoom() {
            this.frameZoom = 1.0;
            this.applyFrameZoom();
        },

        applyFrameZoom() {
            const wrapper = document.getElementById('frameZoomWrapper');
            if (wrapper) {
                wrapper.style.transform = `scale(${this.frameZoom})`;
                wrapper.style.transformOrigin = 'top center';
            }
        },

        // --- AUTOSAVE ENGINE WITH RETRIES ---
        triggerSaving() {
            this.saveStatus = 'Saving...';
            this.isDraftModified = true;
        },

        markSaved() {
            this.saveStatus = 'Saved';
            this.retryCount = 0;
            const now = new Date();
            this.lastSavedTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },

        setupAutosaveListener() {
            const form = document.getElementById('builderMainForm');
            if (!form) return;

            let timer = null;
            const updateUrl = form.getAttribute('data-update-url');

            const inputs = form.querySelectorAll('input:not([type="file"]), textarea, select');
            inputs.forEach(input => {
                input.addEventListener('input', () => {
                    this.triggerSaving();
                    clearTimeout(timer);
                    timer = setTimeout(() => this.performAutosave(form, updateUrl), 800);
                });
                input.addEventListener('change', () => {
                    this.triggerSaving();
                    clearTimeout(timer);
                    timer = setTimeout(() => this.performAutosave(form, updateUrl), 300);
                });
            });
        },

        performAutosave(form, updateUrl) {
            if (!updateUrl) return;
            const formData = new FormData(form);

            fetch(updateUrl, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    this.markSaved();
                    this.refreshPreview();
                } else {
                    this.handleSaveError(form, updateUrl);
                }
            })
            .catch(err => {
                console.error("Autosave error:", err);
                this.handleSaveError(form, updateUrl);
            });
        },

        handleSaveError(form, updateUrl) {
            if (this.retryCount < 3) {
                this.retryCount++;
                this.saveStatus = `Retrying (${this.retryCount}/3)...`;
                setTimeout(() => this.performAutosave(form, updateUrl), 1500);
            } else {
                this.saveStatus = 'Failed';
                this.addToast('Auto-save failed. Check connection.', 'danger');
            }
        },

        refreshPreview() {
            const form = document.getElementById('builderMainForm');
            if (!form) return;
            const previewUrl = form.getAttribute('data-preview-url');
            const iframe = document.getElementById('userPreviewFrame');
            if (!iframe || !previewUrl) return;

            fetch(previewUrl)
                .then(res => res.text())
                .then(html => {
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    doc.open();
                    doc.write(html);
                    doc.close();
                })
                .catch(err => console.error("Preview refresh failed:", err));
        },

        // --- KEYBOARD SHORTCUTS ENGINE ---
        setupKeyboardShortcuts() {
            window.addEventListener('keydown', (e) => {
                const targetTag = e.target.tagName.toLowerCase();
                const isTyping = ['input', 'textarea', 'select'].includes(targetTag) || e.target.isContentEditable;

                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    this.toggleCommandPalette();
                    return;
                }

                if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                    e.preventDefault();
                    const form = document.getElementById('builderMainForm');
                    if (form) form.requestSubmit();
                    this.addToast('Draft saved', 'success');
                    return;
                }

                if (e.key === '?' && !isTyping) {
                    e.preventDefault();
                    this.showShortcutsModal = true;
                    return;
                }

                if (e.key === 'Escape') {
                    this.commandPaletteOpen = false;
                    this.showThemeModal = false;
                    this.showComponentLibraryModal = false;
                    this.showShortcutsModal = false;
                    this.showVersionDrawer = false;
                    this.showCompareModal = false;
                    this.contextMenu.open = false;
                }
            });
        },

        // --- TOAST SYSTEM ---
        addToast(msg, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, msg, type });
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 3000);
        },

        removeToast(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        }
    }));
});
