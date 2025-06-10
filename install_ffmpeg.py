#!/usr/bin/env python3
"""
FFmpeg Installation Helper Script
This script attempts to install FFmpeg automatically on Windows.
"""

import subprocess
import sys
import os
import platform
import urllib.request
import zipfile
import shutil
from pathlib import Path

def run_command(command, shell=True):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "", "Command not found or timed out"

def check_ffmpeg():
    """Check if FFmpeg is already installed"""
    success, stdout, stderr = run_command("ffmpeg -version")
    return success

def install_with_chocolatey():
    """Try to install FFmpeg using Chocolatey"""
    print("Checking for Chocolatey...")
    success, _, _ = run_command("choco --version")
    if success:
        print("Chocolatey found! Installing FFmpeg...")
        success, stdout, stderr = run_command("choco install ffmpeg -y")
        if success:
            print("✅ FFmpeg installed successfully via Chocolatey!")
            return True
        else:
            print(f"❌ Chocolatey installation failed: {stderr}")
    else:
        print("Chocolatey not found.")
    return False

def install_with_winget():
    """Try to install FFmpeg using Winget"""
    print("Checking for Winget...")
    success, _, _ = run_command("winget --version")
    if success:
        print("Winget found! Installing FFmpeg...")
        success, stdout, stderr = run_command("winget install ffmpeg")
        if success:
            print("✅ FFmpeg installed successfully via Winget!")
            return True
        else:
            print(f"❌ Winget installation failed: {stderr}")
    else:
        print("Winget not found.")
    return False

def manual_install_windows():
    """Manual installation for Windows"""
    print("\n" + "="*50)
    print("Manual Installation Guide")
    print("="*50)
    
    ffmpeg_dir = Path("C:/ffmpeg")
    bin_dir = ffmpeg_dir / "bin"
    
    print(f"\nFor manual installation:")
    print(f"1. Download FFmpeg from: https://ffmpeg.org/download.html")
    print(f"2. Extract to: {ffmpeg_dir}")
    print(f"3. Add {bin_dir} to your system PATH")
    print(f"4. Restart this application")
    
    # Try to open the download page
    try:
        import webbrowser
        choice = input("\nWould you like to open the FFmpeg download page? (y/n): ").lower()
        if choice in ['y', 'yes']:
            webbrowser.open("https://ffmpeg.org/download.html")
    except ImportError:
        pass
    
    return False

def add_to_path_windows(directory):
    """Add directory to Windows PATH (requires admin privileges)"""
    try:
        import winreg
        
        # Open the registry key for system environment variables
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                           r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                           0, winreg.KEY_ALL_ACCESS)
        
        # Get current PATH
        current_path, _ = winreg.QueryValueEx(key, "PATH")
        
        # Add new directory if not already present
        if str(directory) not in current_path:
            new_path = current_path + ";" + str(directory)
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"✅ Added {directory} to system PATH")
            return True
        else:
            print(f"Directory {directory} already in PATH")
            return True
            
    except Exception as e:
        print(f"❌ Failed to add to PATH: {e}")
        print("You may need to run this script as Administrator")
        return False
    finally:
        try:
            winreg.CloseKey(key)
        except:
            pass

def main():
    """Main installation function"""
    print("FFmpeg Installation Helper")
    print("=" * 30)
    
    # Check if already installed
    if check_ffmpeg():
        print("✅ FFmpeg is already installed and working!")
        return True
    
    print("FFmpeg not found. Attempting installation...")
    
    # Detect OS
    system = platform.system().lower()
    
    if system == "windows":
        # Try package managers first
        if install_with_chocolatey() or install_with_winget():
            # Verify installation
            if check_ffmpeg():
                print("\n✅ Installation successful!")
                print("FFmpeg is now available. Please restart the YouTube Downloader application.")
                return True
            else:
                print("⚠️ Installation completed but FFmpeg is not in PATH.")
                print("You may need to restart your command prompt or computer.")
        
        # Fall back to manual installation guide
        manual_install_windows()
        
    else:
        print(f"Automatic installation not supported for {system}")
        print("Please install FFmpeg manually using your system's package manager:")
        print("- Ubuntu/Debian: sudo apt install ffmpeg")
        print("- macOS: brew install ffmpeg")
        print("- Arch Linux: sudo pacman -S ffmpeg")
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n" + "="*50)
            print("Installation incomplete. Please follow the manual steps above.")
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    
    input("\nPress Enter to exit...")
