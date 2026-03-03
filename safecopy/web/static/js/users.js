// users.js - Logic for users.html

function createUser(event) {
  event.preventDefault();

  const username = document.getElementById("newUsername").value;
  const password = document.getElementById("newPassword").value;
  const confirmPassword = document.getElementById("confirmPassword").value;

  if (password !== confirmPassword) {
    showNotification("Passwords do not match!", "warning");
    return;
  }

  if (password.length < 6) {
    showNotification("Password must be at least 6 characters long!", "warning");
    return;
  }

  fetch("/create_user", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username, password: password }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("User created successfully!", "success");
        document.getElementById("createUserForm").reset();
        loadUsers();
      } else {
        showNotification(
          "Error creating user: " + (data.error || "Unknown server error"),
          "danger",
        );
      }
    })
    .catch((error) => {
      showNotification("Network error: " + error, "danger");
    });
}

function changePassword(event) {
  event.preventDefault();

  const username = document.getElementById("changeUsername").value;
  const oldPassword = document.getElementById("oldPassword").value;
  const newPassword = document.getElementById("newPasswordChange").value;
  const confirmPassword = document.getElementById(
    "confirmPasswordChange",
  ).value;

  if (newPassword !== confirmPassword) {
    showNotification("New passwords do not match!", "warning");
    return;
  }

  if (newPassword.length < 6) {
    showNotification(
      "New password must be at least 6 characters long!",
      "warning",
    );
    return;
  }

  fetch("/change_password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: username,
      old_password: oldPassword,
      new_password: newPassword,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showNotification("Password changed successfully!", "success");
        document.getElementById("changePasswordForm").reset();
      } else {
        showNotification(
          "Error changing password: " + (data.error || "Unknown server error"),
          "danger",
        );
      }
    })
    .catch((error) => {
      showNotification("Network error: " + error, "danger");
    });
}

function loadUsers() {
  fetch("/get_users")
    .then((response) => response.json())
    .then((data) => {
      const usersList = document.getElementById("usersList");
      const resData = data.data || {};
      if (data.success && resData.users && resData.users.length > 0) {
        usersList.innerHTML = "";
        resData.users.forEach((user) => {
          const div = document.createElement("div");
          div.className = "user-item";
          div.style.padding = "12px";
          div.style.borderBottom = "1px solid #eee";
          div.style.display = "flex";
          div.style.justifyContent = "space-between";
          div.style.alignItems = "center";
          div.innerHTML = `
                    <div>
                        <strong>${user.username}</strong>
                        <span style="color: #666; margin-left: 10px;">Created: ${new Date(user.created_at).toLocaleDateString()}</span>
                        ${user.enabled ? '<span style="color: green; margin-left: 10px;">● Active</span>' : '<span style="color: red; margin-left: 10px;">● Disabled</span>'}
                    </div>
                `;
          usersList.appendChild(div);
        });
      } else {
        usersList.innerHTML =
          '<p style="color: #666;">No users found. Create the first user to enable authentication.</p>';
      }
    })
    .catch((error) => {
      document.getElementById("usersList").innerHTML =
        '<p style="color: #e74c3c;">Error loading users</p>';
    });
}

window.addEventListener("DOMContentLoaded", loadUsers);

// Export to window
window.createUser = createUser;
window.changePassword = changePassword;
window.loadUsers = loadUsers;
