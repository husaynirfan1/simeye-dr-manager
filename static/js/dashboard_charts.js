document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Safely grab the data passed from Django's json_script tags
    const rawStatusData = JSON.parse(document.getElementById('statusData').textContent);
    const rawSeverityData = JSON.parse(document.getElementById('severityData').textContent);

    // --- 2. Status Doughnut Chart ---
    const statusCtx = document.getElementById('statusChart').getContext('2d');
    
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            // Use .map() to extract the arrays JavaScript needs
            labels: rawStatusData.map(item => item.status),
            datasets: [{
                data: rawStatusData.map(item => item.count),
                backgroundColor: ['#0d6efd', '#ffc107', '#dc3545', '#198754', '#6c757d', '#0dcaf0'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });

    // --- 3. Severity Bar Chart ---
    const severityCtx = document.getElementById('severityChart').getContext('2d');
    
    new Chart(severityCtx, {
        type: 'bar',
        data: {
            // Prepend "Severity " to the labels
            labels: rawSeverityData.map(item => "Severity " + item.severity),
            datasets: [{
                label: 'Number of Deficiencies',
                data: rawSeverityData.map(item => item.count),
                backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#0dcaf0', '#6c757d'],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false } 
            },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
});