document.getElementById("loginForm").addEventListener("submit", function(event) {
    event.preventDefault(); // Prevent form submission

    let email = document.getElementById("email").value;
    let password = document.getElementById("password").value;
    let emailError = document.getElementById("emailError");
    let passwordError = document.getElementById("passwordError");

    // Clear previous errors
    emailError.style.display = "none";
    passwordError.style.display = "none";

    // Email validation
    let emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailPattern.test(email)) {
        emailError.textContent = "Invalid email format!";
        emailError.style.display = "block";
        return;
    }

    // Password validation
    if (password.length < 8) {
        passwordError.textContent = "Password must be at least 8 characters!";
        passwordError.style.display = "block";
        return;
    }

    alert("Login successful!");
});
