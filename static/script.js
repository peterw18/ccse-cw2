function loadProductGrid() {
    fetch("/api/products")
        .then(response => response.json())
        .then(data => {
            if (!Array.isArray(data)) {
                throw new Error("Invalid data format: Expected an array");
            }

            const container = document.getElementById("productContainer");
            container.innerHTML = "";

            data.forEach(product => {
                const card = document.createElement("div");
                card.className = "product-card";
                card.id = product.itemid;

                card.addEventListener("click", () => openProductPage(product.itemid));

                const img = document.createElement("img");
                img.src = `../static/uploads/${encodeURIComponent(product.image)}`;
                img.alt = product.name;

                const title = document.createElement("h3");
                title.textContent = product.name;

                const price = document.createElement("h5");
                price.style.float = "right";
                price.textContent = `£${(product.price / 100).toFixed(2)}`;

                card.appendChild(img);
                card.appendChild(title);
                card.appendChild(price);

                container.appendChild(card);
            });
        })
        .catch(error => console.error("Error loading products:", error));
}


function openProductPage(id){
    window.location.href = "/product?id=" + id;
}

function renderBasket(basketItems, total) {
    let container = document.getElementById("basketContainer");
    container.innerHTML = "";
    
    basketItems.forEach(item => {
        const itemDiv = document.createElement("div");
        itemDiv.classList.add("basket-item");

        itemDiv.innerHTML = `
            <img src="../static/uploads/${item[2]}" alt="${item[0]}">
            <div class="item-details">
                <strong>${item[0]}</strong><br>
                Price: £${((item[1])/100).toFixed(2)}<br>
                <form action="/basket" method="post" id="quantityForm${item[3]}">
                <label>Quantity:  </label>
                <input value="${item[3]}" name="itemid" hidden>
                <input type="number" value="${item[5]}" min="0" max="${item[4]}" name="new_quantity" onchange="updateBasketQuantity(${item[3]})">
                </form>
            </div>
        `;
        
        container.appendChild(itemDiv);
    });

    if (basketItems.length == 0){
        const itemDiv = document.createElement("div");
        itemDiv.classList.add("basket-item");

        itemDiv.innerHTML = `
        <strong>Your basket is currently empty</strong>
        <a href="/">Continue Shopping</a>`;

        container.appendChild(itemDiv);
    } else {
        const itemDiv = document.createElement("div");
        itemDiv.classList.add("basket-item");

        itemDiv.innerHTML = `
        <strong>Subtotal: £${(total/100).toFixed(2)}</strong>
        <a href="/checkout" id="checkoutBtn">Checkout</a>`;

        container.appendChild(itemDiv);
    }
}

function updateBasketQuantity(id){
    document.getElementById("quantityForm"+id).submit();
}