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