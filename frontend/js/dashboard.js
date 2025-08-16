// Dashboard Application
class DashboardApp {
    constructor() {
        this.currentPage = 'dashboard';
        this.charts = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.initCharts();
        this.initCalendar();
        this.loadDashboardData();
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                this.showPage(page);
            });
        });

        // Sidebar toggle for mobile
        document.querySelector('.sidebar-toggle')?.addEventListener('click', () => {
            this.toggleSidebar();
        });

        // User dropdown
        document.querySelector('.user-menu .user-avatar')?.addEventListener('click', () => {
            this.toggleUserDropdown();
        });

        // User dropdown links
        document.querySelectorAll('.user-dropdown a[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                console.log('Navigating to page:', page);
                this.showPage(page);
                this.closeUserDropdown();
            });
        });

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleFilter(e.target);
            });
        });

        // Content actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-success, .btn-success *')) {
                this.approveContent(e);
            } else if (e.target.matches('.btn-error, .btn-error *')) {
                this.rejectContent(e);
            }
        });

        // Calendar navigation
        document.getElementById('prevMonth')?.addEventListener('click', () => {
            this.navigateCalendar(-1);
        });

        document.getElementById('nextMonth')?.addEventListener('click', () => {
            this.navigateCalendar(1);
        });

        // Time filter change
        document.querySelector('.time-filter')?.addEventListener('change', (e) => {
            this.updateCharts(e.target.value);
        });

        // Settings inputs
        document.querySelectorAll('input[type="range"]').forEach(input => {
            input.addEventListener('input', (e) => {
                this.updateRangeDisplay(e.target);
            });
        });

        // Generate Content button
        document.querySelector('.btn-primary')?.addEventListener('click', (e) => {
            if (e.target.textContent.includes('Generate Content')) {
                this.generateContent();
            }
        });

        // Notification icon click
        document.getElementById('notificationIcon')?.addEventListener('click', () => {
            toggleSimpleNotifications();
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.user-menu')) {
                this.closeUserDropdown();
            }
            
            // Close notification dropdown if clicking outside
            const notificationIcon = document.getElementById('notificationIcon');
            const simpleDropdown = document.getElementById('simpleNotificationDropdown');
            if (notificationIcon && simpleDropdown && 
                !notificationIcon.contains(e.target) && 
                !simpleDropdown.contains(e.target) &&
                simpleDropdown.classList.contains('show')) {
                closeAllDropdowns();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }

    showPage(pageId) {
        console.log('showPage called with pageId:', pageId);
        
        // Update navigation - only for sidebar nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Only set active if it's a sidebar page
        const sidebarPage = document.querySelector(`.nav-link[data-page="${pageId}"]`);
        if (sidebarPage) {
            sidebarPage.classList.add('active');
            console.log('Set sidebar page active:', pageId);
        }

        // Update content areas
        document.querySelectorAll('.content-area').forEach(area => {
            area.classList.remove('active');
        });
        
        const targetContent = document.getElementById(`${pageId}-content`);
        if (targetContent) {
            targetContent.classList.add('active');
            console.log('Activated content area:', `${pageId}-content`);
        } else {
            console.error('Target content not found:', `${pageId}-content`);
        }

        // Update page title
        const pageTitle = this.getPageTitle(pageId);
        document.querySelector('.page-title').textContent = pageTitle;
        console.log('Updated page title to:', pageTitle);

        this.currentPage = pageId;

        // Load page-specific data
        this.loadPageData(pageId);
    }

    getPageTitle(pageId) {
        const titles = {
            'dashboard': 'Dashboard',
            'content-review': 'Content Review',
            'analytics': 'Analytics',
            'schedule': 'Content Schedule',
            'settings': 'Settings',
            'profile': 'Profile',
            'billing': 'Billing'
        };
        return titles[pageId] || 'Dashboard';
    }

    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.toggle('open');
    }

    toggleUserDropdown() {
        const dropdown = document.querySelector('.user-dropdown');
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    }

    closeUserDropdown() {
        const dropdown = document.querySelector('.user-dropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }

    handleFilter(button) {
        // Update active filter
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');

        // Filter content items
        const filter = button.dataset.filter;
        const items = document.querySelectorAll('.content-item');
        
        items.forEach(item => {
            if (filter === 'all' || item.dataset.status === filter) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }

    async approveContent(e) {
        const contentItem = e.target.closest('.content-item');
        const button = e.target.closest('.btn-success');
        
        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Approving...';
        button.disabled = true;

        try {
            // Simulate API call
            await this.simulateAPICall(1000);
            
            // Update UI
            contentItem.style.opacity = '0.5';
            this.showNotification('Content approved successfully!', 'success');
            
            // Remove from list after animation
            setTimeout(() => {
                contentItem.remove();
                this.updateContentCounts();
            }, 500);

        } catch (error) {
            this.showNotification('Failed to approve content', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async rejectContent(e) {
        const contentItem = e.target.closest('.content-item');
        const button = e.target.closest('.btn-error');
        
        // Show confirmation
        const reason = prompt('Reason for rejection (optional):');
        if (reason === null) return; // User cancelled

        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rejecting...';
        button.disabled = true;

        try {
            // Simulate API call
            await this.simulateAPICall(1000);
            
            // Update UI
            contentItem.style.opacity = '0.5';
            this.showNotification('Content rejected', 'error');
            
            // Remove from list after animation
            setTimeout(() => {
                contentItem.remove();
                this.updateContentCounts();
            }, 500);

        } catch (error) {
            this.showNotification('Failed to reject content', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    updateContentCounts() {
        const pendingCount = document.querySelectorAll('.content-item[data-status="pending"]').length;
        const badge = document.querySelector('.nav-badge');
        if (badge) {
            badge.textContent = pendingCount;
            if (pendingCount === 0) {
                badge.style.display = 'none';
            }
        }

        // Update filter button counts
        const filterBtn = document.querySelector('[data-filter="pending"]');
        if (filterBtn) {
            filterBtn.textContent = `Needs Review (${pendingCount})`;
        }
    }

    initCharts() {
        console.log('Initializing charts...');
        
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded!');
            return;
        }
        
        // Performance Chart
        const performanceCtx = document.getElementById('performanceChart');
        if (performanceCtx) {
            console.log('Creating performance chart...');
            this.charts.performance = new Chart(performanceCtx, {
                type: 'line',
                data: {
                    labels: ['Jan 1', 'Jan 2', 'Jan 3', 'Jan 4', 'Jan 5', 'Jan 6', 'Jan 7'],
                    datasets: [{
                        label: 'Engagement',
                        data: [45, 52, 48, 61, 55, 67, 58],
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Quality Score',
                        data: [88, 92, 85, 94, 90, 96, 93],
                        borderColor: '#10B981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    aspectRatio: 2,
                    layout: {
                        padding: 10
                    },
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    onResize: function(chart, size) {
                        if (size.height > 320) {
                            chart.canvas.style.height = '320px';
                        }
                    }
                }
            });
        }

        // Platform Chart
        const platformCtx = document.getElementById('platformChart');
        if (platformCtx) {
            this.charts.platform = new Chart(platformCtx, {
                type: 'doughnut',
                data: {
                    labels: ['LinkedIn', 'Twitter', 'Reddit'],
                    datasets: [{
                        data: [45, 35, 20],
                        backgroundColor: ['#0077B5', '#1DA1F2', '#FF4500']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    aspectRatio: 1,
                    layout: {
                        padding: 10
                    },
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    },
                    onResize: function(chart, size) {
                        if (size.height > 320) {
                            chart.canvas.style.height = '320px';
                        }
                    }
                }
            });
        }

        // Engagement Chart (Analytics page)
        const engagementCtx = document.getElementById('engagementChart');
        if (engagementCtx) {
            this.charts.engagement = new Chart(engagementCtx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Engagement',
                        data: [120, 150, 180, 140, 200, 160, 130],
                        backgroundColor: 'rgba(59, 130, 246, 0.8)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    aspectRatio: 2,
                    layout: {
                        padding: 10
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 250
                        }
                    },
                    onResize: function(chart, size) {
                        if (size.height > 320) {
                            chart.canvas.style.height = '320px';
                        }
                    }
                }
            });
        }
    }

    updateCharts(timeRange) {
        // Update chart data based on time range
        // This would fetch new data from the API in a real application
        
        const newData = this.generateMockData(timeRange);
        
        if (this.charts.performance) {
            this.charts.performance.data.labels = newData.labels;
            this.charts.performance.data.datasets[0].data = newData.engagement;
            this.charts.performance.data.datasets[1].data = newData.quality;
            this.charts.performance.update();
        }
    }

    generateMockData(timeRange) {
        const data = {
            '7d': {
                labels: ['Jan 1', 'Jan 2', 'Jan 3', 'Jan 4', 'Jan 5', 'Jan 6', 'Jan 7'],
                engagement: [45, 52, 48, 61, 55, 67, 58],
                quality: [88, 92, 85, 94, 90, 96, 93]
            },
            '30d': {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                engagement: [180, 220, 195, 240],
                quality: [89, 91, 87, 94]
            },
            '90d': {
                labels: ['Month 1', 'Month 2', 'Month 3'],
                engagement: [650, 780, 720],
                quality: [88, 90, 92]
            }
        };
        
        return data[timeRange] || data['7d'];
    }

    initCalendar() {
        this.currentDate = new Date();
        this.generateCalendar();
    }

    generateCalendar() {
        const grid = document.getElementById('calendarGrid');
        const monthHeader = document.getElementById('currentMonth');
        
        if (!grid || !monthHeader) return;

        // Update month header
        monthHeader.textContent = this.currentDate.toLocaleDateString('en-US', {
            month: 'long',
            year: 'numeric'
        });

        // Clear previous calendar
        grid.innerHTML = '';

        // Add day headers
        const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayHeaders.forEach(day => {
            const header = document.createElement('div');
            header.className = 'calendar-header-day';
            header.textContent = day;
            header.style.cssText = `
                padding: 0.75rem;
                font-weight: 600;
                background: var(--gray-100);
                text-align: center;
                font-size: 0.875rem;
                color: var(--gray-600);
            `;
            grid.appendChild(header);
        });

        // Generate calendar days
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay());

        const today = new Date();
        
        for (let d = new Date(startDate); d <= new Date(startDate.getTime() + 41 * 24 * 60 * 60 * 1000); d.setDate(d.getDate() + 1)) {
            const dayElement = document.createElement('div');
            dayElement.className = 'calendar-day';
            
            const isToday = d.toDateString() === today.toDateString();
            const isCurrentMonth = d.getMonth() === month;
            
            if (isToday) dayElement.classList.add('today');
            if (!isCurrentMonth) dayElement.classList.add('other-month');
            
            dayElement.innerHTML = `
                <span class="day-number">${d.getDate()}</span>
                <div class="day-events">
                    ${this.getEventsForDate(d)}
                </div>
            `;
            
            grid.appendChild(dayElement);
        }
    }

    getEventsForDate(date) {
        // Mock events - in a real app, this would come from the API
        const events = [
            { date: new Date(2024, 0, 15), title: 'LinkedIn Post', type: 'linkedin' },
            { date: new Date(2024, 0, 16), title: 'Twitter Thread', type: 'twitter' },
            { date: new Date(2024, 0, 18), title: 'Reddit Discussion', type: 'reddit' }
        ];

        const dayEvents = events.filter(event => 
            event.date.toDateString() === date.toDateString()
        );

        return dayEvents.map(event => `
            <div class="event-dot ${event.type}" title="${event.title}"></div>
        `).join('');
    }

    navigateCalendar(direction) {
        this.currentDate.setMonth(this.currentDate.getMonth() + direction);
        this.generateCalendar();
    }

    updateRangeDisplay(input) {
        const value = input.value;
        const display = input.nextElementSibling;
        if (display && display.tagName === 'SPAN') {
            display.textContent = `${value}%`;
        }
    }

    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + number keys for navigation
        if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '5') {
            e.preventDefault();
            const pages = ['dashboard', 'content-review', 'analytics', 'schedule', 'settings'];
            const pageIndex = parseInt(e.key) - 1;
            if (pages[pageIndex]) {
                this.showPage(pages[pageIndex]);
            }
        }

        // Escape to close dropdowns
        if (e.key === 'Escape') {
            this.closeUserDropdown();
        }
    }

    async loadDashboardData() {
        try {
            // Check authentication first
            const token = localStorage.getItem('postsync_access_token');
            if (!token) {
                this.showNotification('Session expired. Please login again.', 'error');
                setTimeout(() => {
                    window.location.href = '/index.html';
                }, 2000);
                return;
            }
            
            // Load user data and dashboard stats
            await Promise.all([
                this.loadUserData(),
                this.loadUserStats()
            ]);
            
            // Start real-time updates
            this.startRealTimeUpdates();
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showNotification('Failed to load dashboard data.', 'error');
        }
    }

    async loadPageData(pageId) {
        switch (pageId) {
            case 'analytics':
                await this.loadAnalyticsData();
                break;
            case 'content-review':
                await this.loadContentReviewData();
                break;
            case 'schedule':
                await this.loadScheduleData();
                break;
            case 'settings':
                await this.loadSettingsData();
                break;
            case 'profile':
                await this.loadProfileData();
                break;
            case 'billing':
                await this.loadBillingData();
                break;
        }
    }

    async loadAnalyticsData() {
        // Load analytics-specific data
        console.log('Loading analytics data...');
    }

    async loadContentReviewData() {
        // Load content review data
        console.log('Loading content review data...');
    }

    async loadScheduleData() {
        // Load schedule data
        console.log('Loading schedule data...');
    }

    async loadSettingsData() {
        // Load settings data
        console.log('Loading settings data...');
    }

    async loadProfileData() {
        // Load profile data
        console.log('Loading profile data...');
    }

    async loadBillingData() {
        // Load billing data
        console.log('Loading billing data...');
    }

    async loadUserData() {
        try {
            const token = localStorage.getItem('postsync_access_token');
            const response = await fetch('http://127.0.0.1:8000/api/v1/auth/me', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const userData = await response.json();
                this.updateUserDisplay(userData);
            } else {
                throw new Error('Failed to fetch user data');
            }
        } catch (error) {
            console.error('Error loading user data:', error);
            // Fallback to stored data or default
            this.updateUserDisplay({
                full_name: 'User',
                subscription_tier: 'Free'
            });
        }
    }

    async loadUserStats() {
        try {
            const token = localStorage.getItem('postsync_access_token');
            const response = await fetch('http://127.0.0.1:8000/api/v1/users/stats', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const stats = await response.json();
                this.updateStatsDisplay(stats);
            } else {
                // Use default stats if API fails
                this.updateStatsDisplay({
                    content_generated: 0,
                    accuracy_rate: 0,
                    posts_published: 0,
                    total_engagement: 0
                });
            }
        } catch (error) {
            console.error('Error loading user stats:', error);
            // Use default stats
            this.updateStatsDisplay({
                content_generated: 0,
                accuracy_rate: 0,
                posts_published: 0,
                total_engagement: 0
            });
        }
    }

    updateUserDisplay(userData) {
        // Update sidebar user info
        const userNameElement = document.querySelector('.user-name');
        const userPlanElement = document.querySelector('.user-plan');
        
        if (userNameElement) {
            userNameElement.textContent = userData.full_name || 'User';
        }
        
        if (userPlanElement) {
            const plan = userData.subscription_tier || 'Free';
            userPlanElement.textContent = plan.charAt(0).toUpperCase() + plan.slice(1) + ' Plan';
        }
    }

    updateStatsDisplay(stats) {
        // Update dashboard stats with real data  
        // Map backend UserStats fields to frontend display
        const statElements = {
            'Content Generated': stats.total_posts || 0,
            'Accuracy Rate': `${Math.round(stats.avg_engagement_rate * 100) || 0}%`,
            'Posts Published': stats.total_posts || 0,
            'Total Engagement': this.formatNumber(stats.total_engagements || 0)
        };

        // Update each stat element
        document.querySelectorAll('.stat-card').forEach(card => {
            const label = card.querySelector('.stat-label')?.textContent;
            const numberElement = card.querySelector('.stat-number');
            
            if (label && numberElement && statElements[label] !== undefined) {
                numberElement.textContent = statElements[label];
            }
        });

        // Animate the numbers
        this.updateStats();
    }

    updateStats() {
        // Animate stat numbers
        document.querySelectorAll('.stat-number').forEach(stat => {
            this.animateNumber(stat);
        });
    }

    animateNumber(element) {
        const target = parseInt(element.textContent.replace(/[^\d]/g, ''));
        const duration = 1000;
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = this.formatNumber(Math.floor(current));
        }, 16);
    }

    formatNumber(num) {
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    startRealTimeUpdates() {
        // Update data every 30 seconds
        setInterval(() => {
            this.updateRealTimeData();
        }, 30000);
    }

    updateRealTimeData() {
        // Update notification badge
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            const currentCount = parseInt(badge.textContent);
            if (Math.random() > 0.7) { // 30% chance of new notification
                badge.textContent = currentCount + 1;
            }
        }

        // Update activity feed
        this.addRecentActivity();
    }

    addRecentActivity() {
        const activityList = document.querySelector('.activity-list');
        if (!activityList) return;

        const activities = [
            {
                icon: 'linkedin',
                title: 'LinkedIn post generated',
                description: 'New content ready for review',
                status: 'pending'
            },
            {
                icon: 'twitter',
                title: 'Twitter thread published',
                description: 'Engagement tracking started',
                status: 'success'
            }
        ];

        if (Math.random() > 0.8) { // 20% chance of new activity
            const activity = activities[Math.floor(Math.random() * activities.length)];
            const activityElement = this.createActivityElement(activity);
            activityList.insertBefore(activityElement, activityList.firstChild);

            // Limit to 5 activities
            const items = activityList.querySelectorAll('.activity-item');
            if (items.length > 5) {
                items[items.length - 1].remove();
            }
        }
    }

    createActivityElement(activity) {
        const element = document.createElement('div');
        element.className = 'activity-item';
        element.innerHTML = `
            <div class="activity-icon ${activity.icon}">
                <i class="fab fa-${activity.icon}"></i>
            </div>
            <div class="activity-content">
                <h4>${activity.title}</h4>
                <p>${activity.description}</p>
                <span class="activity-time">Just now</span>
            </div>
            <div class="activity-status ${activity.status}">
                <i class="fas fa-${activity.status === 'success' ? 'check' : 'clock'}"></i>
            </div>
        `;
        return element;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            max-width: 300px;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    async generateContent() {
        const button = document.querySelector('.btn-primary');
        const originalText = button.innerHTML;
        
        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        button.disabled = true;

        try {
            // Get auth token from localStorage
            const token = localStorage.getItem('postsync_access_token');
            if (!token) {
                this.showNotification('Please login first to generate content', 'error');
                setTimeout(() => {
                    window.location.href = '/index.html';
                }, 2000);
                return;
            }

            // Make API call to generate real Twitter content
            const response = await fetch('http://localhost:8000/api/v1/content/generate/real-twitter-post', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification('🚀 Real Twitter post generated and published successfully!', 'success');
                
                // Show the generated content details
                if (result.data && result.data.twitter_publishing && result.data.twitter_publishing.post_url) {
                    const tweetUrl = result.data.twitter_publishing.post_url;
                    const content = result.data.ai_generation.generated_content;
                    
                    setTimeout(() => {
                        this.showNotification(`Content: "${content.substring(0, 100)}..."`, 'info');
                    }, 1000);
                    
                    setTimeout(() => {
                        this.showNotification(`View post: ${tweetUrl}`, 'info');
                    }, 3000);
                }
                
            } else {
                throw new Error('Failed to generate content');
            }

        } catch (error) {
            console.error('Twitter post generation failed:', error);
            this.showNotification('Twitter post generation failed. Please check your credentials and try again.', 'error');
        } finally {
            // Restore button state
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 2000);
        }
    }

    async simulateAPICall(delay = 1000) {
        return new Promise(resolve => setTimeout(resolve, delay));
    }

    // Social Media Connection Methods
    async connectSocialAccount(platform) {
        try {
            const response = await fetch(`http://127.0.0.1:8000/api/v1/auth/${platform}/oauth`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('postsync_access_token')}`,
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const data = await response.json();
                // Redirect to OAuth URL
                window.location.href = data.oauth_url;
            } else {
                throw new Error(`Failed to initiate ${platform} OAuth`);
            }
        } catch (error) {
            console.error(`Error connecting ${platform}:`, error);
            this.showNotification(`Failed to connect ${platform}. Please try again.`, 'error');
        }
    }

    async disconnectSocialAccount(platform) {
        try {
            const response = await fetch(`http://127.0.0.1:8000/api/v1/users/social-accounts/${platform}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('postsync_access_token')}`,
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                this.updateAccountStatus(platform, false);
                this.showNotification(`${platform} account disconnected successfully`, 'success');
            } else {
                throw new Error(`Failed to disconnect ${platform}`);
            }
        } catch (error) {
            console.error(`Error disconnecting ${platform}:`, error);
            this.showNotification(`Failed to disconnect ${platform}. Please try again.`, 'error');
        }
    }

    updateAccountStatus(platform, isConnected) {
        const accountItem = document.querySelector(`[data-platform="${platform}"]`);
        if (!accountItem) return;

        const statusElement = accountItem.querySelector('.status');
        const connectBtn = accountItem.querySelector('.btn-connect');
        const disconnectBtn = accountItem.querySelector('.btn-disconnect');

        if (isConnected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'status connected';
            connectBtn.style.display = 'none';
            disconnectBtn.style.display = 'inline-block';
        } else {
            statusElement.textContent = 'Not Connected';
            statusElement.className = 'status disconnected';
            connectBtn.style.display = 'inline-block';
            disconnectBtn.style.display = 'none';
        }
    }
}

// Custom confirmation dialog
function showConfirmDialog(message, onConfirm, onCancel = null) {
    // Remove any existing dialog
    const existingDialog = document.querySelector('.confirm-dialog-overlay');
    if (existingDialog) {
        existingDialog.remove();
    }

    const overlay = document.createElement('div');
    overlay.className = 'confirm-dialog-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
        z-index: 10001;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    const dialog = document.createElement('div');
    dialog.className = 'confirm-dialog';
    dialog.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 30px;
        min-width: 400px;
        max-width: 500px;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        text-align: center;
        transform: scale(0.9) translateY(-20px);
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    `;

    dialog.innerHTML = `
        <div style="margin-bottom: 25px;">
            <i class="fas fa-sign-out-alt" style="font-size: 48px; opacity: 0.9; margin-bottom: 15px;"></i>
            <h3 style="margin: 0; font-size: 20px; font-weight: 600; letter-spacing: -0.02em;">${message}</h3>
        </div>
        <div style="display: flex; gap: 15px; justify-content: center;">
            <button class="confirm-btn cancel-btn" style="
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                min-width: 100px;
            ">Cancel</button>
            <button class="confirm-btn ok-btn" style="
                background: rgba(255, 255, 255, 0.9);
                border: none;
                color: #667eea;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                min-width: 100px;
            ">Sign Out</button>
        </div>
    `;

    // Add hover effects
    const style = document.createElement('style');
    style.textContent = `
        .cancel-btn:hover {
            background: rgba(255, 255, 255, 0.2) !important;
            transform: translateY(-1px);
        }
        .ok-btn:hover {
            background: white !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
    `;
    document.head.appendChild(style);

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
        overlay.style.opacity = '1';
        dialog.style.transform = 'scale(1) translateY(0)';
    });

    // Handle buttons
    const cancelBtn = dialog.querySelector('.cancel-btn');
    const okBtn = dialog.querySelector('.ok-btn');

    cancelBtn.onclick = () => {
        closeDialog();
        if (onCancel) onCancel();
    };

    okBtn.onclick = () => {
        closeDialog();
        onConfirm();
    };

    // Close on overlay click
    overlay.onclick = (e) => {
        if (e.target === overlay) {
            closeDialog();
            if (onCancel) onCancel();
        }
    };

    function closeDialog() {
        overlay.style.opacity = '0';
        dialog.style.transform = 'scale(0.9) translateY(-20px)';
        setTimeout(() => {
            if (overlay.parentElement) {
                overlay.remove();
            }
            style.remove();
        }, 300);
    }
}

// Global logout function
function logout() {
    showConfirmDialog(
        'Are you sure you want to sign out?',
        () => {
            localStorage.removeItem('postsync_auth');
            window.location.href = 'index.html';
        }
    );
}

// Simple Notification Functions
function toggleSimpleNotifications() {
    const dropdown = document.getElementById('simpleNotificationDropdown');
    const isVisible = dropdown.classList.contains('show');
    
    if (isVisible) {
        dropdown.classList.remove('show');
        document.removeEventListener('click', closeSimpleNotificationsOnClickOutside);
    } else {
        // Close any other open dropdowns
        closeAllDropdowns();
        
        dropdown.classList.add('show');
        
        // Add click outside listener after a small delay
        setTimeout(() => {
            document.addEventListener('click', closeSimpleNotificationsOnClickOutside);
        }, 10);
    }
}

function closeSimpleNotificationsOnClickOutside(event) {
    const dropdown = document.getElementById('simpleNotificationDropdown');
    const notificationIcon = document.getElementById('notificationIcon');
    
    if (!dropdown.contains(event.target) && !notificationIcon.contains(event.target)) {
        dropdown.classList.remove('show');
        document.removeEventListener('click', closeSimpleNotificationsOnClickOutside);
    }
}

function closeAllDropdowns() {
    // Close user dropdown
    const userDropdown = document.querySelector('.user-dropdown');
    if (userDropdown && userDropdown.style.display === 'block') {
        userDropdown.style.display = 'none';
    }
    
    // Close simple notification dropdown
    const simpleNotificationDropdown = document.getElementById('simpleNotificationDropdown');
    if (simpleNotificationDropdown && simpleNotificationDropdown.classList.contains('show')) {
        simpleNotificationDropdown.classList.remove('show');
        document.removeEventListener('click', closeSimpleNotificationsOnClickOutside);
    }
}

// Profile Functions
function changeProfilePicture() {
    // Create file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('profilePicture').src = e.target.result;
            };
            reader.readAsDataURL(file);
            window.dashboardApp.showNotification('Profile picture updated successfully!', 'success');
        }
    };
    input.click();
}

function removeProfilePicture() {
    document.getElementById('profilePicture').src = 'https://via.placeholder.com/80';
    window.dashboardApp.showNotification('Profile picture removed', 'info');
}

// Global functions for social media account management
function connectAccount(platform) {
    if (window.dashboardApp) {
        window.dashboardApp.connectSocialAccount(platform);
    }
}

function disconnectAccount(platform) {
    if (window.dashboardApp) {
        // Show confirmation dialog
        showConfirmDialog(
            `Are you sure you want to disconnect your ${platform} account?`,
            () => {
                window.dashboardApp.disconnectSocialAccount(platform);
            }
        );
    }
}

// Add notification animations CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .calendar-header-day {
        padding: 0.75rem;
        font-weight: 600;
        background: var(--gray-100);
        text-align: center;
        font-size: 0.875rem;
        color: var(--gray-600);
    }

    .day-number {
        font-weight: 500;
        margin-bottom: 0.25rem;
    }

    .day-events {
        display: flex;
        gap: 2px;
        flex-wrap: wrap;
    }

    .event-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin: 1px;
    }

    .event-dot.linkedin { background: #0077B5; }
    .event-dot.twitter { background: #1DA1F2; }
    .event-dot.reddit { background: #FF4500; }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardApp = new DashboardApp();
    
    // Add some enhanced interactions
    addDashboardInteractions();
});

function addDashboardInteractions() {
    // Add hover effects to stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px) scale(1.02)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Add loading states to buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (!this.disabled && !this.classList.contains('btn-success') && !this.classList.contains('btn-error')) {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                this.disabled = true;

                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }, 1000);
            }
        });
    });

    // Add progress animations
    document.querySelectorAll('.stat-change.positive').forEach(change => {
        change.style.opacity = '0';
        change.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            change.style.transition = 'all 0.5s ease';
            change.style.opacity = '1';
            change.style.transform = 'translateY(0)';
        }, 500);
    });
}