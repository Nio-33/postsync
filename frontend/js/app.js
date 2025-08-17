// PostSync Frontend Application
class PostSyncApp {
    constructor() {
        this.currentPage = 'landing';
        this.init();
    }

    init() {
        this.bindEvents();
        this.initAnimations();
        this.showPage('landing');
    }

    bindEvents() {
        // Navigation events
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick]')) {
                e.preventDefault();
            }
        });

        // Form submissions using event delegation
        document.addEventListener('submit', (e) => {
            if (e.target.id === 'login-form') {
                e.preventDefault();
                this.handleLogin(e);
            } else if (e.target.id === 'signup-form') {
                e.preventDefault();
                this.handleSignup(e);
            }
        });

        // Password strength checker
        document.getElementById('signupPassword')?.addEventListener('input', (e) => {
            this.checkPasswordStrength(e.target.value);
        });

        // Smooth scrolling for navigation links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });

        // Mobile menu toggle
        document.querySelector('.mobile-menu-toggle')?.addEventListener('click', () => {
            this.toggleMobileMenu();
        });

        // Navbar scroll effect
        window.addEventListener('scroll', () => {
            this.handleNavbarScroll();
        });

        // Window resize handling
        window.addEventListener('resize', () => {
            this.handleResize();
        });
    }

    initAnimations() {
        // Typewriter animation for hero title
        this.initTypewriter();

        // Intersection Observer for scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        // Observe elements for animation
        document.querySelectorAll('.feature-card, .stat, .content-card').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            observer.observe(el);
        });
    }

    initTypewriter() {
        const typewriterElement = document.getElementById('typewriter-text');
        if (!typewriterElement) return;

        const text = 'AI-Powered Social Media Automation';
        let index = 0;
        let isDeleting = false;
        let isCompleted = false;

        const typeSpeed = 100;
        const deleteSpeed = 50;
        const pauseTime = 2000;

        function type() {
            if (!isCompleted) {
                if (!isDeleting && index < text.length) {
                    typewriterElement.textContent = text.slice(0, index + 1);
                    index++;
                    setTimeout(type, typeSpeed);
                } else if (!isDeleting && index === text.length) {
                    // Pause before completing
                    setTimeout(() => {
                        isCompleted = true;
                        // Hide cursor after completion
                        document.querySelector('.cursor').style.display = 'none';
                    }, pauseTime);
                }
            }
        }

        // Start typing after a brief delay
        setTimeout(type, 500);
    }

    showPage(pageId) {
        // Hide all pages
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });

        // Show target page
        const targetPage = document.getElementById(`${pageId}-page`);
        if (targetPage) {
            targetPage.classList.add('active');
            this.currentPage = pageId;

            // Update document title
            const titles = {
                'landing': 'PostSync - AI-Powered Social Media Automation',
                'login': 'Sign In - PostSync',
                'signup': 'Create Account - PostSync'
            };
            document.title = titles[pageId] || 'PostSync';

            // Add page-specific classes to body
            document.body.className = `page-${pageId}`;

            // Focus management for accessibility
            if (pageId !== 'landing') {
                const firstInput = targetPage.querySelector('input');
                setTimeout(() => firstInput?.focus(), 100);
            }
        }
    }

    async handleLogin(event) {
        console.log('handleLogin called', event);
        const form = event.target;
        const formData = new FormData(form);
        const email = formData.get('email');
        const password = formData.get('password');
        const remember = formData.get('remember');

        console.log('Login attempt:', { email, password: password ? '***' : 'empty' });

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<div class="loading"></div> Signing In...';
        submitBtn.disabled = true;

        try {
            // Call real API endpoint
            const response = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccessMessage('Successfully signed in!');
                
                // Store authentication tokens
                localStorage.setItem('postsync_access_token', data.access_token);
                localStorage.setItem('postsync_refresh_token', data.refresh_token);
                localStorage.setItem('postsync_user_id', data.user_id);
                
                if (remember) {
                    localStorage.setItem('postsync_remember', 'true');
                }

                // Redirect to dashboard
                setTimeout(() => {
                    this.showSuccessMessage('Redirecting to dashboard...');
                    window.location.href = '/dashboard.html';
                }, 1000);
            } else {
                throw new Error(data.detail || 'Login failed');
            }
        } catch (error) {
            if (error.message.includes('fetch')) {
                this.showErrorMessage('Unable to connect to server. Please make sure the backend is running.');
            } else {
                this.showErrorMessage(error.message || 'Invalid email or password. Please try again.');
            }
        } finally {
            // Reset button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    }

    async handleSignup(event) {
        const form = event.target;
        const formData = new FormData(form);
        const fullName = formData.get('firstName'); // Using firstName field for full name
        const email = formData.get('email');
        const password = formData.get('password');
        const confirmPassword = formData.get('confirmPassword');
        const terms = formData.get('terms');

        // Validation
        const errors = [];
        
        if (!fullName) {
            errors.push('Please enter your full name');
        }
        
        if (!email || !this.isValidEmail(email)) {
            errors.push('Please enter a valid email address');
        }
        
        if (!password || password.length < 8) {
            errors.push('Password must be at least 8 characters long');
        }
        
        if (password !== confirmPassword) {
            errors.push('Passwords do not match');
        }
        
        if (!terms) {
            errors.push('Please accept the terms of service');
        }

        if (errors.length > 0) {
            this.showErrorMessage(errors.join('<br>'));
            return;
        }

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<div class="loading"></div> Creating Account...';
        submitBtn.disabled = true;

        try {
            // Call real API endpoint
            const response = await fetch('http://127.0.0.1:8000/api/v1/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    full_name: fullName,
                    job_title: '',
                    company: ''
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccessMessage('Account created successfully! You can now sign in.');
                
                // Auto-switch to login after success
                setTimeout(() => {
                    this.showLogin();
                    // Pre-fill email in login form
                    document.getElementById('email').value = email;
                }, 2000);
            } else {
                throw new Error(data.detail || 'Registration failed');
            }

        } catch (error) {
            if (error.message.includes('fetch')) {
                this.showErrorMessage('Unable to connect to server. Please make sure the backend is running.');
            } else {
                this.showErrorMessage(error.message || 'Failed to create account. Please try again.');
            }
        } finally {
            // Reset button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    }

    checkPasswordStrength(password) {
        const strengthBar = document.querySelector('.strength-bar');
        const strengthText = document.querySelector('.strength-text');
        
        if (!strengthBar || !strengthText) return;

        let score = 0;
        let feedback = '';

        if (password.length >= 8) score += 25;
        if (/[a-z]/.test(password)) score += 15;
        if (/[A-Z]/.test(password)) score += 15;
        if (/[0-9]/.test(password)) score += 20;
        if (/[^A-Za-z0-9]/.test(password)) score += 25;

        if (score < 30) {
            feedback = 'Weak password';
            strengthBar.style.background = '#ef4444';
        } else if (score < 60) {
            feedback = 'Fair password';
            strengthBar.style.background = '#f59e0b';
        } else if (score < 90) {
            feedback = 'Good password';
            strengthBar.style.background = '#3b82f6';
        } else {
            feedback = 'Strong password';
            strengthBar.style.background = '#10b981';
        }

        strengthBar.style.width = `${Math.min(score, 100)}%`;
        strengthText.textContent = feedback;
    }

    toggleMobileMenu() {
        const navMenu = document.querySelector('.nav-menu');
        const toggle = document.querySelector('.mobile-menu-toggle i');
        
        if (navMenu.style.display === 'flex') {
            navMenu.style.display = 'none';
            toggle.className = 'fas fa-bars';
        } else {
            navMenu.style.display = 'flex';
            navMenu.style.flexDirection = 'column';
            navMenu.style.position = 'absolute';
            navMenu.style.top = '100%';
            navMenu.style.left = '0';
            navMenu.style.right = '0';
            navMenu.style.background = 'white';
            navMenu.style.padding = '1rem';
            navMenu.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
            toggle.className = 'fas fa-times';
        }
    }

    handleNavbarScroll() {
        // Disabled: Keep navbar transparent on scroll
        // const navbar = document.querySelector('.navbar');
        // if (window.scrollY > 50) {
        //     navbar.style.background = 'rgba(255, 255, 255, 0.98)';
        //     navbar.style.backdropFilter = 'blur(20px)';
        // } else {
        //     navbar.style.background = 'rgba(255, 255, 255, 0.95)';
        //     navbar.style.backdropFilter = 'blur(10px)';
        // }
    }

    handleResize() {
        // Reset mobile menu on resize
        if (window.innerWidth > 768) {
            const navMenu = document.querySelector('.nav-menu');
            navMenu.style.display = 'flex';
            navMenu.style.flexDirection = 'row';
            navMenu.style.position = 'static';
            navMenu.style.background = 'transparent';
            navMenu.style.padding = '0';
            navMenu.style.boxShadow = 'none';
        }
    }

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        // Remove existing messages
        document.querySelectorAll('.success-message, .error-message').forEach(el => el.remove());

        // Create new message
        const messageEl = document.createElement('div');
        messageEl.className = `${type}-message`;
        messageEl.innerHTML = message;

        // Insert into current form
        const currentForm = document.querySelector('.page.active .form');
        if (currentForm) {
            currentForm.insertBefore(messageEl, currentForm.firstChild);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                messageEl.remove();
            }, 5000);
        }
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    async simulateAPICall(delay = 1000) {
        return new Promise((resolve) => {
            setTimeout(resolve, delay);
        });
    }

    // Navigation methods (called from HTML onclick attributes)
    showLogin() {
        window.location.href = 'auth.html';
    }

    showSignup() {
        window.location.href = 'auth.html';
    }

    showLanding() {
        this.showPage('landing');
    }

    showDemo() {
        // Placeholder for demo functionality
        alert('Demo feature coming soon!');
    }
}

// Global functions for HTML onclick attributes
function showLogin() {
    window.app.showLogin();
}

function showSignup() {
    window.app.showSignup();
}

function showLanding() {
    window.app.showLanding();
}

function showDemo() {
    window.app.showDemo();
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PostSyncApp();

    // Add some interactive elements
    addInteractiveElements();
});

function addInteractiveElements() {
    // Add hover effects to feature cards
    document.querySelectorAll('.feature-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-10px) scale(1.02)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Add click ripple effect to buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.4);
                border-radius: 50%;
                pointer-events: none;
                animation: ripple 0.6s ease-out;
            `;

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Add CSS for ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            0% {
                transform: scale(0);
                opacity: 1;
            }
            100% {
                transform: scale(2);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // Skip typing effect to preserve HTML structure
    // The typing effect was breaking the HTML formatting for the gradient text
    // Keeping the original HTML intact for proper styling

    // Add parallax effect to floating icons
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallax = scrolled * 0.2;
        
        document.querySelectorAll('.floating-icon').forEach((icon, index) => {
            const speed = 0.5 + (index * 0.2);
            icon.style.transform = `translateY(${parallax * speed}px) rotate(${scrolled * 0.1}deg)`;
        });
    });
}

// Add keyboard navigation support
document.addEventListener('keydown', (e) => {
    // Escape key to go back to landing page
    if (e.key === 'Escape' && window.app.currentPage !== 'landing') {
        window.app.showLanding();
    }
    
    // Enter key on logo to go to landing page
    if (e.key === 'Enter' && e.target.classList.contains('logo-text')) {
        window.app.showLanding();
    }
});

// Add focus management for accessibility
document.addEventListener('focusin', (e) => {
    if (e.target.matches('input, button, a')) {
        e.target.style.outline = '2px solid #3b82f6';
        e.target.style.outlineOffset = '2px';
    }
});

document.addEventListener('focusout', (e) => {
    if (e.target.matches('input, button, a')) {
        e.target.style.outline = 'none';
    }
});