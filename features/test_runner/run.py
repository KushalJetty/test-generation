from app import create_app
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Create necessary directories
os.makedirs(os.path.join('test_runner', 'screenshots'), exist_ok=True)
os.makedirs(os.path.join('test_runner', 'uploads'), exist_ok=True)
os.makedirs(os.path.join('test_runner', 'reports'), exist_ok=True)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
