// Main JavaScript for betting platform
// Handles Socket.IO events and form submissions on both admin and user pages

const socket = io();

// Elements for user page
const betForm = document.getElementById('betForm');
const betsEl = document.getElementById('bets');
const oddsEl = document.getElementById('odds');
const totalsEl = document.getElementById('totals');
const balanceEl = document.getElementById('balance');
const quickBtns = document.querySelectorAll('.quick-bet');
const confirmToggle = document.getElementById('confirmToggle');
const confirmModal = document.getElementById('confirmModal');
const confirmText = document.getElementById('confirmText');
const confirmBtn = document.getElementById('confirmBtn');
const linkBtn = document.getElementById('linkBtn');
const userId = document.body.dataset.userid;
const myBetsEl = document.getElementById('myBets');

// Elements for admin page
const openForm = document.getElementById('openForm');
const closeBtn = document.getElementById('closeBtn');
const resultForm = document.getElementById('resultForm');
const statusEl = document.getElementById('status');
const toastEl = document.getElementById('toast');
const depositForm = document.getElementById('depositForm');
const withdrawForm = document.getElementById('withdrawForm');
const streamForm = document.getElementById('streamForm');
const depList = document.getElementById('depList');
const wdList = document.getElementById('wdList');

function showToast(msg) {
  if (!toastEl) return;
  toastEl.querySelector('.toast-body').textContent = msg;
  const t = new bootstrap.Toast(toastEl);
  t.show();
}

function api(url, data, msg) {
  axios.post(url, data, {headers: {Authorization: `Bearer ${localStorage.getItem('ADMIN_TOKEN') || ''}`}})
    .then(() => msg && showToast(msg))
    .catch(() => alert('เกิดข้อผิดพลาด'));
}

// Socket events
socket.on('round_open', d => {
  if (statusEl) {
    statusEl.textContent = `เปิดรอบ ราคา แดง ${d.red_odds} / น้ำเงิน ${d.blue_odds}`;
  }
  if (oddsEl) {
    oddsEl.textContent = `ราคา แดง ${d.red_odds} / น้ำเงิน ${d.blue_odds}`;
  }
  if (betsEl) betsEl.innerHTML = '';
  if (d.totals) {
    totalsEl && (totalsEl.textContent = `ยอดแดง ${d.totals.red} / น้ำเงิน ${d.totals.blue}`);
  } else {
    totalsEl && (totalsEl.textContent = '');
  }
});

socket.on('round_close', () => {
  if (statusEl) statusEl.textContent = 'ปิดรอบ';
  if (oddsEl) oddsEl.textContent = 'ปิดรอบแล้ว';
});

socket.on('result_announced', d => {
  const winnerTxt = d.winner === 'red' ? 'แดง' : 'น้ำเงิน';
  if (statusEl) statusEl.textContent = `ผลผู้ชนะ: ${winnerTxt}`;
  if (!statusEl) alert(`ผู้ชนะ: ${winnerTxt}`);
});

socket.on('totals', t => {
  totalsEl && (totalsEl.textContent = `ยอดแดง ${t.red} / น้ำเงิน ${t.blue}`);
});

socket.on('new_bet', b => {
  if (betsEl) {
    const li = document.createElement('li');
    li.className = 'list-group-item';
    const sideTxt = b.side === 'red' ? 'แดง' : 'น้ำเงิน';
    li.textContent = `${b.user_id} เดิมพัน ${sideTxt} ${b.amount}`;
    betsEl.appendChild(li);
  }
  if (b.totals) {
    totalsEl && (totalsEl.textContent = `ยอดแดง ${b.totals.red} / น้ำเงิน ${b.totals.blue}`);
  }
  if (myBetsEl && String(b.user_id) === userId) {
    const li = document.createElement('li');
    li.className = 'list-group-item';
    const sideTxt = b.side === 'red' ? 'แดง' : 'น้ำเงิน';
    li.textContent = `${sideTxt} ${b.amount}`;
    myBetsEl.prepend(li);
    if (myBetsEl.children.length > 5) {
      myBetsEl.lastChild.remove();
    }
  }
});

socket.on('stream_update', d => {
  const video = document.getElementById('live_html5_api') || document.getElementById('live');
  if (video) {
    video.src = d.url;
  }
});

socket.on('wallet_update', b => {
  if (!balanceEl) return;
  if (String(b.user_id) === userId) {
    balanceEl.textContent = Number(b.balance).toFixed(2);
  }
});

socket.on('deposit_update', d => {
  alert('เงินเข้า: ' + d.amount + ' บาท');
});

// User bet form
if (betForm) {
  betForm.addEventListener('submit', e => {
    e.preventDefault();
    axios.post('/api/bet', {
      side: document.getElementById('side').value,
      amount: document.getElementById('amount').value
    }).then(r => console.log(r.data));
  });
}

function sendBet(side, amount) {
  axios.post('/api/bet', {side, amount})
    .catch(() => alert('เกิดข้อผิดพลาด'));
}

if (quickBtns.length) {
  quickBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const side = btn.dataset.side;
      const amount = btn.dataset.amount;
      if (confirmToggle && confirmToggle.checked && confirmModal) {
        confirmText.textContent = `${side === 'red' ? 'แดง' : 'น้ำเงิน'} ${amount} บาท`;
        const m = new bootstrap.Modal(confirmModal);
        m.show();
        confirmBtn.onclick = () => { m.hide(); sendBet(side, amount); };
      } else {
        sendBet(side, amount);
      }
    });
  });
}

if (linkBtn) {
  linkBtn.addEventListener('click', () => {
    axios.post('/api/link_token').then(r => {
      alert(`พิมพ์ link ${r.data.token} ใน LINE`);
    });
  });
}

if (depositForm) {
  depositForm.addEventListener('submit', e => {
    e.preventDefault();
    const formData = new FormData(depositForm);
    axios.post('/api/wallet/deposit_request', formData).then(() => alert('ส่งคำขอฝากแล้ว'));
  });
}

if (withdrawForm) {
  withdrawForm.addEventListener('submit', e => {
    e.preventDefault();
    const data = { amount: withdrawForm.elements['amount'].value };
    if (withdrawForm.elements['bank']) data.bank = withdrawForm.elements['bank'].value;
    if (withdrawForm.elements['account']) data.account = withdrawForm.elements['account'].value;
    axios.post('/api/wallet/withdraw_request', data)
      .then(() => alert('ส่งคำขอถอนแล้ว'))
      .catch(() => alert('เกิดข้อผิดพลาด'));
  });
}

if (streamForm) {
  streamForm.addEventListener('submit', e => {
    e.preventDefault();
    api('/api/admin/stream', {hls_url: document.getElementById('hls').value}, 'อัปเดตสตรีมแล้ว');
  });
}

function loadQueues() {
  if (!depList) return;
  axios.get('/api/admin/deposits', {headers: {Authorization: `Bearer ${localStorage.getItem('ADMIN_TOKEN') || ''}`}})
    .then(r => {
      depList.innerHTML = '';
      r.data.forEach(d => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `<span>ผู้ใช้ ${d.user} ${d.amount}</span>
          <div>
            <button class="btn btn-sm btn-success me-1">อนุมัติ</button>
            <button class="btn btn-sm btn-danger">ปฏิเสธ</button>
          </div>`;
        const approveBtn = li.querySelector('.btn-success');
        const rejectBtn = li.querySelector('.btn-danger');
        approveBtn.onclick = () => {
          api(`/api/admin/deposits/${d.id}/approve`, {}, 'อนุมัติแล้ว');
          li.remove();
        };
        rejectBtn.onclick = () => {
          api(`/api/admin/deposits/${d.id}/reject`, {}, 'ปฏิเสธแล้ว');
          li.remove();
        };
        depList.appendChild(li);
      });
    });

  axios.get('/api/admin/withdrawals', {headers: {Authorization: `Bearer ${localStorage.getItem('ADMIN_TOKEN') || ''}`}})
    .then(r => {
      wdList.innerHTML = '';
      r.data.forEach(w => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `<span>ผู้ใช้ ${w.user} ${w.amount}</span>
          <div>
            <button class="btn btn-sm btn-success me-1">อนุมัติ</button>
            <button class="btn btn-sm btn-danger">ปฏิเสธ</button>
          </div>`;
        const approveBtn = li.querySelector('.btn-success');
        const rejectBtn = li.querySelector('.btn-danger');
        approveBtn.onclick = () => {
          api(`/api/admin/withdrawals/${w.id}/approve`, {}, 'อนุมัติแล้ว');
          li.remove();
        };
        rejectBtn.onclick = () => {
          api(`/api/admin/withdrawals/${w.id}/reject`, {}, 'ปฏิเสธแล้ว');
          li.remove();
        };
        wdList.appendChild(li);
      });
    });
}

if (depList || wdList) {
  loadQueues();
  setInterval(loadQueues, 5000);
}

// Admin forms
if (openForm) {
  openForm.addEventListener('submit', e => {
    e.preventDefault();
    api('/api/admin/open_round', {
      red_odds: document.getElementById('red').value,
      blue_odds: document.getElementById('blue').value
    }, 'เปิดรอบแล้ว');
  });
}

if (closeBtn) {
  closeBtn.addEventListener('click', () => {
    api('/api/admin/close_round', {}, 'ปิดรอบแล้ว');
  });
}

if (resultForm) {
  resultForm.addEventListener('submit', e => {
    e.preventDefault();
    api('/api/admin/result', {
      winner: document.getElementById('winner').value
    }, 'บันทึกผลแล้ว');
  });
}
