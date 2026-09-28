const subjects = [
  { name: 'Data Structures',    pct: 72, color: '#534AB7', hrs: 14.4, target: 20 },
  { name: 'Computer Networks',  pct: 55, color: '#1D9E75', hrs: 8.25, target: 15 },
  { name: 'DBMS',               pct: 40, color: '#EF9F27', hrs: 6,    target: 15 },
  { name: 'Operating Systems',  pct: 85, color: '#378ADD', hrs: 17,   target: 20 },
];

const tasks = [
  { topic: 'Binary Trees revision',      subject: 'Data Structures',   dur: '45 min', done: true  },
  { topic: 'TCP/IP model',               subject: 'Computer Networks',  dur: '30 min', done: true  },
  { topic: 'Process scheduling',         subject: 'Operating Systems',  dur: '40 min', done: true  },
  { topic: 'Normalization 1NF\u20133NF', subject: 'DBMS',              dur: '60 min', done: false },
  { topic: 'Graph BFS and DFS',          subject: 'Data Structures',   dur: '50 min', done: false },
];

const streakDays = [
  { lbl: 'M', date: '27', status: 'done'  },
  { lbl: 'T', date: '28', status: 'done'  },
  { lbl: 'W', date: '29', status: 'done'  },
  { lbl: 'T', date: '30', status: 'done'  },
  { lbl: 'F', date: '1',  status: 'done'  },
  { lbl: 'S', date: '2',  status: 'done'  },
  { lbl: 'S', date: 'Today', status: 'today' },
];

const deadlines = [
  { name: 'DBMS unit test',       date: 'May 7',  days: '4 days',  urgency: 'red'    },
  { name: 'Networks assignment',   date: 'May 10', days: '7 days',  urgency: 'amber'  },
  { name: 'DSA practical exam',    date: 'May 15', days: '12 days', urgency: 'green'  },
];

const recentNotes = [
  { title: 'Binary tree traversals',  meta: 'Data Structures \u00b7 May 2' },
  { title: 'OSI vs TCP/IP model',     meta: 'Networks \u00b7 May 1'        },
  { title: 'Normal forms 1NF\u2013BCNF', meta: 'DBMS \u00b7 Apr 30'       },
];

const weeklyHours  = [2, 3, 1.5, 3.5, 2, 1, 1.5];
const weekDayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'sun']
function setGreeting() {
  const hour = new Date().getHours();
  let g = 'Good morning';
  if (hour >= 12 && hour < 17) g = 'Good afternoon';
  else if (hour >= 17) g = 'Good evening';
  const el = document.getElementById('greeting');
  if (el) el.textContent = g + ', Rahul';
}

function renderSubjectProgress() {
  const container = document.getElementById('subject-progress');
  if (!container) return;

  container.innerHTML = subjects.map(s => `
    <div class="subj-row">
      <div class="subj-dot" style="background:${s.color};"></div>
      <div class="subj-name">${s.name}</div>
      <div class="bar-bg">
        <div class="bar-fill" style="width:${s.pct}%; background:${s.color};"></div>
      </div>
      <div class="subj-pct">${s.pct}%</div>
    </div>
  `).join('');
}

function renderTasks() {
  const container = document.getElementById('task-list');
  if (!container) return;

  container.innerHTML = tasks.map((t, i) => `
    <div class="task-item">
      <div class="chk ${t.done ? 'done' : ''}" onclick="toggleTask(${i})" title="Toggle task"></div>
      <div class="task-info">
        <div class="task-name ${t.done ? 'done' : ''}">${t.topic}</div>
        <div class="task-sub">${t.subject}</div>
      </div>
      <div class="task-dur">${t.dur}</div>
    </div>
  `).join('');

  updateTaskStats();
}

function toggleTask(index) {
  tasks[index].done = !tasks[index].done;
  renderTasks();
}

function updateTaskStats() {
  const done    = tasks.filter(t => t.done).length;
  const total   = tasks.length;
  const el      = document.getElementById('stat-tasks');
  if (el) el.textContent = done + ' / ' + total;
}

function renderStreak() {
  const container = document.getElementById('streak-row');
  if (!container) return;

  container.innerHTML = streakDays.map(day => `
    <div class="sc-wrap">
      <div class="sc sc-${day.status}">${day.lbl}</div>
      <div class="sc-lbl">${day.date}</div>
    </div>
  `).join('');
}

function renderDeadlines() {
  const container = document.getElementById('deadlines-list');
  if (!container) return;

  container.innerHTML = deadlines.map(d => `
    <div class="deadline-row">
      <div>
        <div class="deadline-name">${d.name}</div>
        <div class="deadline-date">${d.date}</div>
      </div>
      <span class="tag tag-${d.urgency}">${d.days}</span>
    </div>
  `).join('');
}

function renderNotes() {
  const container = document.getElementById('notes-list');
  if (!container) return;

  container.innerHTML = recentNotes.map(n => `
    <div class="note-row">
      <div>
        <div class="note-title">${n.title}</div>
        <div class="note-meta">${n.meta}</div>
      </div>
    </div>
  `).join('');
}

function renderWeekChart() {
  const canvas = document.getElementById('weekChart');
  if (!canvas) return;

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: weekDayNames,
      datasets: [{
        label: 'Hours studied',
        data: weeklyHours,
        backgroundColor: '#534AB7',
        borderColor: '#3C3489',
        borderWidth: 1,
        borderRadius: 5,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ' ' + ctx.parsed.y + ' hrs'
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 5,
          ticks: {
            stepSize: 1,
            color: '#9CA3AF',
            font: { size: 11 },
            callback: val => val + 'h'
          },
          grid: { color: 'rgba(0,0,0,0.05)' }
        },
        x: {
          ticks: { color: '#9CA3AF', font: { size: 11 } },
          grid: { display: false }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {
  setGreeting();
  renderSubjectProgress();
  renderTasks();
  renderStreak();
  renderDeadlines();
  renderNotes();
  renderWeekChart();
});
