function fetchLogs(url, tableId) {
  axios.get(url, {headers: {Authorization: `Bearer ${localStorage.getItem('ADMIN_TOKEN') || ''}`}})
    .then(r => {
      const tbody = document.querySelector(`#${tableId} tbody`);
      tbody.innerHTML = '';
      r.data.forEach(row => {
        const tr = document.createElement('tr');
        Object.values(row).forEach(v => {
          const td = document.createElement('td');
          td.textContent = v;
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    });
}

fetchLogs('/api/logs/bets', 'betTable');
fetchLogs('/api/logs/wallets', 'walletTable');
fetchLogs('/api/logs/system', 'sysTable');
fetchLogs('/api/logs/security', 'secTable');
