$(document).ready(function() {
    // Handle search form submission
    $('.search-form').on('submit', function(e) {
        e.preventDefault();
        
        // Show loading screen
        $('#loading-screen').fadeIn();
        
        // Get the search query
        const query = $(this).find('input[type="text"]').val();
        
        // Submit the form programmatically
        this.submit();
    });
}); 