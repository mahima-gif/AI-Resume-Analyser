const API_BASE_URL = "http://127.0.0.1:8000";

const tabLogin = document.getElementById("tabLogin");
const tabRegister = document.getElementById("tabRegister");
const authTitle = document.getElementById("authTitle");
const authSubtitle = document.getElementById("authSubtitle");
const authForm = document.getElementById("authForm");
const nameGroup = document.getElementById("nameGroup");
const titleGroup = document.getElementById("titleGroup");
const loginOptions = document.getElementById("loginOptions");
const submitButton = document.getElementById("submitButton");
const loginMessage = document.getElementById("loginMessage");
const togglePrompt = document.getElementById("togglePrompt");
const toggleLink = document.getElementById("toggleLink");

let isRegisterMode = false;

// Tab switcher
tabLogin.addEventListener("click", () => setAuthMode(false));
tabRegister.addEventListener("click", () => setAuthMode(true));
toggleLink.addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode(!isRegisterMode);
});

function setAuthMode(register) {
    isRegisterMode = register;
    loginMessage.textContent = "";

    if (isRegisterMode) {
        tabRegister.classList.add("active");
        tabLogin.classList.remove("active");
        authTitle.textContent = "Create Account";
        authSubtitle.textContent = "Sign up to track and analyze your resumes.";
        nameGroup.style.display = "block";
        titleGroup.style.display = "block";
        loginOptions.style.display = "none";
        submitButton.textContent = "Create Account";
        togglePrompt.innerHTML = 'Already have an account? <a href="#" id="toggleLink2">Login</a>';
        document.getElementById("toggleLink2")?.addEventListener("click", (e) => {
            e.preventDefault();
            setAuthMode(false);
        });
    } else {
        tabLogin.classList.add("active");
        tabRegister.classList.remove("active");
        authTitle.textContent = "Welcome Back";
        authSubtitle.textContent = "Login to continue analyzing your resume.";
        nameGroup.style.display = "none";
        titleGroup.style.display = "none";
        loginOptions.style.display = "flex";
        submitButton.textContent = "Login";
        togglePrompt.innerHTML = 'Don\'t have an account? <a href="#" id="toggleLink3">Sign Up</a>';
        document.getElementById("toggleLink3")?.addEventListener("click", (e) => {
            e.preventDefault();
            setAuthMode(true);
        });
    }
}

// Handle Form Submission
authForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const name = document.getElementById("name")?.value.trim() || "";
    const title = document.getElementById("title")?.value.trim() || "Job Seeker";

    submitButton.disabled = true;
    submitButton.textContent = isRegisterMode ? "Creating..." : "Logging in...";

    try {
        if (isRegisterMode) {
            // Register API
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password, title })
            });

            const data = await response.json();

            if (response.ok) {
                loginMessage.textContent = "🎉 Registration successful! Switching to login...";
                loginMessage.style.color = "#86efac";
                setTimeout(() => {
                    setAuthMode(false);
                    document.getElementById("email").value = email;
                }, 1200);
            } else {
                loginMessage.textContent = data.detail || "Registration failed.";
                loginMessage.style.color = "#fca5a5";
            }
        } else {
            // Login API
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                loginMessage.textContent = "Login successful! Redirecting to dashboard...";
                loginMessage.style.color = "#86efac";

                // Save session in localStorage
                localStorage.setItem("isLoggedIn", "true");
                localStorage.setItem("userEmail", data.user.email);
                localStorage.setItem("userName", data.user.name);
                localStorage.setItem("userTitle", data.user.title || "Resume Analyst");

                setTimeout(() => {
                    window.location.href = "dashboard.html";
                }, 700);
            } else {
                loginMessage.textContent = data.detail || "Invalid email or password.";
                loginMessage.style.color = "#fca5a5";
            }
        }
    } catch (err) {
        console.error(err);
        loginMessage.textContent = "⚠️ Could not connect to the backend server (FastAPI). Make sure it's running.";
        loginMessage.style.color = "#fca5a5";
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = isRegisterMode ? "Create Account" : "Login";
    }
});

// Demo Credentials Auto-Fill
document.getElementById("forgotPassword")?.addEventListener("click", function (event) {
    event.preventDefault();
    document.getElementById("email").value = "admin@gmail.com";
    document.getElementById("password").value = "123456";
    loginMessage.textContent = "Filled demo credentials (admin@gmail.com / 123456).";
    loginMessage.style.color = "#fde68a";
});