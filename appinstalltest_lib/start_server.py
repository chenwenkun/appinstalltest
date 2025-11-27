import uvicorn
from .main import app
import os
import sys

def main():
    # Ensure the current directory is in sys.path so imports work
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(app, host="0.0.0.0", port=8791)

if __name__ == "__main__":
    main()
