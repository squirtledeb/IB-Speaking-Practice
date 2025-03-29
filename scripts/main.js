document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('start-practice');
    
    startButton.addEventListener('click', function() {
        const language = document.getElementById('language-select').value;
        
        if (!language) {
            alert('Please select a language');
            return;
        }
        
        // Redirect to the appropriate practice page based on your existing structure
        window.location.href = `practice/${language}/index.html`;
        
        // If your structure is different, adjust the path accordingly
        // For example, if you have language-specific HTML files in the root:
        // window.location.href = `${language}.html`;
    });
});