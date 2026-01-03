document.addEventListener('click', (e) => {
    // Only react to LEFT click
    if (e.button !== 0) return;

    const menu = document.getElementById('txn-context-menu');
    if (!menu) return;

    // ❗ If the click happened INSIDE the context menu, do nothing
    if (menu.contains(e.target)) return;

    // Otherwise close the menu
    menu.classList.remove('is-visible');
    menu.style.display = 'none';
});

function openTxnContextMenu(event, rowEl) {
    event.preventDefault();
    event.stopPropagation();

    const menu = document.getElementById('txn-context-menu');
    const noteInput = menu.querySelector('.context-menu__note-input');
    const removeItem = menu.querySelector('[data-action=remove-budget]');

    menu.style.top = event.clientY + 'px';
    menu.style.left = event.clientX + 'px';

    menu.dataset.txnId = rowEl.dataset.txnId;
    menu.dataset.txnOccurredAt = rowEl.dataset.txnOccurredAt;
    menu.dataset.txnBudgeted = rowEl.dataset.txnBudgeted;
    menu.dataset.txnNote = rowEl.dataset.txnNote || '';

    noteInput.value = menu.dataset.txnNote;

    if (removeItem) {
        removeItem.style.display =
            (menu.dataset.txnBudgeted === '1' ? 'block' : 'none');
    }

    menu.style.display = 'block';
    menu.classList.add('is-visible');
}