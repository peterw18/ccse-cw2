document.addEventListener("DOMContentLoaded", function () {
    const cardInput = document.getElementById("card-number");
    const cardLogo = document.getElementById("card-logo");
    const expiryInput = document.getElementById("expiry");
    const cvvInput = document.getElementById("cvv");

    // Format Card Number
    cardInput.addEventListener("input", function (e) {
        let value = e.target.value.replace(/\D/g, ""); // Remove non-numeric characters
        value = value.substring(0, 16); // Limit to 16 digits
        let formattedValue = value.replace(/(\d{4})/g, "$1 ").trim(); // Add space every 4 digits
        e.target.value = formattedValue;

        // Detect card type
        if (value.startsWith("4")) {
            cardLogo.src = "../static/resources/visa.png";
            cardLogo.style.display = "block";
        } else if (value.startsWith("5") || value.startsWith("2")) {
            cardLogo.src = "../static/resources/mastercard.png";
            cardLogo.style.display = "block";
        } else {
            cardLogo.src = "";
            cardLogo.style.display = "none";
        }

    });

    cardInput.addEventListener("keydown", function (e) {
        if (e.key === "Backspace") {
            let value = e.target.value;
            if (value.endsWith(" ")) {
                e.target.value = value.slice(0, -1); // Remove last space
            }
        }
    });

    // Format Expiry Date (MM/YY) with month validation
    expiryInput.addEventListener("input", function (e) {
        let value = e.target.value.replace(/\D/g, ""); // Remove non-numeric characters

        if (value.length > 4) value = value.substring(0, 4); // Limit to 4 digits
        
        if (value.length >= 2) {
            let month = parseInt(value.substring(0, 2));
            if (month > 12) {
                month = 12; // Restrict max month to 12
            } else if (month < 1) {
                month = 1; // Restrict min month to 01
            }
            value = month.toString().padStart(2, "0") + "/" + value.substring(2);
        }
        
        e.target.value = value;
    });

    expiryInput.addEventListener("keydown", function (e) {
        if (e.key === "Backspace") {
            let value = e.target.value;
            if (value.endsWith("/")) {
                e.target.value = value.slice(0, -1); // Remove slash if backspacing
            }
        }
    });

    // Format CVV (3 or 4 digits)
    cvvInput.addEventListener("input", function (e) {
        let value = e.target.value.replace(/\D/g, ""); // Remove non-numeric characters
        e.target.value = value.substring(0, 4); // Limit to 4 digits (AMEX uses 4, others use 3)
    });
});
