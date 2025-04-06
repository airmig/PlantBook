from PIL import Image, ImageDraw
import os

def create_favicon():
    # Create a 32x32 image with transparency
    size = 32
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a simple leaf shape
    # Main leaf body
    points = [
        (16, 4),  # Top point
        (28, 8),  # Right point
        (24, 24), # Bottom right
        (8, 24),  # Bottom left
        (4, 8),   # Left point
    ]
    draw.polygon(points, fill=(76, 175, 80, 255))  # #4CAF50 with full opacity
    
    # Save as ICO
    output_path = os.path.join(os.path.dirname(__file__), 'favicon.ico')
    image.save(output_path, format='ICO')

if __name__ == '__main__':
    create_favicon() 