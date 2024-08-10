document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('num_results').addEventListener('input', function() {
        document.getElementById('num_results_output').value = this.value;
    });
    document.getElementById('result_size').addEventListener('input', function() {
        document.getElementById('result_size_output').value = this.value;
    });
});

document.body.addEventListener('htmx:configRequest', function(evt) {
    document.getElementById('results').innerHTML = '';  // Clear the current results
    document.getElementById('loading').style.display = 'flex';
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('results').style.display = 'block';
});

