/**
 * Reusable Chart.js initialization helper
 */
const DashboardCharts = {
    // Default config that respects Tailwind's dark mode
    getDefaultOptions: function() {
        const isDark = document.documentElement.classList.contains('dark');
        const textColor = isDark ? '#9ca3af' : '#6b7280'; // gray-400 : gray-500
        const gridColor = isDark ? '#374151' : '#f3f4f6'; // gray-700 : gray-100

        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor }
                }
            },
            scales: {
                x: {
                    ticks: { color: textColor },
                    grid: { color: gridColor, drawBorder: false }
                },
                y: {
                    ticks: { color: textColor },
                    grid: { color: gridColor, drawBorder: false }
                }
            }
        };
    },

    initLineChart: function(canvasId, labels, dataSets) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: dataSets
            },
            options: {
                ...this.getDefaultOptions(),
                elements: {
                    line: { tension: 0.4 } // Smooth curves
                }
            }
        });
    },

    initBarChart: function(canvasId, labels, dataSets) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: dataSets
            },
            options: {
                ...this.getDefaultOptions()
            }
        });
    },

    initDoughnutChart: function(canvasId, labels, dataSets) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        let options = this.getDefaultOptions();
        // Remove scales for doughnut
        delete options.scales;
        options.cutout = '70%';

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: dataSets
            },
            options: options
        });
    }
};

// Listen for theme changes to update charts dynamically
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('themeToggleBtn')?.addEventListener('click', () => {
        // Small delay to let class toggle finish
        setTimeout(() => {
            // Find all chart instances and update their colors
            for (let id in Chart.instances) {
                let chart = Chart.instances[id];
                let isDark = document.documentElement.classList.contains('dark');
                let textColor = isDark ? '#9ca3af' : '#6b7280';
                let gridColor = isDark ? '#374151' : '#f3f4f6';
                
                if (chart.options.plugins && chart.options.plugins.legend) {
                    chart.options.plugins.legend.labels.color = textColor;
                }
                if (chart.options.scales && chart.options.scales.x) {
                    chart.options.scales.x.ticks.color = textColor;
                    chart.options.scales.x.grid.color = gridColor;
                }
                if (chart.options.scales && chart.options.scales.y) {
                    chart.options.scales.y.ticks.color = textColor;
                    chart.options.scales.y.grid.color = gridColor;
                }
                chart.update();
            }
        }, 50);
    });
});
