#!/usr/bin/env python3
"""
Enhanced YouTube Downloader Launcher
This script provides a safe way to launch the YouTube downloader with error handling.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'ttkbootstrap',
        'plyer', 
        'yt-dlp',
        'tkinterdnd2',
        'pillow',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """Install missing dependencies"""
    print("Installing missing dependencies...")
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    return True

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False

def main():
    """Main launcher function"""
    print("Enhanced YouTube Downloader Launcher")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        input("Press Enter to exit...")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Check dependencies
    print("\nChecking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        choice = input("Would you like to install them automatically? (y/n): ").lower()
        
        if choice in ['y', 'yes']:
            if not install_dependencies(missing):
                print("❌ Failed to install some dependencies")
                input("Press Enter to exit...")
                return False
        else:
            print("Please install the missing packages manually:")
            print(f"pip install {' '.join(missing)}")
            input("Press Enter to exit...")
            return False
    else:
        print("✅ All dependencies are installed")
    
    # Check FFmpeg
    print("\nChecking FFmpeg...")
    if check_ffmpeg():
        print("✅ FFmpeg is available")
    else:
        print("⚠️ FFmpeg not found - some features will be limited")
        print("The application will still work, but:")
        print("• Audio conversion may not be available")
        print("• High-quality video downloads may be limited")
        print("\nYou can install FFmpeg later from within the application.")
    
    # Launch the application
    print("\n" + "=" * 40)
    print("Launching Enhanced YouTube Downloader...")
    print("=" * 40)
    
    try:
        # Import and run the main application
        from downloader import main as run_downloader
        run_downloader()
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import downloader module: {e}")
        print("Make sure downloader.py is in the same directory")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check the error message above and try again")
    
    input("Press Enter to exit...")
    return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication cancelled by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        input("Press Enter to exit...")
