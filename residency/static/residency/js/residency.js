const employeeIDInput = document.getElementById('input');
function handleInput() {
    const inputValue = employeeIDInput.value;
    // Check if the input is an 8-digit number
    if (/^\d{8}$/.test(inputValue)) {
        // Run your custom function here
        // For example, you can display a message, record the time in, etc.
        // console.log(`Employee ID entered: ${inputValue}`);
        document.getElementById('myForm').submit();
    }
}
employeeIDInput.focus();
employeeIDInput.addEventListener('input', handleInput);

document.addEventListener('DOMContentLoaded', function () {
    const timePlaceholder = document.getElementById('timePlaceholder');

    function updateTime() {
        fetch("/current_time") // Send an AJAX request to the server
            .then(response => response.json())
            .then(data => {
                const time = data.time;
                timePlaceholder.textContent = time >= '07:00:00' && time < '21:00:00' 
                    ? "Oras: " + time 
                    : "Closing Hours";

                // Enable or disable the input based on the time
                if (time >= '07:00:00' && time < '21:00:00') {
                    employeeIDInput.disabled = false; // Enable the input
                } else {
                    employeeIDInput.disabled = true; // Disable the input
                    employeeIDInput.value = ""; // Clear the input if disabled
                }
            })
            .catch(error => {
                console.error('Error fetching time:', error);
            });
    }

    // Initial time update
    updateTime();

    // Update the time every second (1000 milliseconds)
    setInterval(updateTime, 1000);
});