// CSRF Token Extractor
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Toast Notification System
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '❌';
  if (type === 'warning') icon = '⚠️';

  toast.innerHTML = `<span>${icon}</span> <div>${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal Helpers
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('active');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('active');
}

// Close modal when clicking on overlay background
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});

// ----------------------------------------------------
// AJAX LIVE CLASS FUNCTIONS
// ----------------------------------------------------

async function startLiveClass(classId, btn) {
  if (!confirm("Are you ready to start this class? Started time will be recorded.")) return;
  
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="pulse-dot"></span> Starting...`;

  try {
    const response = await fetch(`/classes/${classId}/ajax/start/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();
    if (data.success) {
      showToast(data.message, 'success');
      
      // Update badge if exists
      const badge = document.getElementById(`status-badge-${classId}`);
      if (badge) {
        badge.outerHTML = `<span id="status-badge-${classId}" class="pulse-badge"><span class="pulse-dot"></span> Live Now</span>`;
      }

      // Update started time display
      const timeEl = document.getElementById(`time-started-${classId}`);
      if (timeEl) timeEl.textContent = data.actual_start_time;

      // Replace start button with end button
      btn.outerHTML = `
        <button class="btn btn-danger btn-sm" onclick="endLiveClass(${classId}, this)">
          🛑 End Class
        </button>
      `;
    } else {
      showToast(data.error || 'Failed to start class.', 'error');
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  } catch (err) {
    showToast('Network error while starting class.', 'error');
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

async function endLiveClass(classId, btn) {
  if (!confirm("Are you sure you want to end this class? Ended time and duration will be logged.")) return;

  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `Ending...`;

  try {
    const response = await fetch(`/classes/${classId}/ajax/end/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();
    if (data.success) {
      showToast(data.message, 'success');

      // Update badge
      const badge = document.getElementById(`status-badge-${classId}`);
      if (badge) {
        badge.outerHTML = `<span id="status-badge-${classId}" class="badge-completed">Completed</span>`;
      }

      // Update ended time display
      const timeEl = document.getElementById(`time-ended-${classId}`);
      if (timeEl) timeEl.textContent = data.actual_end_time;

      btn.outerHTML = `<span class="badge-completed">Concluded (${data.duration_minutes || 0}m)</span>`;
    } else {
      showToast(data.error || 'Failed to end class.', 'error');
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  } catch (err) {
    showToast('Network error while ending class.', 'error');
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// Student Joins Class & Attendance Recorded
async function joinClassWithAttendance(classId, meetUrl, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `Registering Attendance...`;
  }

  try {
    const response = await fetch(`/classes/${classId}/ajax/join/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();
    if (data.success) {
      showToast(data.message, 'success');

      // Open Google Meet in new tab immediately
      window.open(data.meet_link || meetUrl, '_blank');

      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `✅ Attended (Rejoin Meet)`;
        btn.classList.remove('btn-meet');
        btn.classList.add('btn-outline');
      }

      const attStatus = document.getElementById(`att-status-${classId}`);
      if (attStatus) {
        attStatus.innerHTML = `<span class="pulse-badge" style="background: rgba(16,185,129,0.2);">Attended at ${data.joined_at}</span>`;
      }
    } else {
      showToast(data.error || 'Could not register attendance.', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `🎥 Join Class (Google Meet)`;
      }
    }
  } catch (err) {
    showToast('Network error registering attendance.', 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `🎥 Join Class (Google Meet)`;
    }
  }
}

// ----------------------------------------------------
// AJAX EXAM MARKS AUTO-SAVE
// ----------------------------------------------------

async function autoSaveMark(examId, studentId) {
  const row = document.getElementById(`student-row-${studentId}`);
  if (!row) return;

  const marksInput = row.querySelector('.input-marks');
  const absentCheckbox = row.querySelector('.input-absent');
  const remarksInput = row.querySelector('.input-remarks');
  const statusPill = row.querySelector('.pill-status');
  const percentEl = row.querySelector('.text-percentage');
  const saveIndicator = row.querySelector('.save-indicator');

  if (saveIndicator) saveIndicator.textContent = '⏳';

  const payload = {
    student_id: studentId,
    marks_obtained: absentCheckbox.checked ? null : marksInput.value,
    is_absent: absentCheckbox.checked,
    remarks: remarksInput.value
  };

  try {
    const response = await fetch(`/exams/${examId}/ajax/save-mark/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (data.success) {
      if (saveIndicator) saveIndicator.textContent = '✅';
      marksInput.classList.add('saved');

      setTimeout(() => {
        if (saveIndicator) saveIndicator.textContent = '';
      }, 2500);

      // Update UI row elements
      if (data.is_absent) {
        marksInput.disabled = true;
        if (statusPill) {
          statusPill.textContent = 'Absent';
          statusPill.className = 'pill-status badge-scheduled';
        }
        if (percentEl) percentEl.textContent = '0%';
      } else {
        marksInput.disabled = false;
        if (data.marks_obtained !== null) {
          if (statusPill) {
            statusPill.textContent = data.is_passed ? 'Passed' : 'Failed';
            statusPill.className = `pill-status ${data.is_passed ? 'pulse-badge' : 'badge-danger'}`;
            if (!data.is_passed) {
              statusPill.style.background = 'rgba(239, 68, 68, 0.2)';
              statusPill.style.color = '#f87171';
            }
          }
          if (percentEl) percentEl.textContent = `${data.percentage}%`;
        } else {
          if (statusPill) {
            statusPill.textContent = 'Pending';
            statusPill.className = 'pill-status badge-completed';
          }
          if (percentEl) percentEl.textContent = '-';
        }
      }

      // Update global exam stats on page
      const avgEl = document.getElementById('stat-exam-average');
      if (avgEl && data.exam_average !== undefined) avgEl.textContent = data.exam_average;

      const highEl = document.getElementById('stat-exam-highest');
      if (highEl && data.exam_highest !== undefined) highEl.textContent = data.exam_highest;

    } else {
      if (saveIndicator) saveIndicator.textContent = '❌';
      showToast(data.error || 'Error saving mark.', 'error');
    }
  } catch (err) {
    if (saveIndicator) saveIndicator.textContent = '❌';
    showToast('Failed to save mark due to connection error.', 'error');
  }
}

// Live Class Real-Time Duration Updater
function updateLiveClassDurations() {
  document.querySelectorAll('.live-timer-badge[data-start]').forEach(badge => {
    const startIso = badge.getAttribute('data-start');
    if (!startIso) return;
    const startTime = new Date(startIso);
    const now = new Date();
    const diffMs = now - startTime;
    if (diffMs > 0) {
      const totalSec = Math.floor(diffMs / 1000);
      const mins = Math.floor(totalSec / 60);
      const secs = totalSec % 60;
      if (mins < 60) {
        badge.textContent = `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
      } else {
        const hrs = Math.floor(mins / 60);
        const remMins = mins % 60;
        badge.textContent = `${hrs}h ${remMins}m`;
      }
    }
  });
}

setInterval(updateLiveClassDurations, 1000);
document.addEventListener('DOMContentLoaded', updateLiveClassDurations);
