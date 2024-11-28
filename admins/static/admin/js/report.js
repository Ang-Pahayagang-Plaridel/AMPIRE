$(document).ready(function() {
    $('#date-form').submit(function(event) {
        event.preventDefault();
        fetchReports();
    });

    // Submit the form on page load
    fetchReports();

    // Re-submit the form when date inputs change
    $('#date-form input[type="date"]').change(function() {
        $('#date-form').submit();
    });

    // Re-submit the form when checkboxes change
    $('#date-form input[type="checkbox"]').change(function() {
        $('#date-form').submit();
    });
});

$(document).ready(function() {
    $('#date-form').submit(function(event) {
        event.preventDefault();
        fetchReports();
    });
});

async function fetchReports() {
    const formData = $('#date-form').serialize();
    try {
        const response = await $.ajax({
            url: "/admin/fetch_reports",
            data: formData,
            dataType: 'json'
        });
        console.log(response.reports)
        renderReports(response.reports);
        renderChart(response.section_reports);
    } catch (error) {
        console.error("AJAX error:", error);
    }
}

function renderReports(reports) {
    const reportContainer = $('#report-container');
    if (reports.length === 0) {
        reportContainer.html('<h2>No Report Available</h2>');
        return;
    }

    let reportHtml = `
        <div class="ampire-table">
            <h2>Report</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Position</th>
                        <th>Residency</th>
                    </tr>
                </thead>
                <tbody>`;

    reports.forEach(row => {
        reportHtml += `
            <tr>
                <td>${row.id}</td>
                <td>${row.name}</td>
                <td>${row.position}</td>
                <td>${row.residency} min</td>
            </tr>`;
    });

    reportHtml += `</tbody></table></div>
                <div class="side-col">
                    <div class="section-report">
                        <h2>Seksyon</h2>
                        <div class="chart-container" id="bar-chart">
                            <canvas id="myChart"></canvas>
                        </div>
                    </div>
                </div>`;

    reportContainer.html(reportHtml);
}

function renderChart(sectionReports) {
    const labels = sectionReports.map(report => report.name);
    const values = sectionReports.map(report => report.residency);
    const backgroundColors = sectionReports.map(report => report.primary_color);
    const borderColors = sectionReports.map(report => report.secondary_color);
    // const backgroundColors = ['#3C7F72', '#7A5EA8', '#242223', '#DC6874', '#083b73', '#fad02c', '#f9943b'];
    // const borderColors = ['#63B98F', '#9C80C8', '#474746', '#E37E8B', '#2D6BBF', '#FEEC61', '#FFB561'];

    const ctx = document.getElementById('myChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Residency',
                data: values,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1,
            }]
        },
        options: {
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}
