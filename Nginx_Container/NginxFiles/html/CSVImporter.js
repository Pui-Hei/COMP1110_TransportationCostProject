document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('csvImportForm');
    const resultBox = document.getElementById('result');
    const submitBtn = document.getElementById('submitBtn');

    form.addEventListener('submit', async function (event) {
        event.preventDefault();

        resultBox.className = 'result';
        resultBox.textContent = 'Uploading and importing CSV data...';
        submitBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('map_id', document.getElementById('map_id').value);
            formData.append('map_name', document.getElementById('map_name').value);
            formData.append('landmarks', document.getElementById('landmarks').files[0]);
            formData.append('train_lines', document.getElementById('train_lines').files[0]);
            formData.append('train_fees', document.getElementById('train_fees').files[0]);
            formData.append('bus_lines', document.getElementById('bus_lines').files[0]);

            const response = await fetch('/import-map-data', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                resultBox.className = 'result success';
                resultBox.textContent = JSON.stringify(data, null, 2);
            } else {
                resultBox.className = 'result error';
                resultBox.textContent = JSON.stringify(data, null, 2);
            }
        } catch (error) {
            resultBox.className = 'result error';
            resultBox.textContent = JSON.stringify({
                success: false,
                error: error.message
            }, null, 2);
        } finally {
            submitBtn.disabled = false;
        }
    });
});