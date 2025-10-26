// Main JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Flash message close functionality
    const closeButtons = document.querySelectorAll('.close-flash');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });

    // Auto-hide flash messages after 5 seconds
    setTimeout(() => {
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(message => {
            message.style.display = 'none';
        });
    }, 5000);

    // Mobile menu toggle
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const navMenu = document.querySelector('nav ul');
    
    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Video player functionality
function initVideoPlayer() {
    const video = document.getElementById('promo-video');
    const videoOverlay = document.getElementById('video-overlay');
    const playButton = document.getElementById('play-button');
    
    if (video && playButton) {
        playButton.addEventListener('click', function() {
            video.play();
            videoOverlay.classList.add('hidden');
        });
        
        video.addEventListener('click', function() {
            if (video.paused) {
                video.play();
                videoOverlay.classList.add('hidden');
            } else {
                video.pause();
                videoOverlay.classList.remove('hidden');
            }
        });
    }
}

// User tabs functionality
function initUserTabs() {
    const tabs = document.querySelectorAll('.user-tab');
    const studentContent = document.getElementById('student-content');
    
    if (tabs.length > 0) {
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Remove active class from all tabs
                tabs.forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                this.classList.add('active');
                
                // Update content based on selected tab
                const tabType = this.getAttribute('data-tab');
                updateUserContent(tabType);
            });
        });
    }
}

function updateUserContent(tabType) {
    const userContent = document.querySelector('.user-content');
    
    // This would be expanded with actual content for each user type
    const content = {
        student: document.getElementById('student-content') || createStudentContent(),
        mentor: createMentorContent(),
        admin: createAdminContent()
    };
    
    // Remove existing content
    while (userContent.firstChild) {
        userContent.removeChild(userContent.firstChild);
    }
    
    // Add appropriate content
    userContent.appendChild(content[tabType]);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initVideoPlayer();
    initUserTabs();
});