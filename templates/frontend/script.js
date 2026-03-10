// ============================================
// 🚦 TRAFFIC MANAGEMENT SYSTEM - FRONTEND
// ============================================

let systemStartTime = Date.now();
let lastData = null;
let vehicleHistory = {};

// --- SECTION NAVIGATION ---
function showSection(id) {
    document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    
    document.getElementById(id).classList.add('active');
    
    const btns = document.querySelectorAll('.nav-btn');
    if(id === 'dashboard') btns[0].classList.add('active');
    if(id === 'traffic') btns[1].classList.add('active');
    if(id === 'controls') btns[2].classList.add('active');
    if(id === 'analytics') btns[3].classList.add('active');
}

// --- BACKEND API CALLS ---
async function toggleService(laneId) {
    try {
        const res = await fetch(`/toggle_service_mode/${laneId}`, { method: 'POST' });
        if(res.ok) {
            console.log(`✅ Service mode toggled for Lane ${laneId}`);
        }
    } catch(e) {
        console.error('❌ Service toggle error:', e);
    }
}

async function toggleAcc() {
    try {
        const res = await fetch('/toggle_accident', { method: 'POST' });
        if(res.ok) {
            console.log('✅ Accident mode toggled');
        }
    } catch(e) {
        console.error('❌ Accident toggle error:', e);
    }
}

function updateServiceUI(idx, isActive) {
    const btn = document.getElementById(`svc-btn-${idx}`);
    const btn2 = document.getElementById(`svc-${idx}`);
    
    if(isActive) {
        if(btn) {
            btn.classList.add('active');
            btn.innerText = `Lane ${idx+1}: SERVICE MODE ⚡`;
        }
        if(btn2) {
            btn2.classList.add('active');
            btn2.innerText = `Service: ON ⚡`;
        }
    } else {
        if(btn) {
            btn.classList.remove('active');
            btn.innerText = `Lane ${idx+1}: Normal`;
        }
        if(btn2) {
            btn2.classList.remove('active');
            btn2.innerText = `Service: OFF`;
        }
    }
}

// --- REAL-TIME DATA SYNC ---
async function updateDashboard() {
    try {
        const res = await fetch('/get_stats');
        if(!res.ok) throw new Error('Stats fetch failed');
        
        const data = await res.json();
        lastData = data;

        let totalVehicles = 0;
        let totalCars = 0, totalBikes = 0, totalBuses = 0, totalTrucks = 0;
        let totalPCU = 0;
        let totalLanes = data.lanes.length;
        let tableHtml = "";
        let bestLane = 0, bestPCU = 0;
        let worstLane = 0, worstPCU = 999;

        data.lanes.forEach((lane, idx) => {
            const counts = lane.counts || {};
            const cars = counts.car || 0;
            const bikes = counts.motorbike || 0;
            const buses = counts.bus || 0;
            const trucks = counts.truck || 0;
            const pcu = lane.pcu || 0;
            
            totalCars += cars;
            totalBikes += bikes;
            totalBuses += buses;
            totalTrucks += trucks;
            totalVehicles += cars + bikes + buses + trucks;
            totalPCU += pcu;

            // Track best/worst lanes
            if(pcu > bestPCU) { bestPCU = pcu; bestLane = idx; }
            if(pcu < worstPCU && cars + bikes + buses + trucks > 0) { worstPCU = pcu; worstLane = idx; }

            // Vehicle count
            const vehicleCount = cars + bikes + buses + trucks;
            
            // Signal styling
            const statusColor = lane.signal === "GREEN" ? "#2a9d8f" : "#e76f51";
            const signalText = lane.signal === "GREEN" ? `GO (${lane.timer}s)` : `STOP`;
            
            tableHtml += `
                <tr>
                    <td style="font-weight: bold;">Lane ${idx+1}</td>
                    <td style="color:${statusColor}; font-weight:bold;">${signalText}</td>
                    <td>${pcu.toFixed(1)}</td>
                    <td>${vehicleCount}</td>
                    <td>${lane.timer || 0}s</td>
                    <td>${lane.is_service ? '⚡ SERVICE' : 'NORMAL'}</td>
                </tr>
            `;

            // Update video badges
            const badge = document.getElementById(`badge-${idx}`);
            const box = document.getElementById(`box-${idx}`);
            const info = document.getElementById(`info-${idx}`);
            
            if(lane.signal === "GREEN" && !data.accident_mode) {
                badge.className = "status-badge badge-green";
                badge.innerText = `🟢 GO (${lane.timer}s)`;
                if(box) box.style.borderColor = "#2a9d8f";
            } else {
                badge.className = "status-badge badge-red";
                badge.innerText = `🔴 STOP`;
                if(box) box.style.borderColor = "#333";
            }
            
            if(info) info.innerText = `${vehicleCount} vehicles • PCU: ${pcu.toFixed(1)}`;

            // Update service UI
            updateServiceUI(idx, lane.is_service);
        });

        // Update dashboard cards
        document.getElementById('total-vehicles').innerText = totalVehicles;
        document.getElementById('avg-pcu').innerText = (totalPCU / totalLanes).toFixed(1);
        document.getElementById('active-lane').innerText = `LANE ${data.priority_lane + 1}`;
        document.getElementById('stats-table').innerHTML = tableHtml;

        // Update analytics
        document.getElementById('count-cars').innerText = totalCars;
        document.getElementById('count-bikes').innerText = totalBikes;
        document.getElementById('count-buses').innerText = totalBuses;
        document.getElementById('count-trucks').innerText = totalTrucks;
        document.getElementById('best-lane').innerText = `Lane ${bestLane + 1}`;
        document.getElementById('worst-lane').innerText = worstPCU === 999 ? '--' : `Lane ${worstLane + 1}`;
        document.getElementById('sys-load').innerText = `${((totalPCU / 200) * 100).toFixed(0)}%`;

        // Update accident button
        const accBtn = document.getElementById('btn-acc');
        const sysStatus = document.getElementById('sys-status');
        
        if(data.accident_mode) {
            accBtn.classList.add('active');
            accBtn.innerText = "⚠️ SYSTEM HALTED - CLICK TO RESUME";
            sysStatus.innerText = "🚨 EMERGENCY STOP";
            sysStatus.style.color = "#e76f51";
        } else {
            accBtn.classList.remove('active');
            accBtn.innerText = "🚨 TRIGGER EMERGENCY STOP";
            sysStatus.innerText = "✅ ONLINE";
            sysStatus.style.color = "#2a9d8f";
        }

        // Update uptime
        const uptime = Math.floor((Date.now() - systemStartTime) / 1000);
        const hours = Math.floor(uptime / 3600);
        const mins = Math.floor((uptime % 3600) / 60);
        document.getElementById('sys-uptime').innerText = `Uptime: ${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;

    } catch(e) {
        console.error('❌ Dashboard update error:', e);
        document.getElementById('sys-status').innerText = '⚠️ OFFLINE';
        document.getElementById('sys-status').style.color = '#aaa';
    }
}

// --- CLOCK DISPLAY ---
function updateClock() {
    const now = new Date();
    document.getElementById('time-display').innerText = now.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
}

// --- START AUTO-UPDATE ---
setInterval(updateDashboard, 800);
setInterval(updateClock, 1000);

// Initial load
updateDashboard();
updateClock();


console.log('✅ Frontend loaded successfully!');

