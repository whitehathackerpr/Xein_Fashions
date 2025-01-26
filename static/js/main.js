// Product image gallery
document.querySelectorAll('.thumbnail').forEach(thumb => {
    thumb.addEventListener('click', function() {
        const mainImg = document.querySelector('.product-gallery img');
        mainImg.src = this.src.replace('-thumb', '');
    });
});

// Add to cart functionality
document.querySelectorAll('.btn-add-to-cart').forEach(button => {
    button.addEventListener('click', function() {
        // Add cart functionality here
    });
});

// Shopping Cart Functionality
class ShoppingCart {
    constructor() {
        this.items = [];
        this.total = 0;
    }

    addItem(product) {
        this.items.push(product);
        this.updateTotal();
        this.updateCartUI();
    }

    removeItem(productId) {
        this.items = this.items.filter(item => item.id !== productId);
        this.updateTotal();
        this.updateCartUI();
    }

    updateTotal() {
        this.total = this.items.reduce((sum, item) => sum + item.price, 0);
    }

    updateCartUI() {
        const cartItems = document.getElementById('cart-items');
        const cartTotal = document.getElementById('cart-total');
        
        // Update cart UI logic here
    }
}

// Wishlist Functionality
class Wishlist {
    constructor() {
        this.items = [];
    }

    toggleItem(product) {
        const index = this.items.findIndex(item => item.id === product.id);
        if (index === -1) {
            this.items.push(product);
        } else {
            this.items.splice(index, 1);
        }
        this.updateWishlistUI();
    }

    updateWishlistUI() {
        // Update wishlist UI logic here
    }
}

// Product Search
document.getElementById('search-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const searchTerm = document.getElementById('search-input').value;
    // Implement search logic here
});

// Newsletter Subscription
document.getElementById('newsletter-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const email = this.querySelector('input[type="email"]').value;
    // Implement newsletter subscription logic here
});

// Product Reviews
class ReviewSystem {
    constructor() {
        this.reviews = [];
    }

    addReview(review) {
        this.reviews.push(review);
        this.updateReviewsUI();
    }

    updateReviewsUI() {
        const reviewList = document.querySelector('.review-list');
        // Update reviews UI logic here
    }
}

// Password validation for signup
document.addEventListener('DOMContentLoaded', function() {
    const signupForm = document.querySelector('form[action="/signup"]');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            if (password !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match!');
            }
            
            if (password.length < 8) {
                e.preventDefault();
                alert('Password must be at least 8 characters long!');
            }
        });
    }
});

// Add to cart functionality
function addToCart(productId) {
    const quantity = document.querySelector(`#quantity-${productId}`).value;
    fetch('/add_to_cart/' + productId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Product added to cart!');
            updateCartCount(data.cart_count);
        } else {
            alert('Error adding product to cart');
        }
    });
}

// Update cart count in navbar
function updateCartCount(count) {
    const cartBadge = document.querySelector('.cart-badge');
    if (cartBadge) {
        cartBadge.textContent = count;
    }
} 