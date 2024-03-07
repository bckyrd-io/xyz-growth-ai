
const userRole = getUserRole();

const userTitleElement = document.getElementById('userTitle');
const userNameElement = document.getElementById('userName');

userTitleElement.textContent =  getUserRole();
userNameElement.textContent =  getUserName();

console.log("userId",getUserId());
console.log("userName",getUserName());

// Function to retrieve the user role from sessionStorage
function getUserRole() {
    return sessionStorage.getItem('userRole');
}
function getUserId() {
    return sessionStorage.getItem('userId');
}
function getUserName() {
    return sessionStorage.getItem('userName');
}

// Function to perform access control based on the user's role
function performAccessControl() {
    if (getUserRole() === 'admin') {
        // Example: Show admin-specific content or features
        console.log(getUserRole());
    } else if (userRole === 'researcher') {
        // Example: Show user-specific content or features
        console.log(getUserRole);
        // Hide the "users.html" link for regular users
        const usersLink = document.getElementById('usersLink');
        if (usersLink) {
            usersLink.style.display = 'none';
        }
    } else {
        // Handle other cases or roles
        console.log('User role not recognized');
    }

    const logoutLink = document.getElementById('logoutLink');
    if (logoutLink) {
        logoutLink.addEventListener('click', function (event) {
            event.preventDefault(); // Prevent the default behavior of the link
            logoutUser(); // You need to implement the logoutUser function
            // Redirect to "index.html"
            window.location.href = 'index.html';
        });
    }
}



// Function to perform access control based on the user's role


// Implement the function to log the user out (destroy the session)
function logoutUser() {
    // Clear the user role from sessionStorage
    sessionStorage.removeItem('userRole');
    sessionStorage.removeItem('userId');
    sessionStorage.removeItem('userName');
}
// Call the access control function when the page loads
document.addEventListener('DOMContentLoaded', performAccessControl);

