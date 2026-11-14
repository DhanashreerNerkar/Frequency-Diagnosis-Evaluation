const API_BASE_URL = '/api/v1/audit/lookup';
let currentPage = 1;
const PAGE_LIMIT = 10;
let totalPages = 0;
let totalItems = 0;
let currentItems = [];
let reviewerId = null;
let currentStatus = 'new';
let currentSearch = '';

const statusFilter = document.getElementById('statusFilter');
const confirmModal = document.getElementById('confirmModal');
const modalMessage = document.getElementById('modalMessage');
const modalCancel = document.getElementById('modalCancel');
const modalConfirm = document.getElementById('modalConfirm');

const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const reviewTableContainer = document.getElementById('reviewTableContainer');
const reviewTableBody = document.getElementById('reviewTableBody');
const emptyState = document.getElementById('emptyState');
const reviewForm = document.getElementById('reviewForm');
const submitBtn = document.getElementById('submitBtn');
const pageInfo = document.getElementById('pageInfo');
const paginationContainer = document.getElementById('paginationContainer');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');

const searchInput = document.getElementById('searchInput');      
const searchBtn = document.getElementById('searchBtn');
const clearSearchBtn = document.getElementById('clearSearchBtn');
const editModeBtn = document.getElementById('editModeBtn');

const STORAGE_KEY = 'synonym_review_selections';

function initializeReviewer() {
    reviewerId = localStorage.getItem('reviewer_id');
    
    if (!reviewerId) {
        reviewerId = `reviewer_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
        localStorage.setItem('reviewer_id', reviewerId);
    }
    
    console.log('Reviewer ID:', reviewerId);
}

function saveSelectionsToStorage() {
    try {
        const allSelections = getAllCurrentSelections();
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(allSelections));
    } catch (e) {
        console.error('Failed to save selections:', e);
    }
}

function loadSelectionsFromStorage() {
    try {
        const stored = sessionStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch (e) {
        console.error('Failed to load selections:', e);
        return {};
    }
}

function getAllCurrentSelections() {
    const selections = loadSelectionsFromStorage();
    
    const rows = reviewTableBody.querySelectorAll('tr');
    rows.forEach(row => {
        const synonymId = parseInt(row.dataset.synonymId);
        const icd11Code = row.dataset.icd11Code;
        const action = row.dataset.selectedAction;
        const key = `${icd11Code}_${synonymId}`;
        
        if (action) {
            selections[key] = action;
        } else {
            delete selections[key];
        }
    });
    
    return selections;
}

function clearSelectionsForItems(items) {
    const selections = loadSelectionsFromStorage();
    items.forEach(item => {
        const key = `${item.icd11_code}_${item.synonym_id}`;
        delete selections[key];
    });
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(selections));
}

function restoreCurrentPageSelections() {
    const selections = loadSelectionsFromStorage();
    const rows = reviewTableBody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const synonymId = parseInt(row.dataset.synonymId);
        const icd11Code = row.dataset.icd11Code;
        const key = `${icd11Code}_${synonymId}`;
        
        const savedAction = selections[key];
        if (savedAction) {
            const correctBtn = row.querySelector('.btn-correct');
            const wrongBtn = row.querySelector('.btn-wrong');
            
            if (savedAction === 'correct' && correctBtn) {
                correctBtn.classList.add('selected');
                row.dataset.selectedAction = 'correct';
            } else if (savedAction === 'wrong' && wrongBtn) {
                wrongBtn.classList.add('selected');
                row.dataset.selectedAction = 'wrong';
            }
        }
    });
}

function performSearch() {
    currentSearch = searchInput.value.trim();
    currentPage = 1;
    updateClearButtonVisibility();
    loadSynonyms();
}

function clearSearch() {
    searchInput.value = '';
    currentSearch = '';
    currentPage = 1;
    updateClearButtonVisibility();
    loadSynonyms();
}

function updateClearButtonVisibility() {
    if (currentSearch) {
        clearSearchBtn.classList.remove('hidden');
    } else {
        clearSearchBtn.classList.add('hidden');
    }
}

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing...');
    
    initializeReviewer();
    updateClearButtonVisibility();
    
    // Hide the global edit button - we use per-item edit now
    if (editModeBtn) {
        editModeBtn.style.display = 'none';
    }
    
    // Event listeners
    statusFilter.addEventListener('change', () => {
        currentStatus = statusFilter.value;
        console.log('Status changed to:', currentStatus);
        currentPage = 1;
        loadSynonyms();
    });

    searchBtn.addEventListener('click', performSearch);
    clearSearchBtn.addEventListener('click', clearSearch);

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        }
    });

    reviewForm.addEventListener('submit', handleSubmit);
    prevBtn.addEventListener('click', () => {
        saveSelectionsToStorage();
        goToPage(currentPage - 1);
    });
    nextBtn.addEventListener('click', () => {
        saveSelectionsToStorage();
        goToPage(currentPage + 1);
    });
    
    loadSynonyms();
});

async function loadSynonyms(showLoadingIndicator = true) {
    if (showLoadingIndicator) {
        showLoading();
    }
    hideError();
    hideEmptyState();
    hideTable();

    try {
        const endpoint =
          currentStatus === 'new'
            ? `${API_BASE_URL}/doctor/review`
            : `${API_BASE_URL}/doctor/synonyms`;

        const params = new URLSearchParams({
            status: currentStatus,
            page: currentPage,
            limit: PAGE_LIMIT
        });

        if (currentSearch) {
            params.append('search', currentSearch);
        }

        const response = await fetch(
            `${endpoint}?${params.toString()}`,
            {
                headers: {
                    'X-Reviewer-Id': reviewerId
                }
            }
        );

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log('API Response:', data);
        
        currentItems = data.items || [];
        totalItems = data.total || 0;
        totalPages = data.total_pages || 0;

        if (currentItems.length === 0) {
            showEmptyState();
        } else {
            displayTable(currentItems);
            restoreCurrentPageSelections();
            updatePagination();
        }

    } catch (error) {
        console.error('Error loading synonyms:', error);
        showError(`Failed to load synonyms: ${error.message}`);
    } finally {
        if (showLoadingIndicator) {
            hideLoading();
        }
    }
}

function displayTable(items) {
    reviewTableBody.innerHTML = '';
    
    console.log(`Displaying ${items.length} items. Status: ${currentStatus}`);

    items.forEach((item) => {
        const row = document.createElement('tr');
        row.dataset.synonymId = item.synonym_id;
        row.dataset.icd11Code = item.icd11_code;
        row.dataset.originalStatus = item.status;
        row.dataset.isEditing = 'false';
        
        const isReviewed = (item.status === 'cleared' || item.status === 'wrong');
        
        row.innerHTML = `
            <td class="synonym-cell">
                <div class="synonym-text">${escapeHtml(item.synonym_text)}</div>
                <div class="synonym-id">ID: ${item.synonym_id}</div>
            </td>
            <td class="code-cell">${escapeHtml(item.who_code)}</td>
            <td class="diagnosis-cell">${escapeHtml(item.who_diagnosis)}</td>
            <td class="code-cell">${escapeHtml(item.nih_code)}</td>
            <td class="diagnosis-cell">${escapeHtml(item.nih_diagnosis)}</td>
            <td class="action-cell">
                <button type="button" class="btn-action btn-correct" 
                    data-synonym-id="${item.synonym_id}" 
                    data-action="correct"
                    ${isReviewed ? 'disabled' : ''}>
                    Same
                </button>
            </td>
            <td class="action-cell">
                <button type="button" class="btn-action btn-wrong" 
                    data-synonym-id="${item.synonym_id}" 
                    data-action="wrong"
                    ${isReviewed ? 'disabled' : ''}>
                    Different
                </button>
            </td>
            <td class="edit-cell">
                ${isReviewed ? `
                    <button type="button" class="btn-edit" data-synonym-id="${item.synonym_id}">
                        Edit
                    </button>
                    <button type="button" class="btn-save hidden" data-synonym-id="${item.synonym_id}">
                        Save
                    </button>
                    <button type="button" class="btn-cancel hidden" data-synonym-id="${item.synonym_id}">
                        Cancel
                    </button>
                ` : ''}
            </td>
        `;
        
        const correctBtn = row.querySelector('.btn-correct');
        const wrongBtn = row.querySelector('.btn-wrong');
        const editBtn = row.querySelector('.btn-edit');
        const saveBtn = row.querySelector('.btn-save');
        const cancelBtn = row.querySelector('.btn-cancel');

        // Set initial button states based on item status
        if (item.status === 'cleared') {
            correctBtn.classList.add('selected');
            row.dataset.selectedAction = 'correct';
        } else if (item.status === 'wrong') {
            wrongBtn.classList.add('selected');
            row.dataset.selectedAction = 'wrong';
        }
        
        // Apply visual feedback for disabled buttons
        if (isReviewed) {
            correctBtn.style.opacity = '0.6';
            correctBtn.style.cursor = 'not-allowed';
            wrongBtn.style.opacity = '0.6';
            wrongBtn.style.cursor = 'not-allowed';
        }
        
        // Edit button click handler
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                enterEditMode(row, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
            });
        }
        
        // Save button click handler
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                await saveItemEdit(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
            });
        }
        
        // Cancel button click handler
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                exitEditMode(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
            });
        }
        
        // Correct/Wrong button handlers (only work when not disabled)
        correctBtn.addEventListener('click', () => {
            if (correctBtn.disabled) return;
            
            if (correctBtn.classList.contains('selected')) {
                correctBtn.classList.remove('selected');
                delete row.dataset.selectedAction;
            } else {
                wrongBtn.classList.remove('selected');
                correctBtn.classList.add('selected');
                row.dataset.selectedAction = 'correct';
            }
            saveSelectionsToStorage();
        });
        
        wrongBtn.addEventListener('click', () => {
            if (wrongBtn.disabled) return;
            
            if (wrongBtn.classList.contains('selected')) {
                wrongBtn.classList.remove('selected');
                delete row.dataset.selectedAction;
            } else {
                correctBtn.classList.remove('selected');
                wrongBtn.classList.add('selected');
                row.dataset.selectedAction = 'wrong';
            }
            saveSelectionsToStorage();
        });
        
        reviewTableBody.appendChild(row);
    });
    
    showTable();
}

function enterEditMode(row, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn) {
    console.log('Entering edit mode for item:', row.dataset.synonymId);
    
    row.dataset.isEditing = 'true';
    row.dataset.originalAction = row.dataset.selectedAction;
    
    // Enable buttons
    correctBtn.disabled = false;
    wrongBtn.disabled = false;
    correctBtn.style.opacity = '1';
    correctBtn.style.cursor = 'pointer';
    wrongBtn.style.opacity = '1';
    wrongBtn.style.cursor = 'pointer';
    
    // Show/hide action buttons
    editBtn.classList.add('hidden');
    saveBtn.classList.remove('hidden');
    cancelBtn.classList.remove('hidden');
    
    // Add visual indicator
    row.style.backgroundColor = '#fff3cd';
}

function exitEditMode(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn) {
    console.log('Exiting edit mode for item:', row.dataset.synonymId);
    
    row.dataset.isEditing = 'false';
    
    // Restore original selection
    const originalAction = row.dataset.originalAction;
    correctBtn.classList.remove('selected');
    wrongBtn.classList.remove('selected');
    
    if (originalAction === 'correct') {
        correctBtn.classList.add('selected');
        row.dataset.selectedAction = 'correct';
    } else if (originalAction === 'wrong') {
        wrongBtn.classList.add('selected');
        row.dataset.selectedAction = 'wrong';
    }
    
    // Disable buttons
    correctBtn.disabled = true;
    wrongBtn.disabled = true;
    correctBtn.style.opacity = '0.6';
    correctBtn.style.cursor = 'not-allowed';
    wrongBtn.style.opacity = '0.6';
    wrongBtn.style.cursor = 'not-allowed';
    
    // Show/hide action buttons
    editBtn.classList.remove('hidden');
    saveBtn.classList.add('hidden');
    cancelBtn.classList.add('hidden');
    
    // Remove visual indicator
    row.style.backgroundColor = '';
    
    delete row.dataset.originalAction;
}

async function saveItemEdit(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn) {
    const newAction = row.dataset.selectedAction;
    const originalAction = row.dataset.originalAction;
    
    if (!newAction) {
        showError('Please select Same or Different before saving.');
        return;
    }
    
    if (newAction === originalAction) {
        showError('No changes made.');
        exitEditMode(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
        return;
    }
    
    console.log(`Saving edit: ${item.icd11_code}/${item.synonym_id} - ${originalAction} → ${newAction}`);
    
    // Disable save button during request
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    
    try {
        const payload = {
            items: [{
                icd11_code: item.icd11_code,
                synonym_id: item.synonym_id,
                action: newAction
            }],
            reviewed_by: reviewerId
        };
        
        const response = await fetch(`${API_BASE_URL}/doctor/review/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Reviewer-Id': reviewerId
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            
            if (response.status === 409) {
                showError('Item is locked by another user. Please try again.');
                exitEditMode(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
                return;
            }
            
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.successful > 0) {
            const newStatus = newAction === 'correct' ? 'cleared' : 'wrong';
            
            // Check if the new status matches current filter
            const statusChanged = (originalAction === 'correct' && newAction === 'wrong') || 
                                 (originalAction === 'wrong' && newAction === 'correct');
            
            if (statusChanged && (currentStatus === 'cleared' || currentStatus === 'wrong')) {
                // Status changed and doesn't match current filter - remove from page
                showSuccess(`Review updated! Item moved to ${newAction === 'correct' ? 'Same' : 'Different'} list.`);
                
                // Fade out and remove the row
                row.style.transition = 'opacity 0.3s ease-out';
                row.style.opacity = '0';
                
                setTimeout(() => {
                    row.remove();
                    
                    // Update current items array
                    currentItems = currentItems.filter(i => 
                        !(i.icd11_code === item.icd11_code && i.synonym_id === item.synonym_id)
                    );
                    
                    // If page is now empty, reload to show updated data
                    if (currentItems.length === 0) {
                        setTimeout(() => loadSynonyms(), 500);
                    }
                }, 300);
            } else {
                // Status didn't change or we're viewing "all" - update in place
                showSuccess('Review updated successfully!');
                
                // Update row state
                row.dataset.originalStatus = newStatus;
                row.dataset.isEditing = 'false';
                row.dataset.originalAction = newAction;
                
                // Exit edit mode
                correctBtn.disabled = true;
                wrongBtn.disabled = true;
                correctBtn.style.opacity = '0.6';
                correctBtn.style.cursor = 'not-allowed';
                wrongBtn.style.opacity = '0.6';
                wrongBtn.style.cursor = 'not-allowed';
                
                editBtn.classList.remove('hidden');
                saveBtn.classList.add('hidden');
                cancelBtn.classList.add('hidden');
                
                row.style.backgroundColor = '';
                
                delete row.dataset.originalAction;
            }
        } else {
            showError('Failed to update review.');
            exitEditMode(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
        }
        
    } catch (error) {
        console.error('Error saving edit:', error);
        showError(`Failed to save: ${error.message}`);
        exitEditMode(row, item, correctBtn, wrongBtn, editBtn, saveBtn, cancelBtn);
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save';
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    
    // Only for "new" status items
    if (currentStatus !== 'new') {
        showError('Batch submit is only available for pending review items.');
        return;
    }
    
    const reviewItems = [];
    const unselectedItems = [];
    const rows = reviewTableBody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const synonymId = parseInt(row.dataset.synonymId);
        const icd11Code = row.dataset.icd11Code;
        const synonymText = row.querySelector('.synonym-text')?.textContent || `ID: ${synonymId}`;
        const action = row.dataset.selectedAction || null;
        
        if (action) {
            reviewItems.push({
                icd11_code: icd11Code,
                synonym_id: synonymId,
                action: action
            });
        } else {
            unselectedItems.push({
                synonym_id: synonymId,
                synonym_text: synonymText
            });
        }
    });
    
    if (reviewItems.length === 0) {
        showError('Please select a review action (Same / Different) for at least one item.');
        return;
    }

    if (unselectedItems.length > 0) {
        const message = `You have ${unselectedItems.length} unreviewed item(s) in this page. Do you want to submit only the reviewed items?`;
        
        const userChoice = await showModal(message);
        
        if (!userChoice) {
            return;
        }
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    
    try {
        const payload = {
            items: reviewItems,
            reviewed_by: reviewerId
        };
        
        const response = await fetch(`${API_BASE_URL}/doctor/review/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Reviewer-Id': reviewerId
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
      
            if (response.status === 409) {
                showError('Some items were locked by another user. Refreshing...');
                setTimeout(() => {
                    clearSelectionsForItems(reviewItems);
                    loadSynonyms();
                }, 2000);
                return;
            }
            
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        let message = `Successfully submitted ${result.successful} review(s).`;
        if (result.failed > 0) {
            message += ` ${result.failed} failed.`;
        }
        
        showSuccess(message);
        
        clearSelectionsForItems(reviewItems);
        
        setTimeout(() => loadSynonyms(), 1500);
        
    } catch (error) {
        console.error('Error submitting review:', error);
        showError(`Failed to submit review: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Page';
    }
}

function goToPage(page) {
    if (page < 1 || page > totalPages) {
        return;
    }
    
    currentPage = page;
    loadSynonyms();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updatePagination() {
    if (!totalPages || totalPages <= 0 || !totalItems || totalItems <= 0) {
        if (paginationContainer) paginationContainer.classList.add('hidden');
        if (pageInfo) pageInfo.textContent = '';
        return;
    }

    if (currentPage < 1) currentPage = 1;
    if (currentPage > totalPages) currentPage = totalPages;

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;

    paginationContainer.classList.remove('hidden');
}

function showLoading() {
    if (loadingDiv) loadingDiv.classList.remove('hidden');
}

function hideLoading() {
    if (loadingDiv) loadingDiv.classList.add('hidden');
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    errorDiv.className = 'error';
    setTimeout(() => hideError(), 5000);
}

function showSuccess(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    errorDiv.className = 'error success';
    setTimeout(() => hideError(), 3000);
}

function hideError() {
    errorDiv.classList.add('hidden');
}

function showTable() {
    reviewTableContainer.classList.remove('hidden');
}

function hideTable() {
    reviewTableContainer.classList.add('hidden');
}

function showEmptyState() {
    const emptyStateTitle = emptyState.querySelector('p:first-of-type');
    const emptyStateSubtitle = emptyState.querySelector('.empty-subtitle');
    
    if (currentSearch) {
        emptyStateTitle.textContent = 'No matches found';
        emptyStateSubtitle.textContent = `No synonyms match your search "${currentSearch}". Try adjusting your search terms or filters.`;
    } else {
        emptyStateTitle.textContent = 'No synonyms pending review';
        emptyStateSubtitle.textContent = 'All synonyms have been reviewed or there are no new synonyms from the source.';
    }
    
    emptyState.classList.remove('hidden');
}

function hideEmptyState() {
    emptyState.classList.add('hidden');
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showModal(message) {
    return new Promise((resolve) => {
        modalMessage.textContent = message;
        confirmModal.classList.remove('hidden');

        const cleanup = () => {
            modalConfirm.removeEventListener('click', onConfirm);
            modalCancel.removeEventListener('click', onCancel);
            confirmModal.removeEventListener('click', onBackdrop);
            confirmModal.classList.add('hidden');
        };

        const onConfirm = () => {
            cleanup();
            resolve(true);
        };

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        const onBackdrop = (e) => {
            if (e.target === confirmModal) onCancel();
        };

        modalConfirm.addEventListener('click', onConfirm);
        modalCancel.addEventListener('click', onCancel);
        confirmModal.addEventListener('click', onBackdrop);
    });
}

window.addEventListener('beforeunload', () => {
    saveSelectionsToStorage();
});