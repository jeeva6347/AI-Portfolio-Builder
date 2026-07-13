/**
 * static/js/theme_mapper.js
 * Visual Mapping Editor Frontend Logic (Module 6)
 */
document.addEventListener("DOMContentLoaded", function () {
    const iframe = document.getElementById("mapperFrame");
    const saveBtn = document.getElementById("saveBtn");
    const autoSuggestBtn = document.getElementById("autoSuggestBtn");
    const mappedCounter = document.getElementById("mappedCounter");
    const mappedList = document.getElementById("mappedList");
    const emptyMappedMsg = document.getElementById("emptyMappedMsg");
    
    // Inspector elements
    const noElementSelectedMsg = document.getElementById("noElementSelectedMsg");
    const elementInspectorForm = document.getElementById("elementInspectorForm");
    const inspectTag = document.getElementById("inspectTag");
    const inspectIndex = document.getElementById("inspectIndex");
    const inspectSelector = document.getElementById("inspectSelector");
    const inspectValuePreview = document.getElementById("inspectValuePreview");
    const fieldKeySelect = document.getElementById("fieldKeySelect");
    const attributeSelect = document.getElementById("attributeSelect");
    const customAttributeWrapper = document.getElementById("customAttributeWrapper");
    const customAttributeInput = document.getElementById("customAttributeInput");
    const isRequiredCheck = document.getElementById("isRequiredCheck");
    const addMappingFieldBtn = document.getElementById("addMappingFieldBtn");

    // Viewport resizing
    const vpRadios = document.querySelectorAll('input[name="viewport"]');
    const iframeWrapper = document.getElementById("iframeWrapper");

    // Local state
    let mappedFields = [...INITIAL_MAPPED_FIELDS]; // { id, field_key, selector, attribute, custom_attribute, is_required }
    let selectedElement = null; // { tag, selector, text, element }
    let suggestionsData = null;

    // ── Viewport resizing ──────────────────────────────────────────────────
    vpRadios.forEach(radio => {
        radio.addEventListener("change", function () {
            iframeWrapper.style.width = this.value;
        });
    });

    // ── Iframe Interactions (Same-Origin) ──────────────────────────────────
    if (iframe) {
        iframe.addEventListener("load", function () {
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                
                // 1. Inject highlighter stylesheet into iframe
                const style = doc.createElement("style");
                style.textContent = `
                    .mapper-highlighted {
                        outline: 2px dashed #3b82f6 !important;
                        cursor: pointer !important;
                    }
                    .mapper-selected {
                        outline: 2px solid #10b981 !important;
                        background-color: rgba(16, 185, 129, 0.1) !important;
                    }
                    .mapper-mapped-indicator {
                        outline: 1px dotted #8b5cf6 !important;
                        background-color: rgba(139, 92, 246, 0.05) !important;
                    }
                `;
                doc.head.appendChild(style);
                
                // Highlight already mapped elements
                updateIframeMappedIndicators();

                // 2. Element hover highlight and click interception
                doc.body.addEventListener("mouseover", function (e) {
                    if (e.target.classList.contains("mapper-selected")) return;
                    e.target.classList.add("mapper-highlighted");
                });

                doc.body.addEventListener("mouseout", function (e) {
                    e.target.classList.remove("mapper-highlighted");
                });

                doc.body.addEventListener("click", function (e) {
                    e.preventDefault();
                    e.stopPropagation();

                    // Remove current selection inside iframe
                    const currentSelected = doc.querySelector(".mapper-selected");
                    if (currentSelected) {
                        currentSelected.classList.remove("mapper-selected");
                    }

                    // Set target as selected
                    e.target.classList.add("mapper-selected");

                    // Deriving CSS selector for clicked element
                    const tag = e.target.tagName.toLowerCase();
                    const selector = getUniqueSelector(e.target);
                    const text = e.target.innerText || e.target.src || e.target.href || "";

                    selectedElement = {
                        tag: tag,
                        selector: selector,
                        text: text,
                        element: e.target
                    };

                    showInspector(tag, selector, text);
                });

            } catch (err) {
                console.error("Failed to access iframe DOM: ", err);
                alert("Same-origin access blocked or error loading iframe DOM.");
            }
        });
    }

    // Generate unique CSS selector
    function getUniqueSelector(el) {
        if (el.id) {
            return "#" + el.id;
        }
        if (el.tagName.toLowerCase() === "body") {
            return "body";
        }
        
        let path = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let selector = el.tagName.toLowerCase();
            if (el.className) {
                // Take first class name to avoid long class specificity
                const cls = el.className.split(" ")[0].trim();
                if (cls && !cls.startsWith("mapper-")) {
                    selector += "." + cls;
                }
            }
            
            // Fallback to nth-of-type if there are siblings
            let sibCount = 0;
            let sibIndex = 0;
            let sibling = el.parentNode ? el.parentNode.firstChild : null;
            while (sibling) {
                if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === el.tagName) {
                    sibCount++;
                    if (sibling === el) {
                        sibIndex = sibCount;
                    }
                }
                sibling = sibling.nextSibling;
            }
            if (sibCount > 1) {
                selector += `:nth-of-type(${sibIndex})`;
            }
            
            path.unshift(selector);
            el = el.parentNode;
        }
        return path.join(" > ");
    }

    // ── Inspector Controls ────────────────────────────────────────────────
    function showInspector(tag, selector, text) {
        noElementSelectedMsg.classList.add("d-none");
        elementInspectorForm.classList.remove("d-none");
        
        inspectTag.textContent = tag;
        inspectSelector.textContent = selector;
        inspectValuePreview.textContent = text ? text.substring(0, 150) : "No text/content";

        // Check if there is an existing mapping for this selector
        const existing = mappedFields.find(m => m.selector === selector);
        if (existing) {
            fieldKeySelect.value = existing.field_key;
            attributeSelect.value = existing.attribute;
            customAttributeInput.value = existing.custom_attribute || "";
            isRequiredCheck.checked = existing.is_required || false;
            addMappingFieldBtn.innerHTML = '<i class="bi bi-pencil-square"></i> Update Mapping';
        } else {
            // Default select options depending on tag
            fieldKeySelect.value = "";
            isRequiredCheck.checked = false;
            if (tag === "img") {
                attributeSelect.value = "src";
            } else if (tag === "a") {
                attributeSelect.value = "href";
            } else {
                attributeSelect.value = "text";
            }
            addMappingFieldBtn.innerHTML = '<i class="bi bi-plus-lg"></i> Apply Mapping';
        }
        
        toggleCustomAttributeWrapper();
    }

    attributeSelect.addEventListener("change", toggleCustomAttributeWrapper);
    
    function toggleCustomAttributeWrapper() {
        if (attributeSelect.value === "custom") {
            customAttributeWrapper.style.display = "block";
        } else {
            customAttributeWrapper.style.display = "none";
        }
    }

    // ── Mappings state management ──────────────────────────────────────────
    
    // Add or update mapping
    addMappingFieldBtn.addEventListener("click", function () {
        if (!selectedElement) return;
        const fieldKey = fieldKeySelect.value;
        if (!fieldKey) {
            alert("Please choose a portfolio field key.");
            return;
        }

        const attribute = attributeSelect.value;
        const customAttr = customAttributeInput.value;
        const isRequired = isRequiredCheck.checked;

        // check if this key is already mapped somewhere else
        const sameKeyIdx = mappedFields.findIndex(m => m.field_key === fieldKey);
        if (sameKeyIdx !== -1 && mappedFields[sameKeyIdx].selector !== selectedElement.selector) {
            if (!confirm(`Field '${fieldKey}' is already mapped to '${mappedFields[sameKeyIdx].selector}'. Replace it?`)) {
                return;
            }
            mappedFields.splice(sameKeyIdx, 1);
        }

        const idx = mappedFields.findIndex(m => m.selector === selectedElement.selector);
        const mappingField = {
            field_key: fieldKey,
            selector: selectedElement.selector,
            attribute: attribute,
            custom_attribute: customAttr,
            is_required: isRequired
        };

        if (idx !== -1) {
            mappedFields[idx] = mappingField;
        } else {
            mappedFields.push(mappingField);
        }

        // Reset visual indicators in IFrame and render sidebar list
        updateIframeMappedIndicators();
        renderMappedList();
        
        // Success alert or state change
        selectedElement = null;
        noElementSelectedMsg.classList.remove("d-none");
        elementInspectorForm.classList.add("d-none");
        
        // Remove active class inside iframe
        try {
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            doc.querySelector(".mapper-selected")?.classList.remove("mapper-selected");
        } catch (e) {}
    });

    // Render list in left sidebar
    function renderMappedList() {
        mappedCounter.textContent = mappedFields.length;
        if (mappedFields.length === 0) {
            emptyMappedMsg.classList.remove("d-none");
            // clear dynamic list elements
            document.querySelectorAll(".mapped-item-node").forEach(n => n.remove());
            return;
        }
        emptyMappedMsg.classList.add("d-none");
        document.querySelectorAll(".mapped-item-node").forEach(n => n.remove());

        mappedFields.forEach((item, i) => {
            const div = document.createElement("div");
            div.className = "mapped-item-node p-2.5 mb-2 bg-gray-50 dark:bg-gray-700/20 border border-gray-100 dark:border-gray-700 rounded-lg d-flex align-items-center justify-content-between hover:border-blue-300 transition-colors";
            div.innerHTML = `
                <div class="overflow-hidden me-2">
                    <p class="text-xs fw-bold text-gray-800 dark:text-gray-200 mb-0 font-mono text-truncate">${item.field_key}</p>
                    <p class="text-xxs text-gray-400 font-mono text-truncate mb-0" title="${item.selector}">${item.selector}</p>
                </div>
                <button class="btn btn-xs btn-outline-danger rounded-circle p-1 flex items-center justify-center remove-map-btn" style="width:20px;height:20px;" data-index="${i}">
                    <i class="bi bi-x text-xs"></i>
                </button>
            `;
            mappedList.appendChild(div);
        });

        // Add delete event listeners
        document.querySelectorAll(".remove-map-btn").forEach(btn => {
            btn.addEventListener("click", function (e) {
                e.stopPropagation();
                const index = parseInt(this.getAttribute("data-index"));
                mappedFields.splice(index, 1);
                updateIframeMappedIndicators();
                renderMappedList();
            });
        });
    }

    // Update highlights of mapped elements inside iframe
    function updateIframeMappedIndicators() {
        try {
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc) return;
            
            // clear old classes
            doc.querySelectorAll(".mapper-mapped-indicator").forEach(el => {
                el.classList.remove("mapper-mapped-indicator");
            });

            // apply new indicators
            mappedFields.forEach(item => {
                const el = doc.querySelector(item.selector);
                if (el) {
                    el.classList.add("mapper-mapped-indicator");
                }
            });
        } catch (e) {}
    }

    // ── Auto-suggest mappings ──────────────────────────────────────────────
    autoSuggestBtn.addEventListener("click", function () {
        autoSuggestBtn.disabled = true;
        autoSuggestBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Scanning...';

        fetch(SCAN_SUGGESTIONS_URL)
            .then(res => res.json())
            .then(data => {
                suggestionsData = data;
                const count = suggestionsData.suggestions.length;
                if (count === 0) {
                    alert("No strong mapping recommendations could be detected automatically.");
                } else {
                    let added = 0;
                    suggestionsData.suggestions.forEach(s => {
                        // Avoid overwriting existing user-defined mapping for the selector
                        if (!mappedFields.some(m => m.selector === s.selector || m.field_key === s.field_key)) {
                            mappedFields.push({
                                field_key: s.field_key,
                                selector: s.selector,
                                attribute: s.field_key.endsWith(".photo") || s.field_key.endsWith(".cover") || s.field_key.endsWith(".image") ? "src" : (s.field_key.includes("url") ? "href" : "text"),
                                custom_attribute: "",
                                is_required: false
                            });
                            added++;
                        }
                    });
                    
                    updateIframeMappedIndicators();
                    renderMappedList();
                    alert(`HTML scanner scan complete! Auto-mapped ${added} recommended elements with high confidence.`);
                }
            })
            .catch(err => {
                console.error("Scanner failed: ", err);
                alert("Error during HTML scanning.");
            })
            .finally(() => {
                autoSuggestBtn.disabled = false;
                autoSuggestBtn.innerHTML = '<i class="bi bi-magic"></i> Auto-Suggest Mappings';
            });
    });

    // ── Save Mappings API POST ──────────────────────────────────────────────
    saveBtn.addEventListener("click", function () {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

        fetch(SAVE_MAPPINGS_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken()
            },
            body: JSON.stringify({ fields: mappedFields })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`SUCCESS: All ${data.saved_count} mapping fields saved successfully!`);
            } else {
                alert("ERROR: " + (data.error || "Failed to save mapping fields."));
            }
        })
        .catch(err => {
            console.error("Save failed: ", err);
            alert("Network error saving mappings.");
        })
        .finally(() => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-lg"></i> Save Mapping';
        });
    });

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || "";
    }

    // Initial render
    renderMappedList();
});
