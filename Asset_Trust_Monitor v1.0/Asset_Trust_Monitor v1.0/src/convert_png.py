from PIL import Image

"""Module to convert PNG images for system tray icon usage."""
class PNGConverter:
    """Converts PNG images to required format for system tray"""
    @staticmethod
    def process_ico_titleBar(image_path):
        """Process PNG image for title bar icon usage"""
        img = Image.open(image_path)
        img = img.resize((16, 16), Image.ANTIALIAS)
        return img

    @staticmethod
    def process_ico_tray(image_path):
        """Process PNG image for system tray icon usage"""
        img = Image.open(image_path)
        img = img.resize((32, 32), Image.ANTIALIAS)
        return img
    @staticmethod
    def save_as_ico(image, save_path):
        """Save processed image as ICO format"""
        image.save(save_path, format='ICO')

    @staticmethod
    def process_ico_buttons(image_path):
        """Process PNG image for button icon usage"""
        img = Image.open(image_path)
        img = img.resize((48, 48), Image.ANTIALIAS)
        return img

    @staticmethod
    def convert_png_to_ico(input_path, output_path, for_tray=False, for_titleBar=False, for_buttons=False):
        """Convert PNG to ICO format for either title bar or system tray"""
        if for_tray:
            img = PNGConverter.process_ico_tray(input_path)
        elif for_titleBar:
            img = PNGConverter.process_ico_titleBar(input_path)
        elif for_buttons:
            img = PNGConverter.process_ico_buttons(input_path)
        PNGConverter.save_as_ico(img, output_path)
        return output_path
    
