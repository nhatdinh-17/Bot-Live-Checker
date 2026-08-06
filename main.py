import sys
import os

# Add bot_live_checker folder to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot_live_checker"))
os.chdir(os.path.join(os.path.dirname(__file__), "bot_live_checker"))

from main import main

if __name__ == "__main__":
    main()
