const cart = loadCart();
const isLoggedIn = window.isLoggedIn === true || window.isLoggedIn === 'true';

function addToCart(button) {
    const isbn = button.getAttribute('data-isbn');
    const title = button.getAttribute('data-title');
    const price = parseFloat(button.getAttribute('data-price'));

    if (!cart[isbn]) {
        cart[isbn] = {
            title,
            price,
            quantity: 1,
            image: `/static/covers/${isbn}.jpg`
        };
    } else {
        cart[isbn].quantity += 1;
    }

    if (isLoggedIn) {
        syncAddToCart(isbn);
    }

    saveCart();
    updateCartUI();
    openCart();
}

function removeFromCart(isbn) {
    if (!cart[isbn]) return;

    cart[isbn].quantity -= 1;
    if (cart[isbn].quantity <= 0) {
        delete cart[isbn];
    }

    if (isLoggedIn) {
        syncRemoveFromCart(isbn);
    }

    saveCart();
    updateCartUI();
}

function syncAddToCart(isbn) {
    fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isbn })
    }).catch(err => console.error('Add to cart failed:', err));
}

function syncRemoveFromCart(isbn) {
    fetch('/api/cart/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isbn })
    }).catch(err => console.error('Remove from cart failed:', err));
}

function updateCartUI() {
    const cartBody = document.getElementById('cart-body');
    cartBody.innerHTML = '';

    if (Object.keys(cart).length === 0) {
        cartBody.innerHTML = `
            <div class="cart-empty">
                <i class="fa-solid fa-cart-shopping" style="font-size:3rem;margin-bottom:1rem;"></i>
                <p>There are currently no items in your shopping cart.</p>
            </div>`;
        return;
    }

    const list = document.createElement('ul');
    list.style.listStyle = 'none';
    list.style.padding = '0';

    let total = 0;
    let count = 0;

    for (const isbn in cart) {
        const item = cart[isbn];
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.alignItems = 'center';
        li.style.marginBottom = '10px';

        const img = document.createElement('img');
        img.src = item.image;
        img.alt = item.title;
        img.width = 50;
        img.height = 75;
        img.style.marginRight = '10px';

        const info = document.createElement('div');
        info.innerHTML = `<strong>${item.title}</strong> (x${item.quantity}) — $${(item.price * item.quantity).toFixed(2)}`;

        const removeBtn = document.createElement('button');
        removeBtn.textContent = 'Remove';
        removeBtn.onclick = () => removeFromCart(isbn);
        removeBtn.style.marginLeft = '10px';

        li.appendChild(img);
        li.appendChild(info);
        li.appendChild(removeBtn);
        list.appendChild(li);

        total += item.price * item.quantity;
        count += item.quantity;
    }

    cartBody.appendChild(list);

    const summary = document.createElement('div');
    summary.style.marginTop = '1rem';
    summary.innerHTML = `
        <p><strong>Total Items:</strong> ${count}</p>
        <p><strong>Total:</strong> $${total.toFixed(2)}</p>`;
    cartBody.appendChild(summary);
}

function saveCart() {
    localStorage.setItem('cart', JSON.stringify(cart));
}

function loadCart() {
    const stored = localStorage.getItem('cart');
    return stored ? JSON.parse(stored) : {};
}

function openCart() {
    document.getElementById('cart-popout').classList.add('active');
}

function closeCart() {
    document.getElementById('cart-popout').classList.remove('active');
}

function mergeServerCart(serverCart) {
    for (const isbn in serverCart) {
        const serverItem = serverCart[isbn];
        if (cart[isbn]) {
            cart[isbn].quantity = Math.max(cart[isbn].quantity, serverItem.quantity);
        } else {
            cart[isbn] = {
                ...serverItem,
                image: `/static/covers/${isbn}.jpg`  // Add image if missing
            };
        }
    }
    saveCart();
    updateCartUI();
}

function clearCartBeforeLogout() {
    localStorage.removeItem('cart');
}

document.addEventListener('DOMContentLoaded', () => {
    let justClearedCart = false;

    if (document.cookie.includes('clear_cart=1')) {
        localStorage.removeItem('cart');
        updateCartUI();
        document.cookie = 'clear_cart=; Max-Age=0'; // clear the cookie
        justClearedCart = true;
    }

    if (isLoggedIn && !justClearedCart) {
        fetch('/api/cart')
            .then(res => res.json())
            .then(serverCart => mergeServerCart(serverCart))
            .catch(err => {
                console.error('Failed to load server cart:', err);
                updateCartUI(); // fallback
            });
    } else if (!justClearedCart) {
        updateCartUI();
    }
});

