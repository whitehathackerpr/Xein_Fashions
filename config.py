import os

class Config:
    SECRET_KEY = 'your-secret-key-here'
    
    # MySQL Database Config
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '752002'
    MYSQL_DB = 'xein_fashions'
    
    # Upload folder for product images
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Site specific settings
    SITE_NAME = "Xein Fashions"
    CURRENCY = "UGX"
