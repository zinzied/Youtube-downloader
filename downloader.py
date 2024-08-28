from sre_constants import INFO, SUCCESS
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, Listbox, END, Menu
import threading
from pydub import AudioSegment
from pydub.utils import which
import os
from plyer import notification
import yt_dlp as youtube_dl
from tkinterdnd2 import TkinterDnD, DND_FILES

# Ensure pydub uses ffmpeg
AudioSegment.converter = which("ffmpeg")

# Function to handle right-click context menu
def show_context_menu(event):
    context_menu.post(event.x_root, event.y_root)

# Function to cut text
def cut_text():
    url_entry.event_generate("<<Cut>>")

# Function to copy text
def copy_text():
    url_entry.event_generate("<<Copy>>")

# Function to paste text
def paste_text():
    url_entry.event_generate("<<Paste>>")

# Create the main window
root = TkinterDnD.Tk()
root.title("YouTube Video Downloader")

# Apply ttkbootstrap theme
style = ttk.Style("cosmo")

# Load and set the window icon
icon_image = ttk.PhotoImage(file='video.png')
root.iconphoto(False, icon_image)

# Create and place the URL entry
ttk.Label(root, text="YouTube URL:").grid(row=0, column=0, padx=10, pady=10)
url_entry = ttk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=10)

# Create the context menu
context_menu = Menu(root, tearoff=0)
context_menu.add_command(label="Cut", command=cut_text)
context_menu.add_command(label="Copy", command=copy_text)
context_menu.add_command(label="Paste", command=paste_text)

# Bind the right-click event to the URL entry
url_entry.bind("<Button-3>", show_context_menu)

def show_notification(title, message):
    notification.notify(
        title=title,
        message=message,
        app_icon=None,
        timeout=10,
    )

download_queue = []
stop_event = threading.Event()

def add_to_queue():
    video_url = url_entry.get()
    if video_url:
        download_queue.append(video_url)
        url_entry.delete(0, END)
        process_queue()

def process_queue():
    if download_queue and not threading.active_count() > 1:
        video_url = download_queue.pop(0)
        download_thread = threading.Thread(target=download_video, args=(video_url,))
        download_thread.start()

def download_video(video_url):
    save_path = filedialog.askdirectory()
    download_format = format_var.get()
    
    if not video_url or not save_path:
        messagebox.showerror("Error", "Please provide both URL and save path.")
        return
    
    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'progress_hooks': [on_progress],
    }
    
    if download_format == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Add the downloaded file to the listbox
        downloaded_files_listbox.insert(END, os.path.basename(ydl.prepare_filename(ydl.extract_info(video_url, download=False))))
        
        messagebox.showinfo("Success", "Download completed!")
        show_notification("Download Complete", "Video has been downloaded successfully!")
    except Exception as e:
        if stop_event.is_set():
            messagebox.showinfo("Stopped", "Download stopped by user.")
        else:
            messagebox.showerror("Error", f"An error occurred: {e}")
            show_notification("Download Failed", f"An error occurred: {e}")
    finally:
        stop_event.clear()
        process_queue()

def on_progress(d):
    if stop_event.is_set():
        raise youtube_dl.utils.DownloadError("Download stopped by user.")
    if d['status'] == 'downloading':
        total_size = d.get('total_bytes') or d.get('total_bytes_estimate')
        bytes_downloaded = d.get('downloaded_bytes')
        percentage_of_completion = bytes_downloaded / total_size * 100
        progress_var.set(percentage_of_completion)
        progress_label_var.set(f"{percentage_of_completion:.2f}%")
        root.update_idletasks()

def stop_download():
    stop_event.set()

# Function to handle dropped files
def drop(event):
    url_entry.delete(0, END)
    url_entry.insert(0, event.data)

# Bind the drop event to the URL entry
url_entry.drop_target_register(DND_FILES)
url_entry.dnd_bind('<<Drop>>', drop)

# Create and place the format selection radio buttons
format_var = ttk.StringVar(value='mp4')
ttk.Label(root, text="Format:").grid(row=1, column=0, padx=10, pady=10)
ttk.Radiobutton(root, text="MP4", variable=format_var, value='mp4').grid(row=1, column=1, padx=10, pady=10, sticky='w')
ttk.Radiobutton(root, text="MP3", variable=format_var, value='mp3').grid(row=1, column=1, padx=10, pady=10, sticky='e')

# Create and place the download button
download_button = ttk.Button(root, text="Start", command=add_to_queue, bootstyle=SUCCESS)
download_button.grid(row=2, column=0, columnspan=2, pady=10)

# Create and place the stop button
stop_button = ttk.Button(root, text="Stop", command=stop_download, bootstyle=DANGER)
stop_button.grid(row=2, column=1, columnspan=2, pady=10)

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
