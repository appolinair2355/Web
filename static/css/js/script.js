// Recherche en temps réel
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            if (query.length > 1) {
                fetch(`/search?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(students => {
                        displaySearchResults(students);
                    });
            } else {
                searchResults.innerHTML = '';
            }
        });
    }
    
    // Gestion du modal de paiement
    const modal = document.getElementById('paymentModal');
    const closeBtn = document.querySelector('.close');
    
    if (closeBtn) {
        closeBtn.onclick = function() {
            modal.style.display = 'none';
        }
        
        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    }
});

function displaySearchResults(students) {
    const searchResults = document.getElementById('searchResults');
    
    if (students.length === 0) {
        searchResults.innerHTML = '<p>Aucun élève trouvé.</p>';
        return;
    }
    
    let html = '<div class="search-results">';
    students.forEach(student => {
        html += `
            <div class="search-result-item">
                <a href="/edit/${student.id}">
                    <strong>${student.prenoms} ${student.nom}</strong>
                    <span>${student.classe} - ${student.frais_scolarite.reste} FCFA restant</span>
                </a>
            </div>
        `;
    });
    html += '</div>';
    
    searchResults.innerHTML = html;
}

function showPaymentModal(studentId, studentName) {
    const modal = document.getElementById('paymentModal');
    const studentNameSpan = document.getElementById('studentName');
    const form = document.getElementById('paymentForm');
    
    studentNameSpan.textContent = studentName;
    form.action = `/pay/${studentId}`;
    modal.style.display = 'block';
          }
      
