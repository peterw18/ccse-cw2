function isValidProduct(product) {
    return (
        typeof product.itemid === "number" &&
        typeof product.name === "string" &&
        typeof product.price === "number" &&
        typeof product.image === "string"
    );
}

function loadProductGrid(){
    fetch("/api/products")
    .then(response => response.json())
    .then(data => {
        if (!Array.isArray(data)) {
            throw new Error("Invalid data format: Expected an array");
        }

        const validProducts = data.filter(isValidProduct);

        if (validProducts.length !== data.length) {
            console.warn("Some products were invalid and skipped");
        }

        const container = document.getElementById("productContainer");
        container.innerHTML = validProducts.map(product => `
            <div class="product-card" id="${product.itemid}" onclick="openProductPage(${product.itemid})">
                <img src="../static/uploads/${product.image}" alt="${product.name}">
                <h3>${product.name}</h3>
                <h5 style="float: right;">£${(product.price/100).toFixed(2)}</h5>
            </div>
        `).join("");
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