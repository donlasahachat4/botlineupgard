{
  /* <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script> */
}

const hamburger = document.getElementById("hamburger");
const hamburgerMobile = document.getElementById("hamburger-mobile");
const logoWeb = document.getElementById("logo-web");
const sidebar = document.getElementById("sidebar");
const profile = document.getElementById("profile-pic");
const dropdownMenu = document.getElementById("profile-dropdown");
const changePasswordBtn = document.getElementById("change-password-btn");
const modal = document.getElementById("password-modal");
const cancelBtn = document.getElementById("cancel-btn");
const closeBtn = document.getElementById("close-btn");
const logoutBtn = document.getElementById("logout-btn");

const body = document.body; // ใช้เพื่อเพิ่ม/ลบ class
const accordionHeaders = document.querySelectorAll(".accordion-header-content");
const accordionMobileHeaders = document.querySelectorAll(
  ".accordion-header-mobile-content"
);
// Select all dropdown items
const dropdowns = document.querySelectorAll(".dropdown");
const welcome = document.getElementById("welcome");
const currentPath = window.location.pathname;
const sidebarItems = document.querySelectorAll(".sidebar ul li");
let currentPage = 1;
const totalPages = 10;

sidebarActive = false;

hamburger.addEventListener("click", () => {
  body.classList.toggle("sidebar-expanded"); // Toggle class เพื่อเปิด/ปิด Sidebar

  logoWeb.classList.add("fade-out");
  if (logoWeb.textContent === "W") {
    welcome.style.display = "block";
  } else {
    welcome.style.display = "none";
  }

  // Wait for fade-out animation to complete
  setTimeout(() => {
    // Toggle the text content
    if (logoWeb.textContent === "W") {
      logoWeb.textContent = "WITHEEIT"; // Change to "CAT"
      sidebarActive = true;
    } else {
      logoWeb.textContent = "W"; // Change back to "C"
      sidebarActive = false;
    }

    // Remove fade-out and add fade-in animation
    logoWeb.classList.remove("fade-out");
    logoWeb.classList.add("fade-in");

    // Remove fade-in class after animation completes
    setTimeout(() => {
      logoWeb.classList.remove("fade-in");
    }, 150); // Match the duration of fade-in animation
  }, 150); // Match the duration of fade-out animation

  document.querySelectorAll(".accordion-item").forEach((item) => {
    item.classList.remove("active");

    item.querySelector(".accordion-content").style.maxHeight = null;
  });
});

hamburgerMobile.addEventListener("click", () => {
  body.classList.toggle("sidebar-mobile-expanded"); // Toggle class เพื่อเปิด/ปิด Sidebar
  document.querySelectorAll(".accordion-mobile-item").forEach((item) => {
    item.classList.remove("active");

    item.querySelector(".accordion-content-mobile").style.maxHeight = null;
  });
});

// Add event listeners for mouseenter and mouseleave
dropdowns.forEach((dropdown) => {
  dropdown.addEventListener("mouseenter", () => {
    if (!sidebarActive) {
      dropdown.classList.add("show"); // Add 'show' class on hover
    }
  });

  dropdown.addEventListener("mouseleave", () => {
    dropdown.classList.remove("show"); // Remove 'show' class when hover ends
  });
});

// Select all accordion headers

accordionHeaders.forEach((header, i) => {
  header.addEventListener("click", (v) => {
    // const accordionItem = header.parentElement;
    const accordionItemElement =
      document.querySelectorAll(".accordion-item")[i];
    const accordionContent =
      accordionItemElement.querySelector(".accordion-content");

    // Check if the item is already active
    const isActive = accordionItemElement.classList.contains("active");

    // Close all items
    document.querySelectorAll(".accordion-item").forEach((item) => {
      item.classList.remove("active");

      item.querySelector(".accordion-content").style.maxHeight = null;
    });

    // Toggle current item
    if (!isActive) {
      if (sidebarActive) {
        accordionItemElement.classList.add("active");
        accordionItemElement.style.display = "block";
        accordionContent.style.maxHeight = accordionContent.scrollHeight + "px"; // Set max-height dynamically
      }
    }
  });
});

accordionMobileHeaders.forEach((header, i) => {
  header.addEventListener("click", (v) => {
    // const accordionItem = header.parentElement;
    const accordionItemElement = document.querySelectorAll(
      ".accordion-mobile-item"
    )[i];
    const accordionContent = accordionItemElement.querySelector(
      ".accordion-content-mobile"
    );
    // Check if the item is already active
    const isActive = accordionItemElement.classList.contains("active");

    // Close all items
    document.querySelectorAll(".accordion-mobile-item").forEach((item) => {
      item.classList.remove("active");
      // accordionContent.style.opacity = 0;
      // accordionContent.style.maxHeight = 0;
      item.querySelector(".accordion-content-mobile").style.maxHeight = null;
    });

    // Toggle current item
    if (!isActive) {
      accordionItemElement.classList.add("active");
      // accordionContent.style.opacity = 1;
      accordionItemElement.style.display = "block";
      accordionContent.style.maxHeight = accordionContent.scrollHeight + "px"; // Set max-height dynamically
    }
  });
});

function changeIconColor() {
  const profileIcon = document.querySelector(".profile-icon");
  const colors = [
    "#4CAF50",
    "#FF5722",
    "#2196F3",
    "#9C27B0",
    "#FFC107",
    "#FF9800",
    "#00BCD4",
    "#795548",
    "#607D8B",
    "#E91E63",
    "#3F51B5",
    "#009688",
  ];
  const currentColor = profileIcon.style.backgroundColor;
  let newColor = colors[Math.floor(Math.random() * colors.length)];

  // Ensure new color is different from the current one
  while (newColor === currentColor) {
    newColor = colors[Math.floor(Math.random() * colors.length)];
  }

  profileIcon.style.backgroundColor = newColor;
}

// เพิ่มคลาสให้กับเมนูที่ตรงกับ path
sidebarItems.forEach((item) => {
  const link = item.querySelector("a");
  if (link && currentPath.includes(link.getAttribute("href"))) {
    item.classList.add("hover-sidebar"); // เพิ่มคลาส active หาก URL ตรง
  }
});

// let domain = "https://cus2.witheeit.xyz";
const getUser = async (domain) => {
  try {
    // เรียก API พร้อมใส่ Bearer Token ใน header
    const response = await axios.get(`${domain}/get_admin_data`);

    // ตรวจสอบสถานะจาก response
    if (response.data.status === 200) {
      // ./img/profile.webp
      // console.log(response.data.data);
      const { username, profile_pic } = response.data.data;

      const profile = document.getElementsByClassName("profile-pic");
      const usernameAdminProfile =
        document.getElementsByClassName("username-admin");
      const usernameSidebarAdminProfile = document.getElementById(
        "username-sidebar-admin"
      );

      profile[0].src = profile_pic || "./img/profile.webp";
      profile[1].src = profile_pic || "./img/profile.webp";
      profile[2].src = profile_pic || "./img/profile.webp";
      usernameAdminProfile[0].textContent = username;
      usernameSidebarAdminProfile.textContent = username;

      localStorage.setItem("username", username);
      localStorage.setItem("profilePic", profile_pic || "./img/profile.webp");
      // const profilePic = document.querySelectorAll("profile-pic");
      // const usernameAdmin = document.querySelectorAll("username-admin");
      // const usernameSidebarAdmin = document.querySelectorAll("username-sidebar-admin");
      // console.log(profilePic);
      // profilePic.forEach((pic) => {
      //     pic.src = profile_pic|| './img/profile.webp';
      // });
      // usernameAdmin.forEach((name) => {
      //     name.textContent = username;
      // });
      // usernameSidebarAdmin.forEach((name) => {
      //     name.textContent = username;
      // });
    }
  } catch (error) {
    alert("ไม่พบข้อมูลแอดมิน");
  }
};

profile.addEventListener("click", () => {
  // Toggle class show สำหรับแสดง dropdown
  dropdownMenu.classList.toggle("show");
});

// ปิด dropdown เมื่อคลิกข้างนอก
document.addEventListener("click", (event) => {
  if (!profile.contains(event.target)) {
    dropdownMenu.classList.remove("show");
  }
});

// เปิด Modal
changePasswordBtn.addEventListener("click", (e) => {
  e.preventDefault(); // ป้องกันลิงก์ default
  modal.classList.remove("fade-out");
  modal.classList.add("show");
});

// ปิด Modal ด้วยปุ่ม X
closeBtn.addEventListener("click", () => {
  modal.classList.add("fade-out"); // เพิ่ม animation fade-out

  // รอให้ animation fade-out เสร็จก่อนซ่อน modal
  setTimeout(() => {
    modal.classList.remove("show");
    modal.classList.remove("fade-out");
  }, 300); // 300ms ตรงกับ transition ใน CSS
});

// ปิด Modal ด้วยปุ่ม cencel
cancelBtn.addEventListener("click", () => {
  modal.classList.add("fade-out"); // เพิ่ม animation fade-out

  // รอให้ animation fade-out เสร็จก่อนซ่อน modal
  setTimeout(() => {
    modal.classList.remove("show");
    modal.classList.remove("fade-out");
  }, 300); // 300ms ตรงกับ transition ใน CSS
});

// ปิดการปิด modal เมื่อคลิกนอก modal
modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    event.stopPropagation();
  }
});

// ส่งฟอร์ม (ทดสอบ)
const passwordForm = document.getElementById("password-form");
passwordForm.addEventListener("submit", (event) => {
  event.preventDefault();
  console.log();
  changePassword(domain, event.srcElement[0].value, event.srcElement[1].value);
});

const changePassword = async (domain, oldPassword, newPassword) => {
  const username = localStorage.getItem("username");
  payload = {
    username: username,
    old_password: oldPassword,
    new_password: newPassword,
  };

  try {
    // เรียก API พร้อมใส่ Bearer Token ใน header
    const response = await axios.post(`${domain}/change_password`, payload);

    // ตรวจสอบสถานะจาก response
    if (response.data.status === 200) {
      alert("แก้ไขรหัสผ่านสำเร็จ");
      modal.classList.remove("show");
    }
  } catch (error) {
    alert("แก้ไขรหัสผ่านไม่สำเร็จ");
  }
};

logoutBtn.addEventListener("click", () => {
  logout();
});

function logout() {
  // ลบข้อมูลทั้งหมดใน localStorage
  localStorage.clear();

  // หรือถ้าต้องการลบเฉพาะบาง key:
  // localStorage.removeItem('keyName');

  // Redirect ไปยังหน้า login
  window.location.href = "/login.html"; // ปรับ URL ตามที่ต้องการ
}
