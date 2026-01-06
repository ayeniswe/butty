document.addEventListener('pointerdown', (e) => {
    const menu = document.getElementById('txn-context-menu');
    if (!menu || !menu.classList.contains('is-visible')) return;

    // Close only if press is outside the menu
    if (!menu.contains(e.target)) {
        closeTxnContextMenu();
    }
}, true); // 👈 CAPTURE phase

function closeTxnContextMenu() {
    const menu = document.getElementById('txn-context-menu');
    if (!menu) return;

    menu.classList.remove('is-visible');
    menu.style.display = 'none';

    // Reset views
    const main = menu.querySelector('[data-view=main]');
    const budgets = menu.querySelector('[data-view=budgets]');
    const note = menu.querySelector('[data-view=note]');

    if (main) main.style.display = 'block';
    if (budgets) budgets.style.display = 'none';
    if (note) note.style.display = 'none';
}

function openTxnContextMenu(event, rowEl) {
    event.preventDefault();
    // NO stopPropagation

    const menu = document.getElementById('txn-context-menu');
    const noteInput = menu.querySelector('.context-menu__note-input');
    const removeItem = menu.querySelector('[data-action=remove-budget]');
    const assignItem = menu.querySelector('[data-action=assign-budget]');

    // Determine current period
    const now = new Date();
    const currentMonth = now.getMonth() + 1; // JS months are 0-based
    const currentYear = now.getFullYear();

    menu.dataset.txnId = rowEl.dataset.txnId;
    menu.dataset.txnOccurredAt = rowEl.dataset.txnOccurredAt;
    menu.dataset.txnBudgeted = rowEl.dataset.txnBudgeted;
    menu.dataset.txnNote = rowEl.dataset.txnNote || '';

    menu.style.top = event.clientY + 'px';
    menu.style.left = event.clientX + 'px';

    const txnDate = new Date(rowEl.dataset.txnOccurredAt);
    const txnMonth = txnDate.getMonth() + 1;
    const txnYear = txnDate.getFullYear();

    noteInput.value = menu.dataset.txnNote;

    const isCurrentPeriod =
        txnMonth === currentMonth && txnYear === currentYear;

    // Remove budget → only if budgeted AND current period
    if (removeItem) {
        if (menu.dataset.txnBudgeted === '1' && isCurrentPeriod) {
            removeItem.style.display = 'block';
        } else {
            removeItem.style.display = 'none';
        }
    }

    // Assign budget → only if NOT budgeted AND current period
    if (assignItem) {
        if (menu.dataset.txnBudgeted !== '1' && isCurrentPeriod) {
            assignItem.style.display = 'block';
        } else {
            assignItem.style.display = 'none';
        }
    }

    menu.style.display = 'block';
    menu.classList.add('is-visible');
    htmx.trigger(document.body, 'txn-menu-open');
}