// Chart generation setup wrapper
document.addEventListener("DOMContentLoaded", function() {
  const dataEl = document.getElementById('chart-data');
  if (!dataEl) return; // Equivalent to your old {% if %} Check

  // Read data cleanly from the HTML elements
 const labels  = JSON.parse(dataEl.dataset.labels || '[]');
  const planned = JSON.parse(dataEl.dataset.planned || '[]');
  const studied = JSON.parse(dataEl.dataset.studied || '[]');
  const colors  = JSON.parse(dataEl.dataset.colors || '[]');
 



  // Instantiating Chart Object Canvas Context
  const ctx = document.getElementById('progressChart');
  if (ctx) {
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Planned hours',
            data: planned,
            backgroundColor: 'rgba(200,216,245,0.8)',
            borderColor: '#1E3A6E',
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: 'Studied hours',
            data: studied,
            backgroundColor: colors,
            borderRadius: 4,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: context => ` ${context.dataset.label}: ${context.parsed.y}h`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: '#9CA3AF',
              callback: value => value + 'h'
            },
            grid: { color: 'rgba(0,0,0,0.05)' }
          },
          x: {
            ticks: { color: '#374151' },
            grid:  { display: false }
          }
        }
      }
    });
  }

});
