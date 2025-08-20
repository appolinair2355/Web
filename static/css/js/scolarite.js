let currentStudentId = null;

function openPayModal(id, name) {
    currentStudentId = id;
    document.getElementById('modalStudentName').textContent = name;
    document.getElementById('payModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('payModal').style.display = 'none';
}

document.getElementById('payForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const amount = parseFloat(document.getElementById('payAmount').value);
    fetch(`/api/payer/${currentStudentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ montant: amount })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const row = document.getElementById(`row-${currentStudentId}`);
            row.querySelector('.paye').textContent = data.paye + ' FCFA';
            row.querySelector('.reste').textContent = data.reste + ' FCFA';
            closeModal();
        }
    });
});
          
