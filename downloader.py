import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, Listbox
from pytube import YouTube
import threading
from pydub import AudioSegment
from pydub.utils import which
import os
from plyer import notification

# Ensure pydub uses ffmpeg
AudioSegment.converter = which("ffmpeg")

def show_notification(title, message):
    notification.notify(
        title=title,
        message=message,
        app_icon=None,
        timeout=10,
    )

def on_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    progress_var.set(percentage_of_completion)
    progress_label_var.set(f"{percentage_of_completion:.2f}%")
    root.update_idletasks()

def download_video():
    video_url = url_entry.get()
    save_path = filedialog.askdirectory()
    download_format = format_var.get()
    
    if not video_url or not save_path:
        messagebox.showerror("Error", "Please provide both URL and save path.")
        return
    
    try:
        yt = YouTube(video_url, on_progress_callback=on_progress)
        if download_format == 'mp4':
            stream = yt.streams.get_highest_resolution()
            file_extension = 'mp4'
        elif download_format == 'mp3':
            stream = yt.streams.filter(only_audio=True).first()
            file_extension = 'mp4'  # Download as mp4 first, then convert to mp3
        
        downloaded_file = stream.download(output_path=save_path)
        
        if download_format == 'mp3':
            base, ext = os.path.splitext(downloaded_file)
            new_file = base + '.mp3'
            audio = AudioSegment.from_file(downloaded_file)
            audio.export(new_file, format='mp3')
            os.remove(downloaded_file)  # Remove the original mp4 file
            downloaded_file = new_file
        
        # Add the downloaded file to the listbox
        downloaded_files_listbox.insert(END, os.path.basename(downloaded_file))
        
        messagebox.showinfo("Success", "Download completed!")
        show_notification("Download Complete", f"Video '{yt.title}' has been downloaded successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        show_notification("Download Failed", f"An error occurred: {e}")

def start_download_thread():
    download_thread = threading.Thread(target=download_video)
    download_thread.start()

# Create the main window with a ttkbootstrap theme
root = ttk.Window(themename="cosmo")
root.title("YouTube Video Downloader")

# Load and set the window icon
icon_image = ttk.PhotoImage(file='video.png')
root.iconphoto(False, icon_image)

# Create and place the URL entry
ttk.Label(root, text="YouTube URL:").grid(row=0, column=0, padx=10, pady=10)
url_entry = ttk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=10)

# Create and place the format selection radio buttons
format_var = ttk.StringVar(value='mp4')
ttk.Label(root, text="Format:").grid(row=1, column=0, padx=10, pady=10)
ttk.Radiobutton(root, text="MP4", variable=format_var, value='mp4').grid(row=1, column=1, padx=10, pady=10, sticky='w')
ttk.Radiobutton(root, text="MP3", variable=format_var, value='mp3').grid(row=1, column=1, padx=10, pady=10, sticky='e')

# Create and place the download button
download_button = ttk.Button(root, text="Download", command=start_download_thread, bootstyle=SUCCESS)
download_button.grid(row=2, column=0, columnspan=2, pady=10)

# Create and place the progress bar
progress_var = ttk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, bootstyle=INFO)
progress_bar.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

# Create and place the progress percentage label
progress_label_var = ttk.StringVar(value="0.00%")
progress_label = ttk.Label(root, textvariable=progress_label_var)
progress_label.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

# Create and place the listbox for downloaded files
ttk.Label(root, text="Downloaded Files:").grid(row=5, column=0, padx=10, pady=10, sticky='w')
downloaded_files_listbox = Listbox(root, height=10)
downloaded_files_listbox.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

# Run the application
root.mainloop()
