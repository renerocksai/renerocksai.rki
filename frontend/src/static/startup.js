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


function toggleDivs() {
    const div1 = document.getElementById('div1');
    const div2 = document.getElementById('div2');
    const bt = document.getElementById('switcherButton');

    
    if (div1.classList.contains('active')) {
        div1.classList.remove('active');
        div1.classList.add('inactive');
        div2.classList.add('active');
        bt.innerText = "Umschalten zur Corona-Files.com KI-Suche";
    } else {
        div2.classList.remove('active');
        div1.classList.remove('inactive');
        div1.classList.add('active');
        bt.innerText = "Umschalten zur RKILeak.com Stichwort-/KI-Suchmaske";
    }
}

document.getElementById('switcherButton').onclick = toggleDivs;
