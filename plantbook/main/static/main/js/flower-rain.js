$(document).ready(function() {
    // Create flower elements
    function createFlower() {
        const flower = $('<div class="flower"></div>');
        flower.css({
            'left': Math.random() * 100 + '%',
            'animation-duration': Math.random() * 3 + 2 + 's',
            'animation-delay': Math.random() * 2 + 's',
            'transform': 'rotate(' + Math.random() * 360 + 'deg)',
            'font-size': Math.random() * 20 + 10 + 'px'
        });
        return flower;
    }

    // Start flower rain
    function startFlowerRain() {
        const flowerContainer = $('<div class="flower-container"></div>');
        $('body').append(flowerContainer);

        // Create flowers periodically
        const interval = setInterval(function() {
            const flower = createFlower();
            flowerContainer.append(flower);

            // Remove flower after animation
            flower.on('animationend', function() {
                $(this).remove();
            });
        }, 100);
    }

    // Stop flower rain
    function stopFlowerRain() {
        $('.flower-container').remove();
    }

    // Add hover effects to buttons
    $('.register-button, .btn-primary').hover(
        function() {
            startFlowerRain();
        },
        function() {
            stopFlowerRain();
        }
    );
}); 