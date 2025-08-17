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

        // Generate Content button - be more specific
        document.addEventListener('click', (e) => {
            // Check if clicked element or its parent contains "Generate Content" 
            const target = e.target.closest('button');
            if (target && target.textContent.includes('Generate Content')) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                this.generateContent();
                return false;
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
        
        // Prevent automatic navigation to content-review (causes Generate Content issues)
        if (pageId === 'content-review' && this.isGeneratingContent) {
            console.log('⚠️ Blocked content-review navigation during content generation');
            return;
        }
        
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
            // Destroy existing chart if it exists
            if (this.charts && this.charts.platform) {
                this.charts.platform.destroy();
            }
            this.charts = this.charts || {};
            this.charts.platform = new Chart(platformCtx, {
                type: 'doughnut',
                data: {
                    labels: ['LinkedIn', 'X (Twitter)'],
                    datasets: [{
                        data: [60, 40],
                        backgroundColor: ['#0077B5', '#000000']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    aspectRatio: 1,
                    layout: {
                        padding: {
                            top: 10,
                            left: 10,
                            right: 10,
                            bottom: 40
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                font: {
                                    size: 14
                                }
                            }
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
            
            // Make day clickable for scheduling
            const dateStr = d.toISOString().split('T')[0]; // YYYY-MM-DD format
            dayElement.setAttribute('data-date', dateStr);
            dayElement.style.cursor = 'pointer';
            
            dayElement.innerHTML = `
                <span class="day-number">${d.getDate()}</span>
                <div class="day-events">
                    ${this.getEventsForDate(d)}
                </div>
            `;
            
            // Add click handler for scheduling
            dayElement.addEventListener('click', () => {
                if (isCurrentMonth) { // Only allow scheduling for current month
                    this.openSchedulingModal(dateStr);
                }
            });
            
            grid.appendChild(dayElement);
        }
    }

    getEventsForDate(date) {
        // Mock events - in a real app, this would come from the API
        const events = [
            { date: new Date(2024, 0, 15), title: 'LinkedIn Post', type: 'linkedin' },
            { date: new Date(2024, 0, 16), title: 'X Thread', type: 'twitter' },
            { date: new Date(2024, 0, 18), title: 'AI Innovation Forum', type: 'linkedin' }
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

    openSchedulingModal(date) {
        // Create modal HTML
        const modalHTML = `
            <div class="modal-overlay" id="schedulingModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Schedule Content for ${new Date(date).toLocaleDateString('en-US', { 
                            weekday: 'long', 
                            year: 'numeric', 
                            month: 'long', 
                            day: 'numeric' 
                        })}</h3>
                        <button class="modal-close" onclick="closeSchedulingModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="scheduleForm">
                            <div class="form-group">
                                <label for="contentSelect">Select Content to Schedule:</label>
                                <select id="contentSelect" required>
                                    <option value="">Choose content...</option>
                                    <option value="1">AI Research Breakthrough in Machine Learning</option>
                                    <option value="2">Startup Funding Trends 2024</option>
                                    <option value="3">Future of Remote Work</option>
                                </select>
                            </div>
                            
                            <div class="form-group">
                                <label for="scheduleTime">Time:</label>
                                <input type="time" id="scheduleTime" value="09:00" required>
                            </div>
                            
                            <div class="form-group">
                                <label>Platforms:</label>
                                <div class="platform-checkboxes">
                                    <label class="checkbox-label">
                                        <input type="checkbox" name="platforms" value="linkedin" checked>
                                        <i class="fab fa-linkedin"></i> LinkedIn
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" name="platforms" value="twitter" checked>
                                        <i class="fas fa-times" style="font-weight: bold;"></i> X (Twitter)
                                    </label>
                                </div>
                            </div>
                            
                            <div class="modal-actions">
                                <button type="button" class="btn-secondary" onclick="closeSchedulingModal()">Cancel</button>
                                <button type="submit" class="btn-primary">Schedule Post</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add form submit handler
        document.getElementById('scheduleForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.scheduleContent(date, new FormData(e.target));
        });
    }

    async scheduleContent(date, formData) {
        try {
            const contentId = formData.get('contentSelect');
            const time = formData.get('scheduleTime');
            const platforms = formData.getAll('platforms');
            
            if (!contentId || platforms.length === 0) {
                this.showNotification('Please select content and at least one platform', 'error');
                return;
            }
            
            // Combine date and time
            const scheduledDateTime = `${date}T${time}:00`;
            
            // Call API to schedule content
            const response = await fetch(`http://127.0.0.1:8000/api/v1/content/${contentId}/schedule`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('postsync_access_token')}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    scheduled_time: scheduledDateTime,
                    platforms: platforms
                })
            });

            if (response.ok) {
                this.showNotification('Content scheduled successfully!', 'success');
                closeSchedulingModal();
                // Refresh calendar to show new scheduled content
                this.generateCalendar();
            } else {
                throw new Error('Failed to schedule content');
            }
        } catch (error) {
            console.error('Error scheduling content:', error);
            this.showNotification('Failed to schedule content. Please try again.', 'error');
        }
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
                console.log('No auth token found, redirecting to login');
                this.showNotification('Session expired. Please login again.', 'error');
                setTimeout(() => {
                    window.location.href = '/frontend/index.html';
                }, 2000);
                return;
            }
            
            console.log('Auth token found:', token.substring(0, 20) + '...');
            
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
        
        try {
            await Promise.all([
                this.loadAnalyticsSummary(),
                this.loadAnalyticsCharts(),
                this.loadTopContent(),
                this.loadPublishingHeatmap()
            ]);
        } catch (error) {
            console.error('Error loading analytics data:', error);
            this.showNotification('Failed to load analytics data.', 'error');
        }
    }
    
    async loadAnalyticsSummary() {
        try {
            const token = localStorage.getItem('postsync_access_token');
            const timeRange = document.getElementById('analyticsTimeRange')?.value || '30d';
            
            // In a real implementation, this would fetch from analytics API
            // For now, we'll use demo data
            const summaryData = this.getDemoAnalyticsSummary(timeRange);
            
            this.updateAnalyticsSummary(summaryData);
            
        } catch (error) {
            console.error('Error loading analytics summary:', error);
            // Use demo data as fallback
            this.updateAnalyticsSummary(this.getDemoAnalyticsSummary('30d'));
        }
    }
    
    getDemoAnalyticsSummary(timeRange) {
        const multiplier = timeRange === '7d' ? 0.3 : timeRange === '90d' ? 2.5 : timeRange === '1y' ? 12 : 1;
        
        return {
            totalImpressions: Math.floor(45000 * multiplier),
            totalEngagements: Math.floor(3200 * multiplier),
            engagementRate: 7.1,
            topPostEngagement: Math.floor(890 * multiplier),
            changes: {
                impressions: 12.5,
                engagements: 8.3,
                engagementRate: 0.7,
                topPost: 23.1
            }
        };
    }
    
    updateAnalyticsSummary(data) {
        // Update summary cards
        const updates = [
            { id: 'totalImpressions', value: this.formatNumber(data.totalImpressions), change: data.changes.impressions },
            { id: 'totalEngagements', value: this.formatNumber(data.totalEngagements), change: data.changes.engagements },
            { id: 'engagementRate', value: `${data.engagementRate}%`, change: data.changes.engagementRate },
            { id: 'topPostEngagement', value: this.formatNumber(data.topPostEngagement), change: data.changes.topPost }
        ];
        
        updates.forEach(({ id, value, change }) => {
            const element = document.getElementById(id);
            const changeElement = document.getElementById(id.replace(/([A-Z])/g, '_$1').toLowerCase() + '_change');
            
            if (element) {
                element.textContent = value;
            }
            
            if (changeElement) {
                const sign = change >= 0 ? '+' : '';
                changeElement.textContent = `${sign}${change}%`;
                changeElement.className = `summary-change ${change >= 0 ? 'positive' : 'negative'}`;
            }
        });
    }
    
    async loadAnalyticsCharts() {
        try {
            // Load chart data and create charts
            const timeRange = document.getElementById('analyticsTimeRange')?.value || '30d';
            const platform = document.getElementById('analyticsPlatform')?.value || '';
            
            this.createEngagementTrendsChart(timeRange, platform);
            this.createPlatformPerformanceChart(timeRange);
            this.createContentTypeChart(timeRange, platform);
            this.createAudienceGrowthChart(timeRange, platform);
            
        } catch (error) {
            console.error('Error loading analytics charts:', error);
        }
    }
    
    createEngagementTrendsChart(timeRange, platform) {
        const ctx = document.getElementById('engagementTrendsChart');
        if (!ctx) return;
        
        // Destroy existing chart if it exists
        if (this.charts?.engagementTrends) {
            this.charts.engagementTrends.destroy();
        }
        
        const labels = this.getTimeLabels(timeRange);
        const impressionsData = this.generateDemoData(labels.length, 1500, 500);
        const engagementsData = this.generateDemoData(labels.length, 120, 40);
        
        this.charts = this.charts || {};
        this.charts.engagementTrends = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Impressions',
                        data: impressionsData,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Engagements',
                        data: engagementsData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value >= 1000 ? (value / 1000) + 'K' : value;
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            callback: function(value) {
                                return value >= 1000 ? (value / 1000) + 'K' : value;
                            }
                        }
                    }
                }
            }
        });
    }
    
    createPlatformPerformanceChart(timeRange) {
        const ctx = document.getElementById('platformPerformanceChart');
        if (!ctx) return;
        
        if (this.charts?.platformPerformance) {
            this.charts.platformPerformance.destroy();
        }
        
        this.charts = this.charts || {};
        this.charts.platformPerformance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['LinkedIn', 'X (Twitter)'],
                datasets: [{
                    data: [60, 40],
                    backgroundColor: ['#0077B5', '#000000'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    createContentTypeChart(timeRange, platform) {
        const ctx = document.getElementById('contentTypeChart');
        if (!ctx) return;
        
        if (this.charts?.contentType) {
            this.charts.contentType.destroy();
        }
        
        this.charts = this.charts || {};
        this.charts.contentType = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['AI & Tech', 'Business', 'Startup', 'Industry'],
                datasets: [{
                    label: 'Posts',
                    data: [25, 18, 15, 12],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(249, 115, 22, 0.8)',
                        'rgba(139, 92, 246, 0.8)'
                    ],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    createAudienceGrowthChart(timeRange, platform) {
        const ctx = document.getElementById('audienceGrowthChart');
        if (!ctx) return;
        
        if (this.charts?.audienceGrowth) {
            this.charts.audienceGrowth.destroy();
        }
        
        const labels = this.getTimeLabels(timeRange);
        const growthData = this.generateGrowthData(labels.length, 1200, 50);
        
        this.charts = this.charts || {};
        this.charts.audienceGrowth = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Followers',
                    data: growthData,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value >= 1000 ? (value / 1000) + 'K' : value;
                            }
                        }
                    }
                }
            }
        });
    }
    
    async loadTopContent() {
        const container = document.getElementById('topContentList');
        const loading = document.getElementById('topContentLoading');
        
        if (!container) return;
        
        loading.style.display = 'flex';
        
        try {
            // In a real implementation, this would fetch from analytics API
            const topContent = this.getDemoTopContent();
            this.renderTopContent(topContent);
            
        } catch (error) {
            console.error('Error loading top content:', error);
            this.renderTopContent(this.getDemoTopContent());
        } finally {
            loading.style.display = 'none';
        }
    }
    
    getDemoTopContent() {
        return [
            {
                id: '1',
                title: 'AI Research Breakthrough in Machine Learning',
                platform: 'LinkedIn',
                engagements: 1247,
                impressions: 12450
            },
            {
                id: '2',
                title: 'Startup Funding Trends 2024',
                platform: 'X (Twitter)',
                engagements: 892,
                impressions: 8920
            },
            {
                id: '3',
                title: 'Tech Innovation Discussion',
                platform: 'LinkedIn',
                engagements: 654,
                impressions: 6540
            },
            {
                id: '4',
                title: 'Industry Analysis Report',
                platform: 'LinkedIn',
                engagements: 543,
                impressions: 5430
            },
            {
                id: '5',
                title: 'Market Trends Update',
                platform: 'X (Twitter)',
                engagements: 432,
                impressions: 4320
            }
        ];
    }
    
    renderTopContent(topContent) {
        const container = document.getElementById('topContentList');
        if (!container) return;
        
        // Clear loading state
        const loading = document.getElementById('topContentLoading');
        if (loading) loading.remove();
        
        topContent.forEach((item, index) => {
            const element = document.createElement('div');
            element.className = 'top-content-item';
            
            element.innerHTML = `
                <div class="content-rank">${index + 1}</div>
                <div class="content-details">
                    <h4 class="content-title">${item.title}</h4>
                    <span class="content-platform">${item.platform}</span>
                </div>
                <div class="content-metrics">
                    <div class="metric-value">${this.formatNumber(item.engagements)}</div>
                    <div class="metric-label">Engagements</div>
                </div>
            `;
            
            container.appendChild(element);
        });
    }
    
    async loadPublishingHeatmap() {
        const container = document.getElementById('publishingHeatmap');
        if (!container) return;
        
        try {
            // Generate demo heatmap data
            const heatmapData = this.getDemoHeatmapData();
            this.renderPublishingHeatmap(heatmapData);
            
        } catch (error) {
            console.error('Error loading publishing heatmap:', error);
        }
    }
    
    getDemoHeatmapData() {
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const hours = Array.from({ length: 24 }, (_, i) => i);
        
        return days.map(day => 
            hours.map(hour => ({
                day,
                hour,
                posts: Math.floor(Math.random() * 8) + 1,
                engagements: Math.floor(Math.random() * 200) + 50
            }))
        ).flat();
    }
    
    renderPublishingHeatmap(data) {
        const container = document.getElementById('publishingHeatmap');
        if (!container) return;
        
        container.innerHTML = '<div class="heatmap-grid"></div>';
        const grid = container.querySelector('.heatmap-grid');
        
        // Create day headers
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach(day => {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'heatmap-day-header';
            dayHeader.textContent = day;
            grid.appendChild(dayHeader);
        });
        
        // For simplicity, show a weekly overview instead of full 24-hour heatmap
        const weeklyData = this.getWeeklyHeatmapData();
        weeklyData.forEach(item => {
            const cell = document.createElement('div');
            cell.className = `heatmap-cell ${this.getHeatmapIntensity(item.posts)}`;
            cell.textContent = item.posts;
            cell.setAttribute('data-tooltip', `${item.day}: ${item.posts} posts, ${item.engagements} engagements`);
            grid.appendChild(cell);
        });
    }
    
    getWeeklyHeatmapData() {
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        return days.map(day => ({
            day,
            posts: Math.floor(Math.random() * 6) + 1,
            engagements: Math.floor(Math.random() * 300) + 100
        }));
    }
    
    getHeatmapIntensity(posts) {
        if (posts <= 1) return 'low';
        if (posts <= 3) return 'medium';
        if (posts <= 5) return 'high';
        return 'very-high';
    }
    
    // Analytics helper methods
    getTimeLabels(timeRange) {
        const now = new Date();
        const labels = [];
        
        switch (timeRange) {
            case '7d':
                for (let i = 6; i >= 0; i--) {
                    const date = new Date(now);
                    date.setDate(date.getDate() - i);
                    labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
                }
                break;
            case '30d':
                for (let i = 29; i >= 0; i -= 2) {
                    const date = new Date(now);
                    date.setDate(date.getDate() - i);
                    labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
                }
                break;
            case '90d':
                for (let i = 12; i >= 0; i--) {
                    const date = new Date(now);
                    date.setDate(date.getDate() - (i * 7));
                    labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
                }
                break;
            case '1y':
                for (let i = 11; i >= 0; i--) {
                    const date = new Date(now);
                    date.setMonth(date.getMonth() - i);
                    labels.push(date.toLocaleDateString('en-US', { month: 'short' }));
                }
                break;
        }
        
        return labels;
    }
    
    generateDemoData(length, base, variance) {
        return Array.from({ length }, () => 
            Math.floor(base + (Math.random() - 0.5) * variance * 2)
        );
    }
    
    generateGrowthData(length, start, increment) {
        const data = [];
        let current = start;
        
        for (let i = 0; i < length; i++) {
            data.push(current);
            current += Math.floor(increment + (Math.random() - 0.5) * increment * 0.5);
        }
        
        return data;
    }
    
    // Analytics control methods
    updateAnalyticsTimeRange() {
        this.loadAnalyticsData();
    }
    
    filterAnalytics() {
        this.loadAnalyticsCharts();
    }
    
    exportAnalytics() {
        // In a real implementation, this would export analytics data
        this.showNotification('Analytics export feature coming soon!', 'info');
    }
    
    viewAllContent() {
        // Navigate to content review page
        this.showPage('content-review');
    }

    async loadContentReviewData() {
        // Load content review data with pagination and filtering
        console.log('Loading content review data...');
        
        try {
            await this.loadContentList();
            this.setupContentReviewEventListeners();
        } catch (error) {
            console.error('Error loading content review data:', error);
            this.showNotification('Failed to load content review data.', 'error');
        }
    }
    
    setupContentReviewEventListeners() {
        // Search on Enter key
        const searchInput = document.getElementById('contentSearch');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchContent();
                }
            });
        }
    }
    
    async loadContentList(page = 1, filters = {}) {
        const container = document.getElementById('contentItemsContainer');
        const loadingState = document.getElementById('contentLoading');
        const emptyState = document.getElementById('contentEmpty');
        const pagination = document.getElementById('contentPagination');
        
        if (!container) return;
        
        // Show loading state
        loadingState.style.display = 'flex';
        emptyState.style.display = 'none';
        pagination.style.display = 'none';
        
        try {
            const token = localStorage.getItem('postsync_access_token');
            
            // Build query parameters
            const params = new URLSearchParams({
                page: page.toString(),
                page_size: '10'
            });
            
            // Add filters
            if (filters.status) params.append('status', filters.status);
            if (filters.platform) params.append('platform', filters.platform);
            if (filters.topic) params.append('topic', filters.topic);
            if (filters.search) params.append('search', filters.search);
            
            const response = await fetch(`http://127.0.0.1:8000/api/v1/content?${params}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderContentList(data.items || []);
                this.renderPagination(data.pagination || { page: 1, total_pages: 1, total_items: 0 });
                
                // Store current state
                this.currentContentPage = page;
                this.currentContentFilters = filters;
                
            } else {
                // Handle API error - show empty state with demo data
                this.renderContentList(this.getDemoContentData());
                this.renderPagination({ page: 1, total_pages: 1, total_items: 3 });
            }
            
        } catch (error) {
            console.error('Error loading content list:', error);
            // Show demo data as fallback
            this.renderContentList(this.getDemoContentData());
            this.renderPagination({ page: 1, total_pages: 1, total_items: 3 });
        } finally {
            loadingState.style.display = 'none';
        }
    }
    
    getDemoContentData() {
        return [
            {
                id: '1',
                title: 'AI Research Breakthrough in Machine Learning',
                content: '🚀 Just discovered an incredible breakthrough in AI research that\'s changing everything we know about machine learning algorithms. This development could revolutionize how we approach data processing and automation.',
                platform: 'linkedin',
                status: 'pending',
                topic: 'ai_technology',
                quality_score: 0.92,
                fact_check_score: 0.95,
                created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
            },
            {
                id: '2',
                title: 'Startup Funding Trends 2024',
                content: '📈 The startup funding landscape is evolving rapidly. Here are the key trends every entrepreneur should know about securing investment in 2024. Thread 🧵',
                platform: 'twitter',
                status: 'approved',
                topic: 'startup_news',
                quality_score: 0.88,
                fact_check_score: 0.91,
                created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString()
            },
            {
                id: '3',
                title: 'Professional Development in Tech Industry',
                content: 'Sharing insights on career growth in the tech industry. Key strategies for advancing your career and building meaningful professional relationships. What has worked best for you?',
                platform: 'linkedin',
                status: 'scheduled',
                topic: 'industry_trends',
                quality_score: 0.85,
                fact_check_score: 0.89,
                created_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString()
            }
        ];
    }
    
    renderContentList(contentItems) {
        const container = document.getElementById('contentItemsContainer');
        const emptyState = document.getElementById('contentEmpty');
        
        if (!container) return;
        
        // Clear previous content (except loading and empty states)
        const existingItems = container.querySelectorAll('.content-item');
        existingItems.forEach(item => item.remove());
        
        if (!contentItems || contentItems.length === 0) {
            emptyState.style.display = 'flex';
            return;
        }
        
        emptyState.style.display = 'none';
        
        contentItems.forEach(item => {
            const contentElement = this.createContentItemElement(item);
            container.appendChild(contentElement);
        });
    }
    
    createContentItemElement(item) {
        const div = document.createElement('div');
        div.className = 'content-item';
        div.setAttribute('data-status', item.status);
        div.setAttribute('data-id', item.id);
        
        const timeAgo = this.getTimeAgo(new Date(item.created_at));
        const platformClass = item.platform.toLowerCase();
        const platformIcon = this.getPlatformIcon(item.platform);
        
        div.innerHTML = `
            <input type="checkbox" class="content-item-checkbox" onchange="dashboard.toggleContentSelection('${item.id}')">
            <div class="content-preview">
                <div class="platform-badge ${platformClass}">
                    <i class="${platformIcon}"></i>
                    ${item.platform.charAt(0).toUpperCase() + item.platform.slice(1)}
                </div>
                <h4>${item.title}</h4>
                <p>${item.content}</p>
                <div class="content-metrics">
                    <span class="metric">
                        <i class="fas fa-check-circle"></i>
                        ${Math.round((item.fact_check_score || 0) * 100)}% Fact-check
                    </span>
                    <span class="metric">
                        <i class="fas fa-chart-line"></i>
                        ${Math.round((item.quality_score || 0) * 100)}% Quality Score
                    </span>
                    <span class="metric">
                        <i class="fas fa-clock"></i>
                        ${timeAgo}
                    </span>
                </div>
            </div>
            <div class="content-actions">
                <button class="btn btn-success" onclick="dashboard.approveContent('${item.id}')">
                    <i class="fas fa-check"></i>
                    Approve
                </button>
                <button class="btn btn-error" onclick="dashboard.rejectContent('${item.id}')">
                    <i class="fas fa-times"></i>
                    Reject
                </button>
                <button class="btn btn-secondary" onclick="dashboard.editContent('${item.id}')">
                    <i class="fas fa-edit"></i>
                    Edit
                </button>
            </div>
        `;
        
        return div;
    }
    
    getPlatformIcon(platform) {
        const icons = {
            linkedin: 'fab fa-linkedin',
            twitter: 'fas fa-times'
        };
        return icons[platform.toLowerCase()] || 'fas fa-share-alt';
    }
    
    renderPagination(pagination) {
        const container = document.getElementById('contentPagination');
        const infoElement = document.getElementById('paginationInfo');
        const pageNumbers = document.getElementById('pageNumbers');
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        
        if (!container) return;
        
        const { page, total_pages, total_items, page_size = 10 } = pagination;
        const startItem = ((page - 1) * page_size) + 1;
        const endItem = Math.min(page * page_size, total_items);
        
        // Update pagination info
        if (infoElement) {
            infoElement.textContent = `Showing ${startItem}-${endItem} of ${total_items} items`;
        }
        
        // Update previous/next buttons
        if (prevBtn) {
            prevBtn.disabled = page <= 1;
        }
        if (nextBtn) {
            nextBtn.disabled = page >= total_pages;
        }
        
        // Generate page numbers
        if (pageNumbers) {
            pageNumbers.innerHTML = '';
            
            const maxPages = 5;
            let startPage = Math.max(1, page - Math.floor(maxPages / 2));
            let endPage = Math.min(total_pages, startPage + maxPages - 1);
            
            if (endPage - startPage + 1 < maxPages) {
                startPage = Math.max(1, endPage - maxPages + 1);
            }
            
            for (let i = startPage; i <= endPage; i++) {
                const pageBtn = document.createElement('button');
                pageBtn.className = `page-number ${i === page ? 'active' : ''}`;
                pageBtn.textContent = i;
                pageBtn.onclick = () => this.goToPage(i);
                pageNumbers.appendChild(pageBtn);
            }
        }
        
        container.style.display = total_pages > 1 ? 'flex' : 'none';
    }
    
    // Content Review Methods
    searchContent() {
        const searchInput = document.getElementById('contentSearch');
        const searchTerm = searchInput ? searchInput.value.trim() : '';
        
        const filters = { ...this.currentContentFilters };
        if (searchTerm) {
            filters.search = searchTerm;
        } else {
            delete filters.search;
        }
        
        this.loadContentList(1, filters);
    }
    
    filterContent() {
        const statusFilter = document.getElementById('statusFilter')?.value || '';
        const platformFilter = document.getElementById('platformFilter')?.value || '';
        const topicFilter = document.getElementById('topicFilter')?.value || '';
        
        const filters = {};
        if (statusFilter) filters.status = statusFilter;
        if (platformFilter) filters.platform = platformFilter;
        if (topicFilter) filters.topic = topicFilter;
        
        // Preserve search term
        if (this.currentContentFilters?.search) {
            filters.search = this.currentContentFilters.search;
        }
        
        this.loadContentList(1, filters);
    }
    
    toggleContentSelection(contentId) {
        const checkbox = document.querySelector(`[data-id="${contentId}"] .content-item-checkbox`);
        const contentItem = document.querySelector(`[data-id="${contentId}"]`);
        
        if (checkbox && contentItem) {
            if (checkbox.checked) {
                contentItem.classList.add('selected');
            } else {
                contentItem.classList.remove('selected');
            }
            this.updateBulkActionButtons();
        }
    }
    
    selectAllContent() {
        const checkboxes = document.querySelectorAll('.content-item-checkbox');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = !allChecked;
            const contentItem = checkbox.closest('.content-item');
            if (contentItem) {
                if (checkbox.checked) {
                    contentItem.classList.add('selected');
                } else {
                    contentItem.classList.remove('selected');
                }
            }
        });
        
        this.updateBulkActionButtons();
    }
    
    updateBulkActionButtons() {
        const selectedCount = document.querySelectorAll('.content-item-checkbox:checked').length;
        const bulkApproveBtn = document.getElementById('bulkApproveBtn');
        const bulkRejectBtn = document.getElementById('bulkRejectBtn');
        
        if (bulkApproveBtn) {
            bulkApproveBtn.disabled = selectedCount === 0;
        }
        if (bulkRejectBtn) {
            bulkRejectBtn.disabled = selectedCount === 0;
        }
    }
    
    async approveContent(contentId) {
        try {
            // In a real implementation, this would call the API
            console.log('Approving content:', contentId);
            this.showNotification('Content approved successfully!', 'success');
            
            // Update the UI
            const contentItem = document.querySelector(`[data-id="${contentId}"]`);
            if (contentItem) {
                contentItem.setAttribute('data-status', 'approved');
            }
        } catch (error) {
            console.error('Error approving content:', error);
            this.showNotification('Failed to approve content.', 'error');
        }
    }
    
    async rejectContent(contentId) {
        try {
            // In a real implementation, this would call the API
            console.log('Rejecting content:', contentId);
            this.showNotification('Content rejected.', 'success');
            
            // Update the UI
            const contentItem = document.querySelector(`[data-id="${contentId}"]`);
            if (contentItem) {
                contentItem.setAttribute('data-status', 'rejected');
            }
        } catch (error) {
            console.error('Error rejecting content:', error);
            this.showNotification('Failed to reject content.', 'error');
        }
    }
    
    editContent(contentId) {
        // In a real implementation, this would open an edit modal
        console.log('Editing content:', contentId);
        this.showNotification('Edit functionality coming soon!', 'info');
    }
    
    async bulkApprove() {
        const selectedCheckboxes = document.querySelectorAll('.content-item-checkbox:checked');
        const contentIds = Array.from(selectedCheckboxes).map(cb => 
            cb.closest('.content-item').getAttribute('data-id')
        );
        
        if (contentIds.length === 0) return;
        
        try {
            // In a real implementation, this would call the bulk API
            console.log('Bulk approving content:', contentIds);
            this.showNotification(`${contentIds.length} items approved successfully!`, 'success');
            
            // Update UI
            contentIds.forEach(id => {
                const contentItem = document.querySelector(`[data-id="${id}"]`);
                if (contentItem) {
                    contentItem.setAttribute('data-status', 'approved');
                    const checkbox = contentItem.querySelector('.content-item-checkbox');
                    if (checkbox) checkbox.checked = false;
                    contentItem.classList.remove('selected');
                }
            });
            
            this.updateBulkActionButtons();
        } catch (error) {
            console.error('Error bulk approving content:', error);
            this.showNotification('Failed to approve content.', 'error');
        }
    }
    
    async bulkReject() {
        const selectedCheckboxes = document.querySelectorAll('.content-item-checkbox:checked');
        const contentIds = Array.from(selectedCheckboxes).map(cb => 
            cb.closest('.content-item').getAttribute('data-id')
        );
        
        if (contentIds.length === 0) return;
        
        try {
            // In a real implementation, this would call the bulk API
            console.log('Bulk rejecting content:', contentIds);
            this.showNotification(`${contentIds.length} items rejected.`, 'success');
            
            // Update UI
            contentIds.forEach(id => {
                const contentItem = document.querySelector(`[data-id="${id}"]`);
                if (contentItem) {
                    contentItem.setAttribute('data-status', 'rejected');
                    const checkbox = contentItem.querySelector('.content-item-checkbox');
                    if (checkbox) checkbox.checked = false;
                    contentItem.classList.remove('selected');
                }
            });
            
            this.updateBulkActionButtons();
        } catch (error) {
            console.error('Error bulk rejecting content:', error);
            this.showNotification('Failed to reject content.', 'error');
        }
    }
    
    // Pagination Methods
    goToPage(page) {
        this.loadContentList(page, this.currentContentFilters || {});
    }
    
    prevPage() {
        if (this.currentContentPage > 1) {
            this.goToPage(this.currentContentPage - 1);
        }
    }
    
    nextPage() {
        this.goToPage((this.currentContentPage || 1) + 1);
    }

    async loadScheduleData() {
        // Load schedule data
        console.log('Loading schedule data...');
    }

    async loadSettingsData() {
        // Load settings data
        console.log('Loading settings data...');
        
        try {
            await Promise.all([
                this.loadUserSettings(),
                this.loadConnectedAccounts()
            ]);
        } catch (error) {
            console.error('Error loading settings data:', error);
            this.showNotification('Failed to load settings data.', 'error');
        }
    }
    
    async loadUserSettings() {
        try {
            const token = localStorage.getItem('postsync_access_token');
            
            // In a real implementation, this would fetch user settings from API
            // For now, we'll load from localStorage or use defaults
            const settings = this.getUserSettings();
            this.populateSettingsForm(settings);
            
        } catch (error) {
            console.error('Error loading user settings:', error);
            // Use default settings
            this.populateSettingsForm(this.getDefaultSettings());
        }
    }
    
    getUserSettings() {
        // Load settings from localStorage or return defaults
        const savedSettings = localStorage.getItem('postsync_user_settings');
        if (savedSettings) {
            try {
                return { ...this.getDefaultSettings(), ...JSON.parse(savedSettings) };
            } catch (e) {
                console.error('Error parsing saved settings:', e);
            }
        }
        return this.getDefaultSettings();
    }
    
    getDefaultSettings() {
        return {
            postingFrequency: 'every_2_days',
            qualityThreshold: 85,
            autoApproval: false,
            contentTopics: ['ai_technology', 'business_insights'],
            emailNotifications: true,
            pushNotifications: false,
            weeklyReports: true,
            notificationTime: '17:00',
            contentStyle: 'professional',
            contentLength: 'medium',
            includeHashtags: true,
            maxHashtags: 5,
            apiKey: 'pk_live_••••••••••••••••',
            webhookUrl: '',
            rateLimiting: 'moderate'
        };
    }
    
    populateSettingsForm(settings) {
        // Populate form fields with settings
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = settings[key];
                } else if (element.type === 'range') {
                    element.value = settings[key];
                    // Update range display
                    const displayElement = document.getElementById(key + 'Value');
                    if (displayElement) {
                        displayElement.textContent = key === 'qualityThreshold' ? `${settings[key]}%` : settings[key];
                    }
                } else {
                    element.value = settings[key];
                }
            }
        });
        
        // Handle topic tags
        this.updateTopicTags(settings.contentTopics || []);
        
        // Store current settings
        this.currentSettings = settings;
    }
    
    updateTopicTags(activeTopics) {
        const topicTags = document.querySelectorAll('.topic-tag');
        topicTags.forEach(tag => {
            const topic = tag.getAttribute('data-topic');
            const isActive = activeTopics.includes(topic);
            
            tag.classList.toggle('active', isActive);
            
            const button = tag.querySelector('button');
            const icon = button.querySelector('i');
            
            if (isActive) {
                icon.className = 'fas fa-times';
            } else {
                icon.className = 'fas fa-plus';
            }
        });
    }
    
    async loadConnectedAccounts() {
        const container = document.getElementById('connectedAccounts');
        if (!container) return;
        
        try {
            // Try to fetch real connected accounts from API
            const token = localStorage.getItem('postsync_access_token');
            if (token) {
                const response = await fetch('http://127.0.0.1:8000/api/v1/users/social-accounts', {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const socialAccounts = await response.json();
                    const accounts = this.convertToAccountFormat(socialAccounts);
                    this.renderConnectedAccounts(accounts);
                    return;
                }
            }
            
            // Fallback to default empty state (not mock data)
            const accounts = this.getEmptyConnectedAccounts();
            this.renderConnectedAccounts(accounts);
            
        } catch (error) {
            console.error('Error loading connected accounts:', error);
            // Show empty state instead of fake data
            this.renderConnectedAccounts(this.getEmptyConnectedAccounts());
        }
    }
    
    convertToAccountFormat(socialAccountsData) {
        const connectedAccounts = socialAccountsData.connected_accounts || {};
        
        // Default account structure
        const defaultAccounts = [
            {
                platform: 'linkedin',
                name: 'LinkedIn',
                icon: 'fab fa-linkedin',
                connected: false,
                username: null
            },
            {
                platform: 'twitter',
                name: 'X (Twitter)',
                icon: 'fas fa-times',
                connected: false,
                username: null
            }
        ];
        
        // Update with real connection data
        defaultAccounts.forEach(account => {
            const platformData = connectedAccounts[account.platform];
            if (platformData && platformData.is_active) {
                account.connected = true;
                account.username = platformData.username;
            }
        });
        
        return defaultAccounts;
    }
    
    getEmptyConnectedAccounts() {
        return [
            {
                platform: 'linkedin',
                name: 'LinkedIn',
                icon: 'fab fa-linkedin',
                connected: false,
                username: null
            },
            {
                platform: 'twitter',
                name: 'X (Twitter)',
                icon: 'fas fa-times',
                connected: false,
                username: null
            }
        ];
    }
    
    getDemoConnectedAccounts() {
        return [
            {
                platform: 'linkedin',
                name: 'LinkedIn',
                icon: 'fab fa-linkedin',
                connected: true,
                username: 'postsync_user'
            },
            {
                platform: 'twitter',
                name: 'X (Twitter)',
                icon: 'fas fa-times',
                connected: false,
                username: null
            }
        ];
    }
    
    renderConnectedAccounts(accounts) {
        const container = document.getElementById('connectedAccounts');
        if (!container) return;
        
        container.innerHTML = '';
        
        accounts.forEach(account => {
            const accountElement = document.createElement('div');
            accountElement.className = 'account-item';
            accountElement.setAttribute('data-platform', account.platform);
            
            const statusText = account.connected ? 'Connected' : 'Not Connected';
            const statusClass = account.connected ? 'connected' : 'disconnected';
            const buttonText = account.connected ? 'Disconnect' : 'Connect';
            const buttonClass = account.connected ? 'btn-disconnect' : 'btn-connect';
            const buttonAction = account.connected ? 'disconnectAccount' : 'connectAccount';
            
            accountElement.innerHTML = `
                <div class="account-info">
                    <i class="${account.icon}"></i>
                    <span>${account.name}</span>
                </div>
                <div class="account-actions">
                    <span class="status ${statusClass}">${statusText}</span>
                    <button class="${buttonClass}" onclick="dashboard.${buttonAction}('${account.platform}')">
                        ${buttonText}
                    </button>
                </div>
            `;
            
            container.appendChild(accountElement);
        });
    }
    
    // Settings control methods
    updateSetting(key, value) {
        if (!this.currentSettings) {
            this.currentSettings = this.getDefaultSettings();
        }
        
        this.currentSettings[key] = value;
        console.log(`Setting updated: ${key} = ${value}`);
        
        // Show unsaved changes indicator
        this.markSettingsChanged();
    }
    
    updateQualityThreshold(value) {
        const displayElement = document.getElementById('qualityThresholdValue');
        if (displayElement) {
            displayElement.textContent = `${value}%`;
        }
        this.updateSetting('qualityThreshold', parseInt(value));
    }
    
    updateMaxHashtags(value) {
        const displayElement = document.getElementById('maxHashtagsValue');
        if (displayElement) {
            displayElement.textContent = value;
        }
        this.updateSetting('maxHashtags', parseInt(value));
    }
    
    toggleTopic(topic) {
        if (!this.currentSettings) {
            this.currentSettings = this.getDefaultSettings();
        }
        
        const currentTopics = this.currentSettings.contentTopics || [];
        const index = currentTopics.indexOf(topic);
        
        if (index > -1) {
            // Remove topic
            currentTopics.splice(index, 1);
        } else {
            // Add topic
            currentTopics.push(topic);
        }
        
        this.currentSettings.contentTopics = currentTopics;
        this.updateTopicTags(currentTopics);
        this.markSettingsChanged();
        
        console.log('Topics updated:', currentTopics);
    }
    
    async connectAccount(platform) {
        try {
            // Use existing OAuth flow
            const response = await this.connectSocialAccount(platform);
            if (response) {
                this.showNotification(`${platform.charAt(0).toUpperCase() + platform.slice(1)} connected successfully!`, 'success');
                await this.loadConnectedAccounts(); // Refresh the accounts list
            }
        } catch (error) {
            console.error(`Error connecting ${platform}:`, error);
            this.showNotification(`Failed to connect ${platform}.`, 'error');
        }
    }
    
    async disconnectAccount(platform) {
        try {
            const response = await this.disconnectSocialAccount(platform);
            if (response) {
                this.showNotification(`${platform.charAt(0).toUpperCase() + platform.slice(1)} disconnected.`, 'success');
                await this.loadConnectedAccounts(); // Refresh the accounts list
            }
        } catch (error) {
            console.error(`Error disconnecting ${platform}:`, error);
            this.showNotification(`Failed to disconnect ${platform}.`, 'error');
        }
    }
    
    async refreshConnections() {
        this.showNotification('Refreshing connections...', 'info');
        await this.loadConnectedAccounts();
        this.showNotification('Connections refreshed.', 'success');
    }
    
    regenerateApiKey() {
        // Generate a new API key
        const newKey = 'pk_live_' + Math.random().toString(36).substring(2, 18);
        const apiKeyInput = document.getElementById('apiKey');
        
        if (apiKeyInput) {
            apiKeyInput.value = newKey;
            this.updateSetting('apiKey', newKey);
            this.showNotification('API key regenerated successfully!', 'success');
        }
    }
    
    markSettingsChanged() {
        // Add visual indicator for unsaved changes
        const saveButton = document.querySelector('.settings-actions .btn-primary');
        if (saveButton && !saveButton.classList.contains('unsaved')) {
            saveButton.classList.add('unsaved');
            saveButton.innerHTML = '<i class="fas fa-save"></i> Save Changes *';
        }
    }
    
    async saveSettings(event) {
        if (event) {
            event.preventDefault();
        }
        
        try {
            // Save settings to localStorage (in a real app, this would be an API call)
            localStorage.setItem('postsync_user_settings', JSON.stringify(this.currentSettings));
            
            // In a real implementation, make API call to save settings
            // const response = await this.saveUserSettings(this.currentSettings);
            
            this.showNotification('Settings saved successfully!', 'success');
            
            // Remove unsaved changes indicator
            const saveButton = document.querySelector('.settings-actions .btn-primary');
            if (saveButton) {
                saveButton.classList.remove('unsaved');
                saveButton.innerHTML = '<i class="fas fa-save"></i> Save Changes';
            }
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Failed to save settings.', 'error');
        }
    }
    
    resetSettings() {
        if (confirm('Are you sure you want to reset all settings to defaults? This action cannot be undone.')) {
            const defaultSettings = this.getDefaultSettings();
            this.populateSettingsForm(defaultSettings);
            this.currentSettings = defaultSettings;
            this.markSettingsChanged();
            this.showNotification('Settings reset to defaults.', 'info');
        }
    }
    
    async saveUserSettings(settings) {
        // In a real implementation, this would make an API call
        const token = localStorage.getItem('postsync_access_token');
        
        const response = await fetch('http://127.0.0.1:8000/api/v1/users/settings', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Failed to save settings');
        }
        
        return await response.json();
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
            console.log('Loading user data with token...');
            
            const response = await fetch('http://127.0.0.1:8000/api/v1/auth/me', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                }
            });

            console.log('User data response status:', response.status);

            if (response.ok) {
                const userData = await response.json();
                console.log('User data loaded successfully:', userData.email);
                this.updateUserDisplay(userData);
            } else if (response.status === 401) {
                console.log('Token expired, redirecting to login');
                localStorage.removeItem('postsync_access_token');
                this.showNotification('Session expired. Please login again.', 'error');
                setTimeout(() => {
                    window.location.href = '/frontend/index.html';
                }, 2000);
                return;
            } else {
                throw new Error(`Failed to fetch user data: ${response.status}`);
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
                title: 'X thread published',
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
        
        // Set flag to prevent navigation interference
        this.isGeneratingContent = true;
        
        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        button.disabled = true;

        try {
            // Get auth token from localStorage
            const token = localStorage.getItem('postsync_access_token');
            if (!token) {
                this.showNotification('Please login first to generate content', 'error');
                setTimeout(() => {
                    window.location.href = '/frontend/index.html';
                }, 2000);
                return;
            }

            // Make API call to generate content from fresh Reddit discovery
            const response = await fetch('http://127.0.0.1:8000/api/v1/content/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification('✅ New content generated successfully! Refreshing dashboard...', 'success');
                
                // Refresh dashboard data to show new content
                setTimeout(() => {
                    this.loadDashboardData();
                }, 1000);
                
            } else {
                throw new Error('Failed to generate content');
            }

        } catch (error) {
            console.error('Content generation failed:', error);
            this.showNotification('Content generation failed. Please try again or check your connection.', 'error');
        } finally {
            // Restore button state and clear flag
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
                this.isGeneratingContent = false;
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

    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        
        return date.toLocaleDateString();
    }

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    getPlatformIcon(platform) {
        const icons = {
            'linkedin': 'fab fa-linkedin',
            'twitter': 'fab fa-twitter',
            'facebook': 'fab fa-facebook',
            'instagram': 'fab fa-instagram'
        };
        return icons[platform.toLowerCase()] || 'fas fa-share-alt';
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
            window.location.href = '/frontend/index.html';
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

// Global function to close scheduling modal
function closeSchedulingModal() {
    const modal = document.getElementById('schedulingModal');
    if (modal) {
        modal.remove();
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
    .event-dot.twitter { background: #000000; }
    .event-dot.linkedin { background: #0077B5; }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardApp();
    window.dashboardApp = window.dashboard; // Keep both for compatibility
    console.log('✅ Dashboard initialized successfully');
    
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

// Debug functions for testing Generate Content
window.testGenerateContent = function() {
    console.log('🧪 Testing Generate Content from console...');
    if (window.dashboard) {
        window.dashboard.generateContent();
    } else if (window.dashboardApp) {
        window.dashboardApp.generateContent();
    } else {
        console.error('❌ Dashboard not initialized');
        console.log('💡 Try refreshing the page and wait for "✅ Dashboard initialized successfully"');
    }
};

window.checkGenerateButton = function() {
    const buttons = document.querySelectorAll('button');
    console.log('🔍 All buttons found:', buttons.length);
    
    for (let i = 0; i < buttons.length; i++) {
        const btn = buttons[i];
        if (btn.textContent.includes('Generate Content')) {
            console.log('✅ Found Generate Content button:', btn);
            console.log('   - Text:', btn.textContent);
            console.log('   - Classes:', btn.className);
            console.log('   - Disabled:', btn.disabled);
            return btn;
        }
    }
    console.error('❌ Generate Content button not found');
    return null;
};