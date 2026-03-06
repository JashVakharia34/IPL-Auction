/* ═══════════════════════════════════════════════
   IPL AUCTION 2026 — Client-Side Logic
   ═══════════════════════════════════════════════ */

let socket;
let config = {};
let auctionState = {};
let activeSet = 1;

const ROLE_ICONS = {
    BAT: '🏏',
    BOWL: '🎯',
    AR: '⭐',
    WK: '🧤',
};

const ROLE_LABELS = {
    BAT: 'Batsman',
    BOWL: 'Bowler',
    AR: 'All-Rounder',
    WK: 'Wicketkeeper',
};

function initAuction(cfg) {
    config = cfg;

    // Always load initial state first before hooking up sockets
    loadAuctionData();

    try {
        socket = io();
        setupSocketEvents();
    } catch (err) {
        console.error("Socket.io failed to initialize:", err);
        showToast("Warning: Live connection failed. Please disable ad-blockers for Socket.io.");
    }

    // Admin buttons
    if (config.isAdmin) {
        const nextBtn = document.getElementById('nextPlayerBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (socket) socket.emit('next_player', { room_code: config.roomCode });
                nextBtn.disabled = true;
                setTimeout(() => nextBtn.disabled = false, 2000);
            });
        }
    } else {
        // Team bid button
        const bidBtn = document.getElementById('bidBtn');
        if (bidBtn) {
            bidBtn.addEventListener('click', () => {
                if (socket) socket.emit('place_bid', {
                    room_code: config.roomCode,
                    team_id: config.teamId,
                });
                bidBtn.disabled = true;
                setTimeout(() => bidBtn.disabled = false, 1000);
            });
        }
    }

    // Set tabs
    document.querySelectorAll('.set-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.set-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            activeSet = parseInt(tab.dataset.set);
            renderPlayerPool();
        });
    });
}


function setupSocketEvents() {
    socket.on('connect', () => {
        socket.emit('join_auction', {
            room_code: config.roomCode,
            team_id: config.teamId || null,
            is_admin: config.isAdmin,
        });
    });

    socket.on('joined', (data) => {
        console.log('Joined auction:', data);
    });

    socket.on('team_status', (data) => {
        if (auctionState.teams) {
            const team = auctionState.teams.find(t => t.id === data.team_id);
            if (team) {
                team.is_connected = data.is_connected;
                renderTeams();
            }
        }
    });

    socket.on('new_player', (data) => {
        showActiveStage();
        auctionState.current_player = data.player;
        auctionState.status = 'live';
        renderCurrentPlayer();
        renderPlayerPool();
        updateStatus('live');
        clearBidFeed();
    });

    socket.on('bid_update', (data) => {
        auctionState.current_player.current_bid = data.amount;
        auctionState.current_player.current_bid_formatted = data.amount_formatted;
        auctionState.current_player.current_bid_team_id = data.team_id;
        auctionState.current_player.current_bid_team_name = data.team_name;
        auctionState.current_player.next_bid = data.next_bid;
        auctionState.current_player.next_bid_formatted = data.next_bid_formatted;

        updateBidDisplay();
        addBidToFeed(data);
        updateBidButton();
    });

    socket.on('timer_tick', (data) => {
        updateTimer(data.seconds_left);
    });

    socket.on('player_sold', (data) => {
        showSoldOverlay(data, true);
        // Update local state
        if (auctionState.teams) {
            const team = auctionState.teams.find(t => t.id === data.team.id);
            if (team) {
                Object.assign(team, data.team);
            }
        }
        if (auctionState.players) {
            const player = auctionState.players.find(p => p.id === data.player.id);
            if (player) {
                Object.assign(player, data.player);
            }
        }
        renderTeams();
        renderPlayerPool();
        updateMyTeamInfo();
    });

    socket.on('player_unsold', (data) => {
        showSoldOverlay(data, false);
        if (auctionState.players) {
            const player = auctionState.players.find(p => p.id === data.player.id);
            if (player) {
                Object.assign(player, data.player);
            }
        }
        renderPlayerPool();
    });

    socket.on('auction_paused', () => {
        auctionState.status = 'paused';
        updateStatus('paused');
        if (config.isAdmin) {
            document.getElementById('pauseBtn').style.display = 'none';
            document.getElementById('resumeBtn').style.display = '';
        }
    });

    socket.on('auction_resumed', (data) => {
        auctionState.status = 'live';
        updateStatus('live');
        if (config.isAdmin) {
            document.getElementById('pauseBtn').style.display = '';
            document.getElementById('resumeBtn').style.display = 'none';
        }
    });

    socket.on('auction_complete', () => {
        auctionState.status = 'completed';
        updateStatus('completed');
        document.getElementById('stageActive').style.display = 'none';
        document.getElementById('stageWaiting').style.display = 'none';
        document.getElementById('soldOverlay').style.display = 'none';
        document.getElementById('stageComplete').style.display = 'flex';
    });

    socket.on('error', (data) => {
        showToast(data.message);
    });

    // Admin controls
    if (config.isAdmin) {
        setTimeout(() => {
            const pauseBtn = document.getElementById('pauseBtn');
            const resumeBtn = document.getElementById('resumeBtn');
            if (pauseBtn) {
                pauseBtn.addEventListener('click', () => {
                    socket.emit('pause_auction', { room_code: config.roomCode });
                });
            }
            if (resumeBtn) {
                resumeBtn.addEventListener('click', () => {
                    socket.emit('resume_auction', { room_code: config.roomCode });
                });
            }
        }, 100);
    }
}


async function loadAuctionData() {
    try {
        const res = await fetch(`/api/auction/${config.roomCode}`);
        const data = await res.json();
        auctionState = data;
        renderTeams();
        renderPlayerPool();
        updateMyTeamInfo();

        if (data.status === 'live' && data.current_player) {
            showActiveStage();
            renderCurrentPlayer();
            updateTimer(data.seconds_left);
        } else if (data.status === 'completed') {
            document.getElementById('stageWaiting').style.display = 'none';
            document.getElementById('stageComplete').style.display = 'flex';
        }

        updateStatus(data.status);
    } catch (err) {
        console.error('Failed to load auction data:', err);
    }
}


function renderTeams() {
    const container = document.getElementById('teamsList');
    if (!container || !auctionState.teams) return;

    container.innerHTML = auctionState.teams.map(team => `
        <div class="team-card-mini" style="--team-color: ${team.color}">
            <div class="team-mini-header">
                <span class="team-mini-name">
                    ${team.logo_emoji} ${team.short_name}
                    <span class="team-mini-connection ${team.is_connected ? 'connected' : ''}"></span>
                </span>
                <span class="team-mini-purse">${team.purse_formatted}</span>
            </div>
            <div class="team-mini-squad">${team.squad_count}/18 players</div>
            <div class="team-mini-players">
                ${team.squad.map(p => `<span class="squad-tag">${p.name.split(' ').pop()}</span>`).join('')}
            </div>
        </div>
    `).join('');
}


function renderPlayerPool() {
    const container = document.getElementById('playersList');
    if (!container || !auctionState.players) return;

    const filtered = auctionState.players.filter(p => p.set_number === activeSet);

    container.innerHTML = filtered.map(p => {
        let cls = 'player-mini';
        if (p.is_sold) cls += ' sold';
        else if (p.is_unsold) cls += ' unsold';
        if (auctionState.current_player && p.id === auctionState.current_player.id) cls += ' current';

        const flag = p.nationality === 'OVERSEAS' ? '<span class="overseas-flag">🌍</span>' : '';
        const priceStr = p.is_sold ? (p.sold_price_formatted || '') : (p.base_price_formatted || '');
        const team = p.is_sold && p.team_id ? auctionState.teams?.find(t => t.id === p.team_id) : null;
        const soldTo = team ? ` → ${team.short_name}` : '';

        return `
            <div class="${cls}">
                <span class="player-mini-name">
                    ${flag} ${p.name}
                    <span class="player-mini-role">${p.role}</span>
                </span>
                <span class="player-mini-price">${priceStr}${soldTo}</span>
            </div>
        `;
    }).join('');
}


function renderCurrentPlayer() {
    const p = auctionState.current_player;
    if (!p) return;

    document.getElementById('playerName').textContent = p.name;
    document.getElementById('playerRole').textContent = ROLE_LABELS[p.role] || p.role;
    document.getElementById('playerNationality').textContent = p.nationality;
    document.getElementById('playerNationality').className = 'player-nationality' + (p.nationality === 'OVERSEAS' ? ' overseas' : '');
    document.getElementById('playerBasePrice').textContent = `Base: ${p.base_price_formatted}`;
    document.getElementById('playerSetBadge').textContent = `SET ${p.set_number}`;
    document.getElementById('roleIcon').textContent = ROLE_ICONS[p.role] || '🏏';

    // Render Dynamic Stats
    const statsGrid = document.getElementById('playerStatsGrid');
    if (statsGrid) {
        statsGrid.innerHTML = '';
        if (p.stats && Object.keys(p.stats).length > 0) {
            Object.entries(p.stats).forEach(([key, val]) => {
                statsGrid.innerHTML += `
                    <div class="stat-box">
                        <div class="stat-value">${val}</div>
                        <div class="stat-label">${key}</div>
                    </div>
                `;
            });
            statsGrid.style.display = 'grid';
        } else {
            statsGrid.style.display = 'none';
        }
    }

    updateBidDisplay();
    updateBidButton();
    updateTimer(60);
}


function updateBidDisplay() {
    const p = auctionState.current_player;
    if (!p) return;

    const amountEl = document.getElementById('currentBidAmount');
    const teamEl = document.getElementById('currentBidTeam');

    if (p.current_bid) {
        amountEl.textContent = p.current_bid_formatted;
        const team = auctionState.teams?.find(t => t.id === p.current_bid_team_id);
        if (team) {
            teamEl.textContent = team.name;
            teamEl.style.background = team.color;
            teamEl.style.color = 'white';
        } else {
            teamEl.textContent = p.current_bid_team_name || '';
        }
        // Trigger pop animation
        amountEl.style.animation = 'none';
        amountEl.offsetHeight; // reflow
        amountEl.style.animation = 'bidPop 0.3s ease-out';
    } else {
        amountEl.textContent = '—';
        teamEl.textContent = 'No bids yet';
        teamEl.style.background = 'transparent';
        teamEl.style.color = 'var(--text-muted)';
    }
}


function updateBidButton() {
    if (config.isAdmin) return;

    const btn = document.getElementById('bidBtn');
    const amountEl = document.getElementById('bidBtnAmount');
    if (!btn || !amountEl) return;

    const p = auctionState.current_player;
    if (!p) { btn.disabled = true; return; }

    // Disable if we already have the highest bid
    if (p.current_bid_team_id === config.teamId) {
        btn.disabled = true;
        amountEl.textContent = 'Highest Bidder!';
        return;
    }

    btn.disabled = false;
    amountEl.textContent = p.next_bid_formatted || p.base_price_formatted;
}


function updateTimer(seconds) {
    const textEl = document.getElementById('timerText');
    const progressEl = document.getElementById('timerProgress');
    if (!textEl || !progressEl) return;

    textEl.textContent = Math.max(0, seconds);

    // Update circular progress
    const circumference = 2 * Math.PI * 54; // r=54
    const offset = circumference * (1 - seconds / 60);
    progressEl.style.strokeDashoffset = offset;

    // Color transitions
    textEl.className = 'timer-text';
    progressEl.className = 'timer-progress';

    if (seconds <= 10) {
        textEl.classList.add('danger');
        progressEl.classList.add('danger');
    } else if (seconds <= 20) {
        textEl.classList.add('warning');
        progressEl.classList.add('warning');
    }
}


function showActiveStage() {
    document.getElementById('stageWaiting').style.display = 'none';
    document.getElementById('stageActive').style.display = 'flex';
    document.getElementById('soldOverlay').style.display = 'none';
    document.getElementById('stageComplete').style.display = 'none';
}


function showSoldOverlay(data, isSold) {
    const overlay = document.getElementById('soldOverlay');
    const label = document.getElementById('soldLabel');
    const playerEl = document.getElementById('soldPlayer');
    const details = document.getElementById('soldDetails');

    overlay.style.display = 'flex';

    if (isSold) {
        label.textContent = 'SOLD! 🔨';
        label.className = 'sold-label';
        playerEl.textContent = data.player.name;
        details.innerHTML = `
            <strong style="color: ${data.team.color}">${data.team.name}</strong><br>
            for <strong style="color: var(--accent-gold)">${data.sold_price_formatted}</strong>
        `;
    } else {
        label.textContent = 'UNSOLD ❌';
        label.className = 'sold-label unsold-label';
        playerEl.textContent = data.player.name;
        details.textContent = 'No bids received';
    }

    // Admin next player button
    const nextBtn = document.getElementById('nextAfterSold');
    if (nextBtn) {
        nextBtn.onclick = () => {
            overlay.style.display = 'none';
            socket.emit('next_player', { room_code: config.roomCode });
        };
    }

    // Auto-hide for non-admin after 3 seconds
    if (!config.isAdmin) {
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 3000);
    }
}


function addBidToFeed(data) {
    const feedList = document.getElementById('feedList');
    if (!feedList) return;

    const item = document.createElement('div');
    item.className = 'feed-item';
    item.innerHTML = `
        <span class="feed-team" style="background: ${data.team_color}">${data.team_name}</span>
        <span class="feed-amount">${data.amount_formatted}</span>
    `;
    feedList.insertBefore(item, feedList.firstChild);
}


function clearBidFeed() {
    const feedList = document.getElementById('feedList');
    if (feedList) feedList.innerHTML = '';
}


function updateStatus(status) {
    const badge = document.getElementById('statusBadge');
    if (!badge) return;
    badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    badge.className = 'status-badge ' + status;
}


function updateMyTeamInfo() {
    if (config.isAdmin || !config.teamId || !auctionState.teams) return;

    const team = auctionState.teams.find(t => t.id === config.teamId);
    if (!team) return;

    const teamBadge = document.getElementById('myTeamBadge');
    const purseBadge = document.getElementById('myPurseBadge');
    if (teamBadge) {
        teamBadge.textContent = `${team.logo_emoji} ${team.short_name}`;
        teamBadge.style.background = team.color;
    }
    if (purseBadge) {
        purseBadge.textContent = `💰 ${team.purse_formatted}`;
    }
}


function showToast(message) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
