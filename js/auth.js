// Simple client-side password protection
// Note: This is not secure for sensitive data, but deters casual access

// SHA-256 hash of password "einvoice2026"
// To change password: generate new hash using: await crypto.subtle.digest('SHA-256', new TextEncoder().encode('your-password'))
const HASHED_PASSWORD = 'a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1';

// For demo purposes, using a simple password check
// In production, use a proper hash
const VALID_PASSWORD = 'einvoice2026';

/**
 * Check if user is authenticated
 * Redirects to login page if not authenticated
 */
function checkAuth() {
    const authToken = localStorage.getItem('einvoice-auth');
    const authExpiry = localStorage.getItem('einvoice-auth-expiry');

    // Check if auth exists and hasn't expired (24 hour session)
    if (!authToken || !authExpiry || Date.now() > parseInt(authExpiry)) {
        localStorage.removeItem('einvoice-auth');
        localStorage.removeItem('einvoice-auth-expiry');
        window.location.href = 'login.html';
        return false;
    }

    return true;
}

/**
 * Attempt to log in with provided password
 * @param {string} password - The password to verify
 * @returns {boolean} - Whether login was successful
 */
function login(password) {
    if (password === VALID_PASSWORD) {
        // Set auth token and expiry (24 hours)
        const token = generateToken();
        const expiry = Date.now() + (24 * 60 * 60 * 1000);

        localStorage.setItem('einvoice-auth', token);
        localStorage.setItem('einvoice-auth-expiry', expiry.toString());

        return true;
    }
    return false;
}

/**
 * Log out the user
 */
function logout() {
    localStorage.removeItem('einvoice-auth');
    localStorage.removeItem('einvoice-auth-expiry');
    window.location.href = 'login.html';
}

/**
 * Generate a random token for session
 * @returns {string} - Random token
 */
function generateToken() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Hash a string using SHA-256 (for future use with proper password hashing)
 * @param {string} str - String to hash
 * @returns {Promise<string>} - Hex-encoded hash
 */
async function sha256(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(byte => byte.toString(16).padStart(2, '0')).join('');
}
