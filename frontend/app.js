// ==========================================================================
// SIAB WhatsApp Automation Engine - Core Application Logic
// ==========================================================================

const app = {
    state: {
        currentTab: 'dashboard',
        stats: null,
        schools: [],
        totalSchoolsCount: 575,
        currentPage: 1,
        pageSize: 20,
        totalPages: 1,
        activeSchoolId: 1,
        activeSchool: null,
        curriculumList: [],
        ticketsList: [],
        districtsList: [],
        config: {},
        ws: null,
        bucketChart: null,
        subjectChart: null
    },

    init() {
        console.log("Initializing SIAB WhatsApp Automation Engine UI...");
        this.setupTheme();
        this.setupNavigation();
        this.setupEventListeners();
        this.initWebSocket();
        
        // Initial Data Load
        this.fetchDashboardStats();
        this.fetchDistricts();
        this.fetchSchools(1);
        this.fetchAutomationConfig();
        this.fetchCurriculum();
        this.fetchTickets();
        this.initSimulator(1);
    },

    // ==================== THEME & NAVIGATION ====================

    setupTheme() {
        const savedTheme = localStorage.getItem('siab_theme') || 'theme-dark';
        document.body.className = savedTheme;

        const toggleBtn = document.getElementById('btn-theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const isDark = document.body.classList.contains('theme-dark');
                const newTheme = isDark ? 'theme-light' : 'theme-dark';
                document.body.className = newTheme;
                localStorage.setItem('siab_theme', newTheme);
                if (this.state.bucketChart) this.renderCharts();
            });
        }
    },

    setupNavigation() {
        const navButtons = document.querySelectorAll('.nav-item');
        navButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.getAttribute('data-tab');
                this.switchTab(tab);
            });
        });
    },

    switchTab(tabId) {
        this.state.currentTab = tabId;
        
        // Update nav items
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        });

        // Update tab contents
        document.querySelectorAll('.tab-content').forEach(sec => {
            sec.classList.toggle('active', sec.id === `tab-${tabId}`);
        });

        // Update titles
        const titles = {
            'dashboard': {
                title: 'Executive Telemetry Overview',
                sub: 'Monitoring 240,000+ students across 575 active School-in-a-Box locations'
            },
            'schools': {
                title: 'School Fleet & Telemetry Monitor',
                sub: 'Live device sync health, weekly usage hours, and bucket classification'
            },
            'automation': {
                title: '3-Step Friday Automation Engine',
                sub: 'Configure thresholds, dry-run previews, and batch dispatch human-tone nudges'
            },
            'simulator': {
                title: 'WhatsApp Mobile Simulator & 2-Way Bot',
                sub: 'Live smartphone preview: simulate teacher interactions and auto-ticketing'
            },
            'curriculum-tickets': {
                title: 'Curriculum Catalog & Support Tickets Desk',
                sub: 'Offline pedagogical resources & automated hardware/power escalation'
            }
        };

        if (titles[tabId]) {
            document.getElementById('page-title').innerText = titles[tabId].title;
            document.getElementById('page-subtitle').innerText = titles[tabId].sub;
        }

        lucide.createIcons();

        // Refetch or redraw if necessary
        if (tabId === 'dashboard') {
            this.fetchDashboardStats();
        } else if (tabId === 'schools') {
            this.fetchSchools(this.state.currentPage);
        } else if (tabId === 'simulator') {
            this.loadSimulatorChat(this.state.activeSchoolId);
        }
    },

    // ==================== EVENT LISTENERS ====================

    setupEventListeners() {
        // Quick Top Bar Buttons
        document.getElementById('btn-quick-preview').addEventListener('click', () => {
            this.switchTab('automation');
            this.runAutomationDryRun();
        });

        document.getElementById('btn-quick-run-engine').addEventListener('click', () => {
            this.switchTab('automation');
            this.executeAutomationDispatch();
        });

        // Automation Tab Buttons
        document.getElementById('btn-run-preview-tab').addEventListener('click', () => {
            this.runAutomationDryRun();
        });

        document.getElementById('btn-run-dispatch-tab').addEventListener('click', () => {
            this.executeAutomationDispatch();
        });

        // Config Sliders
        const threshGreat = document.getElementById('input-thresh-great');
        threshGreat.addEventListener('input', (e) => {
            document.getElementById('val-thresh-great').innerText = `≥ ${parseFloat(e.target.value).toFixed(1)} hrs/week`;
        });

        const threshNudge = document.getElementById('input-thresh-nudge');
        threshNudge.addEventListener('input', (e) => {
            document.getElementById('val-thresh-nudge').innerText = `< ${parseFloat(e.target.value).toFixed(1)} hrs/week`;
        });

        const threshOffline = document.getElementById('input-thresh-offline');
        threshOffline.addEventListener('input', (e) => {
            document.getElementById('val-thresh-offline').innerText = `> ${parseFloat(e.target.value).toFixed(1)} days unsynced`;
        });

        // Rules Form Submit
        document.getElementById('form-rules-config').addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                threshold_doing_great_hours: document.getElementById('input-thresh-great').value,
                threshold_needs_nudge_hours: document.getElementById('input-thresh-nudge').value,
                threshold_offline_days: document.getElementById('input-thresh-offline').value,
                schedule_day: document.getElementById('input-schedule-day').value,
                schedule_time: document.getElementById('input-schedule-time').value,
                whatsapp_provider: document.getElementById('select-whatsapp-provider').value
            };

            try {
                const res = await fetch('/api/automation/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    this.showToast('Threshold rules and schedule updated successfully!', 'success');
                    this.logTerminal(`[Config] Updated thresholds: Great ≥ ${payload.threshold_doing_great_hours}h, Nudge < ${payload.threshold_needs_nudge_hours}h, Offline > ${payload.threshold_offline_days}d`, 'info');
                }
            } catch (err) {
                this.showToast('Failed to update config', 'error');
            }
        });

        // School Fleet Filters
        document.getElementById('input-search-schools').addEventListener('input', () => this.debounce(() => this.fetchSchools(1), 300)());
        document.getElementById('select-bucket-filter').addEventListener('change', () => this.fetchSchools(1));
        document.getElementById('select-district-filter').addEventListener('change', () => this.fetchSchools(1));
        document.getElementById('select-sort-filter').addEventListener('change', () => this.fetchSchools(1));

        // Pagination Buttons
        document.getElementById('btn-prev-page').addEventListener('click', () => {
            if (this.state.currentPage > 1) this.fetchSchools(this.state.currentPage - 1);
        });
        document.getElementById('btn-next-page').addEventListener('click', () => {
            if (this.state.currentPage < this.state.totalPages) this.fetchSchools(this.state.currentPage + 1);
        });

        // Simulator Interaction
        document.getElementById('sim-btn-send').addEventListener('click', () => this.sendSimulatorTeacherMessage());
        document.getElementById('sim-input-message').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendSimulatorTeacherMessage();
        });

        // Quick Reply Chips
        document.querySelectorAll('.chip-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const msg = btn.getAttribute('data-msg');
                document.getElementById('sim-input-message').value = msg;
                this.sendSimulatorTeacherMessage();
            });
        });

        // Manual Operator Message
        document.getElementById('btn-send-manual-msg').addEventListener('click', () => this.sendManualOperatorMessage());

        // Drawer Close
        document.getElementById('btn-close-drawer').addEventListener('click', () => this.closeDrawer());
        document.getElementById('drawer-backdrop').addEventListener('click', (e) => {
            if (e.target.id === 'drawer-backdrop') this.closeDrawer();
        });

        // Ticket Filter
        document.getElementById('select-ticket-status-filter').addEventListener('change', (e) => {
            this.fetchTickets(e.target.value);
        });
    },

    // ==================== DASHBOARD STATS & CHARTS ====================

    async fetchDashboardStats() {
        try {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();
            this.state.stats = data;

            // Render KPIs
            document.getElementById('kpi-students').innerText = data.total_students.toLocaleString() + '+';
            document.getElementById('kpi-schools').innerText = data.total_schools;
            document.getElementById('kpi-hours').innerText = data.total_weekly_hours.toLocaleString() + ' hrs';
            document.getElementById('kpi-sync-health').innerText = data.sync_health_percentage + '%';

            const offlineCount = data.buckets.device_offline || 0;
            document.getElementById('kpi-offline-count').innerText = `${offlineCount} boxes require power check`;

            // Bucket counts
            document.getElementById('count-great').innerText = `${data.buckets.doing_great} Schools`;
            document.getElementById('count-nudge').innerText = `${data.buckets.needs_nudge} Schools`;
            document.getElementById('count-offline').innerText = `${data.buckets.device_offline} Schools`;

            // Render Recent Nudges Table
            this.renderRecentNudgesTable(data.recent_nudges);

            // Render Charts
            this.renderCharts(data);

            lucide.createIcons();
        } catch (err) {
            console.error("Error fetching stats:", err);
        }
    },

    renderRecentNudgesTable(nudges) {
        const tbody = document.getElementById('tbody-recent-nudges');
        if (!tbody) return;

        if (!nudges || nudges.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted" style="padding:24px;">No dispatches yet. Click 'Run Friday Engine' to generate nudges.</td></tr>`;
            return;
        }

        tbody.innerHTML = nudges.map(n => {
            const bucketBadge = this.getBucketBadge(n.bucket);
            const timeAgo = this.formatTimeAgo(n.dispatched_at);
            return `
                <tr>
                    <td>
                        <strong>${n.school_name}</strong><br>
                        <span class="text-muted small">${n.district}</span>
                    </td>
                    <td>${bucketBadge}</td>
                    <td>
                        <div class="msg-snippet" title="${n.message_text.replace(/"/g, '&quot;')}">${n.message_text}</div>
                    </td>
                    <td><span class="badge-green">${n.status.toUpperCase()}</span></td>
                    <td class="text-muted small">${timeAgo}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="app.openSimulatorForSchool(${n.school_id})">
                            <i data-lucide="message-circle"></i> Chat
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        lucide.createIcons();
    },

    renderCharts(data) {
        const stats = data || this.state.stats;
        if (!stats) return;

        const isDark = document.body.classList.contains('theme-dark');
        const textColor = isDark ? '#9ca3af' : '#4b5563';

        // 1. Bucket Doughnut Chart
        const ctxBucket = document.getElementById('bucketChart');
        if (ctxBucket) {
            if (this.state.bucketChart) this.state.bucketChart.destroy();
            this.state.bucketChart = new Chart(ctxBucket, {
                type: 'doughnut',
                data: {
                    labels: ['Doing Great (≥12h)', 'Needs a Nudge (<4h)', 'Device Offline (>3d)'],
                    datasets: [{
                        data: [stats.buckets.doing_great, stats.buckets.needs_nudge, stats.buckets.device_offline],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                        borderWidth: 0,
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: textColor, font: { family: 'Plus Jakarta Sans', size: 12 } }
                        }
                    },
                    cutout: '70%'
                }
            });
        }

        // 2. Subject Bar Chart
        const ctxSubject = document.getElementById('subjectChart');
        if (ctxSubject) {
            if (this.state.subjectChart) this.state.subjectChart.destroy();
            this.state.subjectChart = new Chart(ctxSubject, {
                type: 'bar',
                data: {
                    labels: ['Science (PhET)', 'Maths Lab', 'Arts / Music', 'StoryWeaver', 'STEM Projects'],
                    datasets: [{
                        label: 'Active Hours Logged',
                        data: [2840, 2190, 1150, 980, 682],
                        backgroundColor: ['#6366f1', '#06b6d4', '#ec4899', '#8b5cf6', '#10b981'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { display: false }, ticks: { color: textColor } },
                        y: { grid: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }, ticks: { color: textColor } }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
    },

    // ==================== SCHOOLS FLEET ====================

    async fetchDistricts() {
        try {
            const res = await fetch('/api/districts');
            const data = await res.json();
            this.state.districtsList = data;
            const select = document.getElementById('select-district-filter');
            if (select) {
                select.innerHTML = '<option value="all">All Districts (25+)</option>' + 
                    data.map(d => `<option value="${d.district}">${d.district} (${d.state})</option>`).join('');
            }
        } catch (err) {
            console.error("Error fetching districts:", err);
        }
    },

    async fetchSchools(page = 1) {
        this.state.currentPage = page;
        const search = document.getElementById('input-search-schools')?.value || '';
        const bucket = document.getElementById('select-bucket-filter')?.value || 'all';
        const district = document.getElementById('select-district-filter')?.value || 'all';
        const sortBy = document.getElementById('select-sort-filter')?.value || 'id';

        const params = new URLSearchParams({
            page: page,
            page_size: this.state.pageSize,
            search: search,
            bucket: bucket,
            district: district,
            sort_by: sortBy
        });

        try {
            const res = await fetch(`/api/schools?${params.toString()}`);
            const data = await res.json();
            this.state.schools = data.schools;
            this.state.totalPages = data.total_pages;

            // Render Table
            this.renderSchoolsTable(data.schools);

            // Update Pagination Info
            const start = (data.page - 1) * data.page_size + 1;
            const end = Math.min(data.page * data.page_size, data.total_count);
            document.getElementById('pagination-info').innerText = `Showing ${start}-${end} of ${data.total_count} schools`;
            document.getElementById('page-num-display').innerText = `${data.page} / ${data.total_pages || 1}`;

            document.getElementById('btn-prev-page').disabled = data.page <= 1;
            document.getElementById('btn-next-page').disabled = data.page >= data.total_pages;

            lucide.createIcons();
        } catch (err) {
            console.error("Error fetching schools:", err);
        }
    },

    renderSchoolsTable(schools) {
        const tbody = document.getElementById('tbody-schools-fleet');
        if (!tbody) return;

        if (!schools || schools.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding:28px;">No schools match your search or filter.</td></tr>`;
            return;
        }

        tbody.innerHTML = schools.map(s => {
            const bucketBadge = this.getBucketBadge(s.current_bucket);
            const timeAgo = this.formatTimeAgo(s.last_synced_at);
            const isOffline = s.current_bucket === 'device_offline';

            return `
                <tr>
                    <td><code class="text-muted">${s.school_code}</code></td>
                    <td>
                        <strong>${s.name}</strong><br>
                        <span class="text-muted small"><i data-lucide="map-pin" style="width:12px;display:inline;"></i> ${s.district}, ${s.state} (${s.students_count} students)</span>
                    </td>
                    <td>
                        <strong>${s.contact_name}</strong><br>
                        <span class="text-muted small">${s.phone_number}</span>
                    </td>
                    <td>
                        <strong>${s.weekly_usage_hours} hrs</strong><br>
                        <span class="text-muted small">${s.smart_class_sessions} sessions</span>
                    </td>
                    <td>
                        <span class="${isOffline ? 'text-danger font-weight-bold' : 'text-muted'}">${timeAgo}</span>
                    </td>
                    <td>${bucketBadge}</td>
                    <td>
                        <div style="display:flex;gap:6px;">
                            <button class="btn btn-sm btn-secondary" onclick="app.openSchoolDrawer(${s.id})" title="View Telemetry Drawer">
                                <i data-lucide="info"></i> Details
                            </button>
                            <button class="btn btn-sm btn-primary" onclick="app.openSimulatorForSchool(${s.id})" title="Open WhatsApp Simulator">
                                <i data-lucide="message-square"></i> Chat
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    // ==================== 3-STEP AUTOMATION ENGINE ====================

    async fetchAutomationConfig() {
        try {
            const res = await fetch('/api/automation/config');
            const data = await res.json();
            this.state.config = data;

            document.getElementById('input-thresh-great').value = data.threshold_doing_great_hours;
            document.getElementById('val-thresh-great').innerText = `≥ ${data.threshold_doing_great_hours} hrs/week`;

            document.getElementById('input-thresh-nudge').value = data.threshold_needs_nudge_hours;
            document.getElementById('val-thresh-nudge').innerText = `< ${data.threshold_needs_nudge_hours} hrs/week`;

            document.getElementById('input-thresh-offline').value = data.threshold_offline_days;
            document.getElementById('val-thresh-offline').innerText = `> ${data.threshold_offline_days} days unsynced`;

            document.getElementById('input-schedule-day').value = data.schedule_day;
            document.getElementById('input-schedule-time').value = data.schedule_time;
            document.getElementById('select-whatsapp-provider').value = data.whatsapp_provider;
        } catch (err) {
            console.error("Error fetching config:", err);
        }
    },

    async runAutomationDryRun() {
        this.logTerminal("[Engine] Initializing Step 1: Telemetry Data Ingestion...", "info");
        this.logTerminal("[Engine] Initializing Step 2: Running 3-Bucket Logic Classification (Dry Run)...", "info");

        try {
            const res = await fetch('/api/automation/preview');
            const data = await res.json();

            this.logTerminal(`[Classification Complete] Evaluated ${data.total_evaluated} schools:`, "success");
            this.logTerminal(`  • Doing Great: ${data.bucket_counts.doing_great} schools (Personalized celebration + STEM suggestions)`, "success");
            this.logTerminal(`  • Needs a Nudge: ${data.bucket_counts.needs_nudge} schools (Gentle supportive check-in)`, "warning");
            this.logTerminal(`  • Device Offline: ${data.bucket_counts.device_offline} schools (Proactive power/cable diagnosis)`, "error");
            this.logTerminal("[Engine] Ready to dispatch. Click 'Execute & Dispatch All Nudges' to push via WhatsApp.", "info");

            // Render Preview Table
            const wrap = document.getElementById('preview-results-wrap');
            wrap.style.display = 'block';

            document.getElementById('preview-counts-summary').innerHTML = `
                <span class="badge-great">${data.bucket_counts.doing_great} Great</span>
                <span class="badge-nudge">${data.bucket_counts.needs_nudge} Nudge</span>
                <span class="badge-offline">${data.bucket_counts.device_offline} Offline</span>
            `;

            const tbody = document.getElementById('tbody-preview-results');
            tbody.innerHTML = data.results.slice(0, 8).map(r => `
                <tr>
                    <td><strong>${r.school_name}</strong><br><span class="text-muted small">${r.contact_name} (${r.district})</span></td>
                    <td>${r.weekly_usage_hours} hrs<br><span class="text-muted small">${r.days_since_sync}d since sync</span></td>
                    <td>${this.getBucketBadge(r.bucket)}</td>
                    <td><div class="msg-snippet" title="${r.message_text.replace(/"/g, '&quot;')}">${r.message_text}</div></td>
                </tr>
            `).join('');

            lucide.createIcons();
            this.showToast('Dry run completed! Previewing 575 schools.', 'info');
        } catch (err) {
            this.logTerminal(`[Error] Dry run failed: ${err.message}`, "error");
        }
    },

    async executeAutomationDispatch() {
        this.logTerminal("[Step 1] Ingesting real-time device telemetries across 575 fleet units...", "info");
        this.logTerminal("[Step 2] Executing rule engine & updating school database records...", "info");
        this.logTerminal("[Step 3] Dispatching customized WhatsApp nudges via Gateway...", "info");

        try {
            const res = await fetch('/api/automation/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();

            this.logTerminal(`[SUCCESS] 🚀 Dispatched ${data.total_evaluated} automated WhatsApp nudges at ${data.timestamp}!`, "success");
            this.logTerminal(`  ✓ ${data.bucket_counts.doing_great} Celebratory & Curriculum messages delivered`, "success");
            this.logTerminal(`  ✓ ${data.bucket_counts.needs_nudge} Empathetic check-in nudges delivered`, "warning");
            this.logTerminal(`  ✓ ${data.bucket_counts.device_offline} Urgent power/hardware diagnostic alerts sent`, "error");

            this.showToast(`Successfully dispatched ${data.total_evaluated} WhatsApp nudges!`, 'success');
            this.fetchDashboardStats();
            this.fetchSchools(this.state.currentPage);
        } catch (err) {
            this.logTerminal(`[Error] Automation execution failed: ${err.message}`, "error");
        }
    },

    logTerminal(text, type = "info") {
        const body = document.getElementById('terminal-logs');
        if (!body) return;
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.innerText = text;
        body.appendChild(line);
        body.scrollTop = body.scrollHeight;
    },

    // ==================== WHATSAPP MOBILE SIMULATOR ====================

    async initSimulator(initialSchoolId = 1) {
        try {
            const res = await fetch('/api/schools?page=1&page_size=30');
            const data = await res.json();
            const listContainer = document.getElementById('sim-teachers-list');
            if (!listContainer) return;

            listContainer.innerHTML = data.schools.map(s => `
                <div class="chat-item ${s.id === initialSchoolId ? 'active' : ''}" id="sim-item-${s.id}" onclick="app.loadSimulatorChat(${s.id})">
                    <div class="chat-item-avatar">${s.contact_name.split(' ').map(n => n[0]).join('').slice(0, 2)}</div>
                    <div class="chat-item-details">
                        <div class="chat-item-name">${s.contact_name}</div>
                        <div class="chat-item-sub">${s.name}</div>
                    </div>
                </div>
            `).join('');

            // Setup search inside simulator
            const simSearch = document.getElementById('input-sim-search');
            if (simSearch) {
                simSearch.addEventListener('input', (e) => {
                    const val = e.target.value.toLowerCase();
                    document.querySelectorAll('.chat-item').forEach(item => {
                        item.style.display = item.innerText.toLowerCase().includes(val) ? 'flex' : 'none';
                    });
                });
            }

            this.loadSimulatorChat(initialSchoolId);
        } catch (err) {
            console.error("Error initializing simulator:", err);
        }
    },

    openSimulatorForSchool(schoolId) {
        this.switchTab('simulator');
        this.loadSimulatorChat(schoolId);
    },

    async loadSimulatorChat(schoolId) {
        this.state.activeSchoolId = schoolId;

        // Highlight active item
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
        const activeItem = document.getElementById(`sim-item-${schoolId}`);
        if (activeItem) activeItem.classList.add('active');

        try {
            // Fetch school details
            const sRes = await fetch(`/api/schools/${schoolId}`);
            const sData = await sRes.json();
            const s = sData.school;
            this.state.activeSchool = s;

            // Update Phone Header
            document.getElementById('sim-active-name').innerText = `${s.contact_name} (${s.contact_role})`;
            document.getElementById('sim-active-school').innerText = `${s.name} • ${s.phone_number}`;

            // Update Inspector
            document.getElementById('insp-bucket').className = `badge-${s.current_bucket === 'doing_great' ? 'great' : s.current_bucket === 'needs_nudge' ? 'nudge' : 'offline'}`;
            document.getElementById('insp-bucket').innerText = this.formatBucketName(s.current_bucket);
            document.getElementById('insp-hours').innerText = `${s.weekly_usage_hours} hrs`;
            document.getElementById('insp-sync').innerText = this.formatTimeAgo(s.last_synced_at);
            document.getElementById('insp-device').innerText = s.device_id;

            // Render Tickets in Inspector
            const ticketsContainer = document.getElementById('sim-tickets-list');
            if (sData.tickets && sData.tickets.length > 0) {
                ticketsContainer.innerHTML = sData.tickets.map(t => `
                    <div class="sim-ticket-card">
                        <strong>${t.ticket_code}</strong>: ${t.title}<br>
                        <span class="text-muted small">Status: <strong>${t.status.toUpperCase()}</strong> • Priority: ${t.priority}</span>
                    </div>
                `).join('');
            } else {
                ticketsContainer.innerHTML = `<span class="text-muted small">No active support tickets for this school.</span>`;
            }

            // Render Chat Messages
            this.renderChatMessages(sData.chat_history);
        } catch (err) {
            console.error("Error loading chat:", err);
        }
    },

    renderChatMessages(messages) {
        const chatBody = document.getElementById('sim-chat-body');
        if (!chatBody) return;

        if (!messages || messages.length === 0) {
            chatBody.innerHTML = `
                <div class="wa-date-pill">TODAY</div>
                <div class="text-center text-muted small" style="margin-top:20px;">No messages exchanged yet. Send a nudge or type as teacher below!</div>
            `;
            return;
        }

        chatBody.innerHTML = `
            <div class="wa-date-pill">TODAY</div>
            ${messages.map(m => {
                const isTeacher = m.sender === 'teacher';
                const bubbleClass = isTeacher ? 'wa-bubble-teacher' : 'wa-bubble-system';
                const timeStr = new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                return `
                    <div class="wa-bubble ${bubbleClass}">
                        <div class="wa-msg-text">${this.formatMessageText(m.message_text)}</div>
                        <div class="wa-meta">
                            <span>${timeStr}</span>
                            ${isTeacher ? '<span class="wa-ticks">✓✓</span>' : ''}
                        </div>
                    </div>
                `;
            }).join('')}
        `;

        chatBody.scrollTop = chatBody.scrollHeight;
    },

    async sendSimulatorTeacherMessage() {
        const input = document.getElementById('sim-input-message');
        const text = input.value.trim();
        if (!text) return;

        input.value = '';

        try {
            const res = await fetch('/api/whatsapp/simulate-incoming', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    school_id: this.state.activeSchoolId,
                    message: text
                })
            });
            const data = await res.json();
            
            // Reload chat to show bot response immediately
            this.loadSimulatorChat(this.state.activeSchoolId);
            this.fetchDashboardStats();
            this.fetchTickets();

            if (data.ticket_created) {
                this.showToast(`Support Ticket #${data.ticket_created.code} Auto-Created!`, 'error');
            }
        } catch (err) {
            this.showToast('Failed to send simulator message', 'error');
        }
    },

    async sendManualOperatorMessage() {
        const input = document.getElementById('input-manual-operator-msg');
        const text = input.value.trim();
        if (!text) return;

        input.value = '';

        try {
            const res = await fetch('/api/whatsapp/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    school_id: this.state.activeSchoolId,
                    message: text
                })
            });
            const data = await res.json();
            this.showToast('Manual message dispatched to teacher WhatsApp!', 'success');
            this.loadSimulatorChat(this.state.activeSchoolId);
        } catch (err) {
            this.showToast('Failed to dispatch message', 'error');
        }
    },

    // ==================== CURRICULUM & SUPPORT TICKETS ====================

    async fetchCurriculum() {
        try {
            const res = await fetch('/api/curriculum');
            const data = await res.json();
            this.state.curriculumList = data.modules;

            const grid = document.getElementById('curriculum-grid');
            if (!grid) return;

            grid.innerHTML = data.modules.map(m => `
                <div class="curriculum-card">
                    <div class="curr-badge-row">
                        <span class="curr-type-badge">${m.module_type}</span>
                        <span class="badge-neutral">${m.grade_range}</span>
                    </div>
                    <div class="curr-title">${m.title}</div>
                    <div class="curr-concept">💡 Concept: ${m.key_concept}</div>
                    <div class="curr-desc">${m.description}</div>
                    <button class="btn btn-sm btn-secondary" onclick="app.testCurriculumInSimulator('${m.title}')" style="margin-top:auto;">
                        <i data-lucide="share-2"></i> Recommend in Simulator
                    </button>
                </div>
            `).join('');

            lucide.createIcons();
        } catch (err) {
            console.error("Error fetching curriculum:", err);
        }
    },

    testCurriculumInSimulator(title) {
        this.switchTab('simulator');
        document.getElementById('sim-input-message').value = `Can you guide me on how to run ${title} with my students?`;
        this.sendSimulatorTeacherMessage();
    },

    async fetchTickets(status = 'all') {
        try {
            const res = await fetch(`/api/tickets?status=${status}`);
            const data = await res.json();
            this.state.ticketsList = data.tickets;

            const list = document.getElementById('tickets-queue-list');
            if (!list) return;

            if (data.tickets.length === 0) {
                list.innerHTML = `<div class="text-center text-muted" style="padding:24px;">No tickets matching filter.</div>`;
                return;
            }

            list.innerHTML = data.tickets.map(t => {
                const isUrgent = t.priority === 'urgent' || t.priority === 'high';
                const badgeClass = isUrgent ? 'badge-offline' : 'badge-nudge';

                return `
                    <div class="ticket-item">
                        <div class="ticket-header">
                            <span class="ticket-code">${t.ticket_code}</span>
                            <span class="${badgeClass}">${t.priority.toUpperCase()}</span>
                        </div>
                        <div class="ticket-title">${t.title}</div>
                        <div class="ticket-desc">${t.description}</div>
                        <div class="ticket-footer">
                            <span>School: <strong>${t.school_name}</strong> (${t.district})</span>
                            <div style="display:flex;gap:6px;align-items:center;">
                                <span>Status: <strong>${t.status.toUpperCase()}</strong></span>
                                ${t.status !== 'resolved' ? `
                                    <button class="btn btn-sm btn-secondary" onclick="app.resolveTicket(${t.id})" style="padding:2px 8px;font-size:0.7rem;">
                                        Mark Resolved
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            lucide.createIcons();
        } catch (err) {
            console.error("Error fetching tickets:", err);
        }
    },

    async resolveTicket(ticketId) {
        try {
            const res = await fetch(`/api/tickets/${ticketId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'resolved' })
            });
            const data = await res.json();
            if (data.success) {
                this.showToast(`Ticket #${ticketId} marked as resolved!`, 'success');
                this.fetchTickets();
            }
        } catch (err) {
            this.showToast('Failed to resolve ticket', 'error');
        }
    },

    // ==================== SCHOOL DETAIL DRAWER ====================

    async openSchoolDrawer(schoolId) {
        try {
            const res = await fetch(`/api/schools/${schoolId}`);
            const data = await res.json();
            const s = data.school;

            document.getElementById('drawer-school-name').innerText = s.name;
            document.getElementById('drawer-school-code').innerText = `${s.school_code} • Device: ${s.device_id}`;

            const content = document.getElementById('drawer-content');
            content.innerHTML = `
                <div class="drawer-section">
                    <h4>Overview & Location</h4>
                    <p><strong>District:</strong> ${s.district}, ${s.state}</p>
                    <p><strong>Students Reached:</strong> ${s.students_count} Active Learners</p>
                    <p><strong>Primary Contact:</strong> ${s.contact_name} (${s.contact_role}) - ${s.phone_number}</p>
                    <p><strong>Current Allocation:</strong> ${this.getBucketBadge(s.current_bucket)}</p>
                </div>

                <div class="drawer-section">
                    <h4>Weekly Telemetry</h4>
                    <p><strong>Weekly Usage:</strong> ${s.weekly_usage_hours} hours (${s.smart_class_sessions} sessions)</p>
                    <p><strong>Last Sync Timestamp:</strong> ${s.last_synced_at} (${this.formatTimeAgo(s.last_synced_at)})</p>
                    <div style="margin-top:8px;">
                        <strong>Subject Distribution:</strong>
                        <div style="display:flex;gap:8px;margin-top:4px;flex-wrap:wrap;">
                            ${Object.entries(s.subjects || {}).map(([k, v]) => `<span class="badge-neutral">${k}: ${v}</span>`).join('')}
                        </div>
                    </div>
                </div>

                <div class="drawer-section">
                    <h4>Recent Telemetry Pings</h4>
                    <div class="table-responsive small-table">
                        <table class="data-table">
                            <thead>
                                <tr><th>Sync Time</th><th>Hours</th><th>Health</th></tr>
                            </thead>
                            <tbody>
                                ${(data.telemetry_logs || []).slice(0, 4).map(t => `
                                    <tr>
                                        <td>${new Date(t.synced_at).toLocaleString()}</td>
                                        <td>${t.usage_hours}h</td>
                                        <td><span class="badge-green">${t.system_health}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="margin-top:24px;display:flex;gap:12px;">
                    <button class="btn btn-primary btn-block" onclick="app.closeDrawer();app.openSimulatorForSchool(${s.id});">
                        <i data-lucide="message-square"></i> Open in WhatsApp Simulator
                    </button>
                </div>
            `;

            document.getElementById('drawer-backdrop').classList.add('active');
            lucide.createIcons();
        } catch (err) {
            console.error("Error opening drawer:", err);
        }
    },

    closeDrawer() {
        document.getElementById('drawer-backdrop').classList.remove('active');
    },

    // ==================== WEBSOCKET REAL-TIME FEED ====================

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;

        this.state.ws = new WebSocket(wsUrl);

        this.state.ws.onopen = () => {
            console.log("WebSocket connected live.");
            document.getElementById('ws-status-text').innerText = "Connected Live";
        };

        this.state.ws.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                console.log("[WS Event Received]:", payload);

                if (payload.event === 'teacher_interaction') {
                    if (this.state.activeSchoolId === payload.data.school_id) {
                        this.loadSimulatorChat(payload.data.school_id);
                    }
                    this.fetchDashboardStats();
                } else if (payload.event === 'automation_completed') {
                    this.fetchDashboardStats();
                    this.fetchSchools(this.state.currentPage);
                } else if (payload.event === 'ticket_updated') {
                    this.fetchTickets();
                }
            } catch (e) {
                console.error("WebSocket message parsing error:", e);
            }
        };

        this.state.ws.onclose = () => {
            document.getElementById('ws-status-text').innerText = "Reconnecting...";
            setTimeout(() => this.initWebSocket(), 3000);
        };
    },

    // ==================== UTILITIES ====================

    getBucketBadge(bucket) {
        if (bucket === 'doing_great') return '<span class="badge-great">🌟 Doing Great</span>';
        if (bucket === 'needs_nudge') return '<span class="badge-nudge">👋 Needs a Nudge</span>';
        return '<span class="badge-offline">⚠️ Device Offline</span>';
    },

    formatBucketName(bucket) {
        if (bucket === 'doing_great') return 'Doing Great';
        if (bucket === 'needs_nudge') return 'Needs a Nudge';
        return 'Device Offline';
    },

    formatTimeAgo(isoString) {
        if (!isoString) return 'Never';
        try {
            const dtStr = isoString.replace('Z', '');
            const dt = new Date(dtStr);
            const now = new Date();
            const diffMs = now - dt;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffDays = Math.floor(diffHours / 24);

            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return `${diffHours} hrs ago`;
            if (diffDays === 1) return 'Yesterday';
            return `${diffDays} days ago`;
        } catch (e) {
            return isoString;
        }
    },

    formatMessageText(text) {
        if (!text) return '';
        return text.replace(/\n/g, '<br>');
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    },

    debounce(fn, delay) {
        let timer = null;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }
};

// Start application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
