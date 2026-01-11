document.addEventListener('pointerdown', (e) => {
    const menu = document.getElementById('txn-context-menu');
    if (!menu || !menu.classList.contains('is-visible')) return;

    // Close only if press is outside the menu
    if (!menu.contains(e.target)) {
        closeTxnContextMenu();
    }
}, true); // 👈 CAPTURE phase

function triggerBudgetRefreshIfListVisible() {
    const budgetList = document.getElementById('budget-list-items');
    if (!budgetList) return;
    htmx.trigger(document.body, 'refresh-budgets');
}

function adjustTxnContextMenuBounds(menu, anchorX, anchorY) {
    const viewport = window.visualViewport;
    const viewportWidth = viewport?.width ?? window.innerWidth;
    const viewportHeight = viewport?.height ?? window.innerHeight;
    const viewportLeft = viewport?.offsetLeft ?? 0;
    const viewportTop = viewport?.offsetTop ?? 0;
    const padding = 12;

    menu.style.maxHeight = `${Math.max(0, viewportHeight - padding * 2)}px`;
    menu.style.overflowY = 'auto';

    const rect = menu.getBoundingClientRect();
    let left = anchorX;
    let top = anchorY;

    const rightLimit = viewportLeft + viewportWidth - padding;
    const bottomLimit = viewportTop + viewportHeight - padding;
    const leftLimit = viewportLeft + padding;
    const topLimit = viewportTop + padding;

    if (rect.right > rightLimit) {
        left = Math.max(leftLimit, rightLimit - rect.width);
    }
    if (rect.bottom > bottomLimit) {
        top = Math.max(topLimit, bottomLimit - rect.height);
    }
    if (left < leftLimit) {
        left = leftLimit;
    }
    if (top < topLimit) {
        top = topLimit;
    }

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;

    const header = menu.querySelector('.context-menu__header');
    const headerHeight = header ? header.getBoundingClientRect().height : 0;
    const scrollLists = menu.querySelectorAll('.context-menu__list--scroll');
    const maxListHeight = Math.max(140, viewportHeight - headerHeight - padding * 4);
    scrollLists.forEach((list) => {
        list.style.maxHeight = `${maxListHeight}px`;
    });
}

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

    const rowRect = rowEl.getBoundingClientRect();
    const clickX = Number.isFinite(event.clientX) ? event.clientX : rowRect.left;
    const clickY = Number.isFinite(event.clientY) ? event.clientY : rowRect.top;
    menu.dataset.anchorX = String(clickX);
    menu.dataset.anchorY = String(clickY);

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
    menu.style.visibility = 'hidden';
    menu.style.top = clickY + 'px';
    menu.style.left = clickX + 'px';
    adjustTxnContextMenuBounds(menu, clickX, clickY);
    menu.style.visibility = 'visible';
    menu.classList.add('is-visible');
    htmx.trigger(document.body, 'txn-menu-open');
}

if (window.visualViewport) {
    const handleViewportChange = () => {
        const menu = document.getElementById('txn-context-menu');
        if (!menu || !menu.classList.contains('is-visible')) return;
        const anchorX = Number(menu.dataset.anchorX || 0);
        const anchorY = Number(menu.dataset.anchorY || 0);
        adjustTxnContextMenuBounds(menu, anchorX, anchorY);
    };
    window.visualViewport.addEventListener('resize', handleViewportChange);
    window.visualViewport.addEventListener('scroll', handleViewportChange);
}
