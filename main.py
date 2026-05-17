import sys
import os

# Ensure the package directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solar_system_app.application import SolarSystemApplication

if __name__ == "__main__":
    SolarSystemApplication().run()
