import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, Listbox, END, Menu, Text, Scrollbar
import threading
import os
import requests
from PIL import Image, ImageTk
import io
import webbrowser

# Custom modules
from config import config
from download_history import history

# Third-party imports
try:
    from pydub import AudioSegment
    from pydub.utils import which
    # Ensure pydub uses ffmpeg
    AudioSegment.converter = which("ffmpeg")
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Warning: pydub not available. Audio processing features may be limited.")

from plyer import notification
import yt_dlp as youtube_dl
from tkinterdnd2 import TkinterDnD, DND_FILES

class YouTubeDownloaderApp:
    def __init__(self):
        # Initialize main window
        self.root = TkinterDnD.Tk()
        self.root.title("Enhanced YouTube Downloader")
        self.root.geometry(config.get('window_geometry', '900x700'))

        # Initialize variables
        self.download_queue = []
        self.stop_events = {}  # Track stop events for each download
        self.current_downloads = {}  # Track active downloads
        self.playlist_info = None

        # Apply theme
        self.apply_theme()

        # Load and set icon
        try:
            icon_image = ttk.PhotoImage(file='video.png')
            self.root.iconphoto(False, icon_image)
        except:
            pass  # Icon file not found, continue without it

        # Create UI
        self.create_ui()

        # Bind events
        self.bind_events()

    def apply_theme(self):
        """Apply the selected theme"""
        theme_name = config.get('theme', 'cosmo')
        self.style = ttk.Style(theme_name)

        # Apply dark mode if enabled
        if config.get('dark_mode', False):
            dark_themes = ['darkly', 'cyborg', 'vapor', 'superhero', 'solar']
            if theme_name not in dark_themes:
                self.style = ttk.Style('darkly')

    def create_ui(self):
        """Create the main user interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self.create_download_tab()
        self.create_history_tab()
        self.create_settings_tab()
        self.create_about_tab()

    def create_download_tab(self):
        """Create the main download tab"""
        self.download_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.download_frame, text="Download")

        # URL input section
        url_frame = ttk.LabelFrame(self.download_frame, text="Video/Playlist URL", padding=10)
        url_frame.pack(fill='x', padx=10, pady=5)

        self.url_entry = ttk.Entry(url_frame, font=('Arial', 11))
        self.url_entry.pack(fill='x', pady=(0, 10))

        # Add drag and drop support
        self.url_entry.drop_target_register(DND_FILES)
        self.url_entry.dnd_bind('<<Drop>>', self.on_drop)

        # Context menu for URL entry
        self.create_context_menu()

        # Buttons frame
        buttons_frame = ttk.Frame(url_frame)
        buttons_frame.pack(fill='x')

        ttk.Button(buttons_frame, text="Get Info", command=self.get_video_info,
                  bootstyle=INFO).pack(side='left', padx=(0, 5))
        ttk.Button(buttons_frame, text="Clear", command=self.clear_url,
                  bootstyle=SECONDARY).pack(side='left')

        # Video info section
        self.create_video_info_section()

        # Download options section
        self.create_download_options_section()

        # Progress section
        self.create_progress_section()

        # Queue section
        self.create_queue_section()

    def create_context_menu(self):
        """Create context menu for URL entry"""
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Cut", command=lambda: self.url_entry.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Copy", command=lambda: self.url_entry.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Paste", command=lambda: self.url_entry.event_generate("<<Paste>>"))
        self.url_entry.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu"""
        self.context_menu.post(event.x_root, event.y_root)

    def create_video_info_section(self):
        """Create video information display section"""
        self.info_frame = ttk.LabelFrame(self.download_frame, text="Video Information", padding=10)
        self.info_frame.pack(fill='x', padx=10, pady=5)

        # Create info display with thumbnail
        info_container = ttk.Frame(self.info_frame)
        info_container.pack(fill='x')

        # Thumbnail frame
        self.thumbnail_frame = ttk.Frame(info_container)
        self.thumbnail_frame.pack(side='left', padx=(0, 10))

        self.thumbnail_label = ttk.Label(self.thumbnail_frame, text="No thumbnail")
        self.thumbnail_label.pack()

        # Info text frame
        info_text_frame = ttk.Frame(info_container)
        info_text_frame.pack(side='left', fill='both', expand=True)

        self.info_text = Text(info_text_frame, height=6, wrap='word', state='disabled')
        info_scrollbar = Scrollbar(info_text_frame, orient='vertical', command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scrollbar.set)

        self.info_text.pack(side='left', fill='both', expand=True)
        info_scrollbar.pack(side='right', fill='y')

    def create_download_options_section(self):
        """Create download options section"""
        options_frame = ttk.LabelFrame(self.download_frame, text="Download Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)

        # Format selection
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(format_frame, text="Format:").pack(side='left')
        self.format_var = ttk.StringVar(value=config.get('default_format', 'mp4'))

        formats = config.get_formats()
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.format_var,
                                        values=list(formats.keys()), state='readonly', width=15)
        self.format_combo.pack(side='left', padx=(10, 20))

        # Quality selection
        ttk.Label(format_frame, text="Quality:").pack(side='left')
        self.quality_var = ttk.StringVar(value=config.get('default_quality', 'best'))

        self.quality_combo = ttk.Combobox(format_frame, textvariable=self.quality_var,
                                         state='readonly', width=15)
        self.quality_combo.pack(side='left', padx=(10, 0))

        # Update quality options when format changes
        self.format_combo.bind('<<ComboboxSelected>>', self.update_quality_options)
        self.update_quality_options()

        # Additional options
        options_row2 = ttk.Frame(options_frame)
        options_row2.pack(fill='x', pady=(0, 10))

        self.subtitle_var = ttk.BooleanVar(value=config.get('download_subtitles', False))
        ttk.Checkbutton(options_row2, text="Download Subtitles",
                       variable=self.subtitle_var).pack(side='left')

        self.playlist_var = ttk.BooleanVar(value=config.get('auto_detect_playlist', True))
        ttk.Checkbutton(options_row2, text="Auto-detect Playlist",
                       variable=self.playlist_var).pack(side='left', padx=(20, 0))

        # Download path
        path_frame = ttk.Frame(options_frame)
        path_frame.pack(fill='x')

        ttk.Label(path_frame, text="Download Path:").pack(side='left')
        self.path_var = ttk.StringVar(value=config.get('last_used_path', config.get('default_download_path')))
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side='left', fill='x', expand=True, padx=(10, 5))

        ttk.Button(path_frame, text="Browse", command=self.browse_path,
                  bootstyle=SECONDARY).pack(side='right')

    def create_progress_section(self):
        """Create progress tracking section"""
        progress_frame = ttk.LabelFrame(self.download_frame, text="Download Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)

        # Current download info
        self.current_download_label = ttk.Label(progress_frame, text="No active downloads")
        self.current_download_label.pack(anchor='w')

        # Progress bar
        self.progress_var = ttk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, bootstyle=INFO)
        self.progress_bar.pack(fill='x', pady=(5, 0))

        # Progress details
        progress_details_frame = ttk.Frame(progress_frame)
        progress_details_frame.pack(fill='x', pady=(5, 0))

        self.progress_label_var = ttk.StringVar(value="0.00%")
        self.progress_label = ttk.Label(progress_details_frame, textvariable=self.progress_label_var)
        self.progress_label.pack(side='left')

        self.speed_label_var = ttk.StringVar(value="")
        self.speed_label = ttk.Label(progress_details_frame, textvariable=self.speed_label_var)
        self.speed_label.pack(side='right')

        # Control buttons
        control_frame = ttk.Frame(progress_frame)
        control_frame.pack(fill='x', pady=(10, 0))

        self.download_button = ttk.Button(control_frame, text="Download",
                                         command=self.start_download, bootstyle=SUCCESS)
        self.download_button.pack(side='left', padx=(0, 5))

        self.stop_button = ttk.Button(control_frame, text="Stop",
                                     command=self.stop_download, bootstyle=DANGER)
        self.stop_button.pack(side='left', padx=(0, 5))

        self.pause_button = ttk.Button(control_frame, text="Pause All",
                                      command=self.pause_all_downloads, bootstyle=WARNING)
        self.pause_button.pack(side='left')

    def create_queue_section(self):
        """Create download queue section"""
        queue_frame = ttk.LabelFrame(self.download_frame, text="Download Queue", padding=10)
        queue_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Queue listbox with scrollbar
        queue_container = ttk.Frame(queue_frame)
        queue_container.pack(fill='both', expand=True)

        self.queue_listbox = Listbox(queue_container, height=8)
        queue_scrollbar = Scrollbar(queue_container, orient='vertical', command=self.queue_listbox.yview)
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)

        self.queue_listbox.pack(side='left', fill='both', expand=True)
        queue_scrollbar.pack(side='right', fill='y')

        # Queue control buttons
        queue_buttons = ttk.Frame(queue_frame)
        queue_buttons.pack(fill='x', pady=(10, 0))

        ttk.Button(queue_buttons, text="Add to Queue", command=self.add_to_queue,
                  bootstyle=INFO).pack(side='left', padx=(0, 5))
        ttk.Button(queue_buttons, text="Remove Selected", command=self.remove_from_queue,
                  bootstyle=SECONDARY).pack(side='left', padx=(0, 5))
        ttk.Button(queue_buttons, text="Clear Queue", command=self.clear_queue,
                  bootstyle=DANGER).pack(side='left')

        ttk.Label(queue_buttons, text="Queue Status:").pack(side='right', padx=(20, 5))
        self.queue_status_var = ttk.StringVar(value="0 items")
        ttk.Label(queue_buttons, textvariable=self.queue_status_var).pack(side='right')

    def create_history_tab(self):
        """Create download history tab"""
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="History")

        # Search and filter section
        search_frame = ttk.Frame(self.history_frame)
        search_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(search_frame, text="Search:").pack(side='left')
        self.search_var = ttk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(5, 10))

        ttk.Button(search_frame, text="Search", command=self.search_history,
                  bootstyle=INFO).pack(side='left', padx=(0, 5))
        ttk.Button(search_frame, text="Refresh", command=self.refresh_history,
                  bootstyle=SECONDARY).pack(side='left')

        # History display
        history_container = ttk.Frame(self.history_frame)
        history_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Create treeview for history
        columns = ('Title', 'Format', 'Quality', 'Size', 'Date', 'Status')
        self.history_tree = ttk.Treeview(history_container, columns=columns, show='headings', height=15)

        # Configure columns
        self.history_tree.heading('Title', text='Title')
        self.history_tree.heading('Format', text='Format')
        self.history_tree.heading('Quality', text='Quality')
        self.history_tree.heading('Size', text='Size')
        self.history_tree.heading('Date', text='Date')
        self.history_tree.heading('Status', text='Status')

        self.history_tree.column('Title', width=300)
        self.history_tree.column('Format', width=80)
        self.history_tree.column('Quality', width=80)
        self.history_tree.column('Size', width=100)
        self.history_tree.column('Date', width=120)
        self.history_tree.column('Status', width=80)

        # Scrollbars for history
        history_v_scrollbar = ttk.Scrollbar(history_container, orient='vertical', command=self.history_tree.yview)
        history_h_scrollbar = ttk.Scrollbar(history_container, orient='horizontal', command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=history_v_scrollbar.set, xscrollcommand=history_h_scrollbar.set)

        self.history_tree.pack(side='left', fill='both', expand=True)
        history_v_scrollbar.pack(side='right', fill='y')
        history_h_scrollbar.pack(side='bottom', fill='x')

        # History control buttons
        history_buttons = ttk.Frame(self.history_frame)
        history_buttons.pack(fill='x', padx=10, pady=(0, 10))

        ttk.Button(history_buttons, text="Open File", command=self.open_selected_file,
                  bootstyle=SUCCESS).pack(side='left', padx=(0, 5))
        ttk.Button(history_buttons, text="Open Folder", command=self.open_file_folder,
                  bootstyle=INFO).pack(side='left', padx=(0, 5))
        ttk.Button(history_buttons, text="Delete Entry", command=self.delete_history_entry,
                  bootstyle=DANGER).pack(side='left', padx=(0, 5))
        ttk.Button(history_buttons, text="Clear History", command=self.clear_history,
                  bootstyle=DANGER).pack(side='left')

        # Statistics
        stats_frame = ttk.LabelFrame(self.history_frame, text="Statistics", padding=10)
        stats_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.stats_label = ttk.Label(stats_frame, text="Loading statistics...")
        self.stats_label.pack()

        # Load initial history
        self.refresh_history()

    def create_settings_tab(self):
        """Create settings tab"""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")

        # Theme settings
        theme_frame = ttk.LabelFrame(self.settings_frame, text="Appearance", padding=10)
        theme_frame.pack(fill='x', padx=10, pady=10)

        theme_row1 = ttk.Frame(theme_frame)
        theme_row1.pack(fill='x', pady=(0, 10))

        ttk.Label(theme_row1, text="Theme:").pack(side='left')
        self.theme_var = ttk.StringVar(value=config.get('theme', 'cosmo'))
        theme_combo = ttk.Combobox(theme_row1, textvariable=self.theme_var,
                                  values=config.get_available_themes(), state='readonly')
        theme_combo.pack(side='left', padx=(10, 20))

        self.dark_mode_var = ttk.BooleanVar(value=config.get('dark_mode', False))
        ttk.Checkbutton(theme_row1, text="Dark Mode", variable=self.dark_mode_var,
                       command=self.toggle_dark_mode).pack(side='left')

        ttk.Button(theme_row1, text="Apply Theme", command=self.apply_theme_change,
                  bootstyle=INFO).pack(side='right')

        # Download settings
        download_frame = ttk.LabelFrame(self.settings_frame, text="Download Settings", padding=10)
        download_frame.pack(fill='x', padx=10, pady=(0, 10))

        # Default path
        path_row = ttk.Frame(download_frame)
        path_row.pack(fill='x', pady=(0, 10))

        ttk.Label(path_row, text="Default Download Path:").pack(side='left')
        self.default_path_var = ttk.StringVar(value=config.get('default_download_path'))
        path_entry = ttk.Entry(path_row, textvariable=self.default_path_var)
        path_entry.pack(side='left', fill='x', expand=True, padx=(10, 5))
        ttk.Button(path_row, text="Browse", command=self.browse_default_path,
                  bootstyle=SECONDARY).pack(side='right')

        # Quality settings
        quality_row = ttk.Frame(download_frame)
        quality_row.pack(fill='x', pady=(0, 10))

        ttk.Label(quality_row, text="Default Video Quality:").pack(side='left')
        self.default_quality_var = ttk.StringVar(value=config.get('default_quality', 'best'))
        quality_combo = ttk.Combobox(quality_row, textvariable=self.default_quality_var,
                                    values=list(config.get_video_qualities().keys()), state='readonly')
        quality_combo.pack(side='left', padx=(10, 20))

        ttk.Label(quality_row, text="Audio Quality:").pack(side='left')
        self.audio_quality_var = ttk.StringVar(value=config.get('audio_quality', '192'))
        audio_combo = ttk.Combobox(quality_row, textvariable=self.audio_quality_var,
                                  values=list(config.get_audio_qualities().keys()), state='readonly')
        audio_combo.pack(side='left', padx=(10, 0))

        # Advanced settings
        advanced_frame = ttk.LabelFrame(self.settings_frame, text="Advanced Settings", padding=10)
        advanced_frame.pack(fill='x', padx=10, pady=(0, 10))

        advanced_row1 = ttk.Frame(advanced_frame)
        advanced_row1.pack(fill='x', pady=(0, 10))

        ttk.Label(advanced_row1, text="Max Concurrent Downloads:").pack(side='left')
        self.max_downloads_var = ttk.IntVar(value=config.get('max_concurrent_downloads', 3))
        max_downloads_spin = ttk.Spinbox(advanced_row1, from_=1, to=10, textvariable=self.max_downloads_var, width=5)
        max_downloads_spin.pack(side='left', padx=(10, 20))

        self.notifications_var = ttk.BooleanVar(value=config.get('notification_enabled', True))
        ttk.Checkbutton(advanced_row1, text="Enable Notifications",
                       variable=self.notifications_var).pack(side='left')

        # Save settings button
        ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings,
                  bootstyle=SUCCESS).pack(pady=20)

    def create_about_tab(self):
        """Create about tab"""
        self.about_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.about_frame, text="About")

        # Main content
        content_frame = ttk.Frame(self.about_frame)
        content_frame.pack(expand=True, fill='both', padx=20, pady=20)

        # Title
        title_label = ttk.Label(content_frame, text="Enhanced YouTube Downloader",
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))

        # Version info
        version_label = ttk.Label(content_frame, text="Version 2.0 - Enhanced Edition",
                                 font=('Arial', 12))
        version_label.pack(pady=(0, 20))

        # Features
        features_frame = ttk.LabelFrame(content_frame, text="Features", padding=15)
        features_frame.pack(fill='x', pady=(0, 20))

        features_text = """
• Download videos in multiple formats (MP4, WebM, MKV)
• Download audio in various formats (MP3, AAC, OGG, WAV, M4A)
• Quality selection for both video and audio
• Playlist support with individual video selection
• Download history with search and statistics
• Multiple theme support with dark mode
• Progress tracking with speed information
• Queue management for batch downloads
• Subtitle download support
• Drag & drop URL support
• Desktop notifications
        """.strip()

        features_label = ttk.Label(features_frame, text=features_text, justify='left')
        features_label.pack(anchor='w')

        # Credits
        credits_frame = ttk.LabelFrame(content_frame, text="Credits", padding=15)
        credits_frame.pack(fill='x', pady=(0, 20))

        credits_text = """
Original Author: Zied Boughdir
Enhanced by: Zinzied
Libraries: yt-dlp, ttkbootstrap, tkinter, PIL, requests
        """.strip()

        credits_label = ttk.Label(credits_frame, text=credits_text, justify='left')
        credits_label.pack(anchor='w')

        # System Requirements
        requirements_frame = ttk.LabelFrame(content_frame, text="System Requirements", padding=15)
        requirements_frame.pack(fill='x', pady=(0, 20))

        # Check FFmpeg status
        ffmpeg_status = "✅ Installed" if self._check_ffmpeg() else "❌ Not Found"
        requirements_text = f"""
FFmpeg: {ffmpeg_status}
Python: ✅ {os.sys.version.split()[0]}
        """.strip()

        requirements_label = ttk.Label(requirements_frame, text=requirements_text, justify='left')
        requirements_label.pack(anchor='w')

        if not self._check_ffmpeg():
            ffmpeg_help_frame = ttk.Frame(requirements_frame)
            ffmpeg_help_frame.pack(fill='x', pady=(10, 0))

            ttk.Label(ffmpeg_help_frame, text="FFmpeg is required for audio conversion and high-quality video downloads.",
                     foreground='red').pack(anchor='w')

            buttons_frame = ttk.Frame(ffmpeg_help_frame)
            buttons_frame.pack(anchor='w', pady=(5, 0))

            ttk.Button(buttons_frame, text="Install FFmpeg Guide",
                      command=self.show_ffmpeg_guide, bootstyle=WARNING).pack(side='left', padx=(0, 10))

            ttk.Button(buttons_frame, text="Auto Install FFmpeg",
                      command=self.auto_install_ffmpeg, bootstyle=SUCCESS).pack(side='left')

        # Links
        links_frame = ttk.Frame(content_frame)
        links_frame.pack(fill='x')

        ttk.Button(links_frame, text="GitHub Repository",
                  command=lambda: webbrowser.open("https://github.com/zinzied/Youtube-downloader"),
                  bootstyle=INFO).pack(side='left', padx=(0, 10))

        ttk.Button(links_frame, text="Report Issues",
                  command=lambda: webbrowser.open("https://github.com/zinzied/Youtube-downloader/issues"),
                  bootstyle=WARNING).pack(side='left')

    # Event binding methods
    def bind_events(self):
        """Bind events"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.url_entry.bind('<Return>', lambda e: self.get_video_info())
        self.search_entry.bind('<Return>', lambda e: self.search_history())

    def on_closing(self):
        """Handle application closing"""
        # Save window geometry
        config.set('window_geometry', self.root.geometry())

        # Stop all downloads
        for stop_event in self.stop_events.values():
            stop_event.set()

        # Close application
        self.root.destroy()

    # Utility methods
    def on_drop(self, event):
        """Handle drag and drop"""
        self.url_entry.delete(0, END)
        self.url_entry.insert(0, event.data.strip())

    def clear_url(self):
        """Clear URL entry"""
        self.url_entry.delete(0, END)
        self.clear_video_info()

    def clear_video_info(self):
        """Clear video information display"""
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, END)
        self.info_text.config(state='disabled')
        self.thumbnail_label.config(image='', text="No thumbnail")
        self.playlist_info = None

    def browse_path(self):
        """Browse for download path"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            config.set('last_used_path', path)

    def browse_default_path(self):
        """Browse for default download path"""
        path = filedialog.askdirectory(initialdir=self.default_path_var.get())
        if path:
            self.default_path_var.set(path)

    def update_quality_options(self, event=None):
        """Update quality options based on selected format"""
        format_type = self.format_var.get()

        if format_type in ['mp3', 'aac', 'ogg', 'wav', 'm4a']:
            # Audio format - show audio qualities
            qualities = config.get_audio_qualities()
        else:
            # Video format - show video qualities
            qualities = config.get_video_qualities()

        self.quality_combo.config(values=list(qualities.keys()))
        if self.quality_var.get() not in qualities:
            self.quality_var.set('best')

    def show_notification(self, title, message):
        """Show desktop notification"""
        if config.get('notification_enabled', True):
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_icon=None,
                    timeout=10,
                )
            except Exception:
                pass  # Notification failed, continue silently

    # Video info methods
    def get_video_info(self):
        """Get video information from URL"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return

        # Clear previous info
        self.clear_video_info()

        # Show loading message
        self.info_text.config(state='normal')
        self.info_text.insert(END, "Loading video information...")
        self.info_text.config(state='disabled')

        # Get info in separate thread
        thread = threading.Thread(target=self._get_video_info_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def _get_video_info_thread(self, url):
        """Get video info in separate thread"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Check if it's a playlist
                if 'entries' in info:
                    self.playlist_info = info
                    self._display_playlist_info(info)
                else:
                    self._display_video_info(info)

        except Exception as e:
            self.root.after(0, lambda: self._show_info_error(str(e)))

    def _display_video_info(self, info):
        """Display single video information"""
        def update_ui():
            self.info_text.config(state='normal')
            self.info_text.delete(1.0, END)

            # Format info text
            info_text = f"Title: {info.get('title', 'Unknown')}\n"
            info_text += f"Duration: {self._format_duration(info.get('duration', 0))}\n"
            info_text += f"Uploader: {info.get('uploader', 'Unknown')}\n"
            info_text += f"View Count: {info.get('view_count', 'Unknown'):,}\n" if info.get('view_count') else ""
            info_text += f"Upload Date: {info.get('upload_date', 'Unknown')}\n"

            # Add description if available
            description = info.get('description', '')
            if description:
                info_text += f"\nDescription:\n{description[:200]}{'...' if len(description) > 200 else ''}"

            self.info_text.insert(1.0, info_text)
            self.info_text.config(state='disabled')

            # Load thumbnail
            self._load_thumbnail(info.get('thumbnail'))

        self.root.after(0, update_ui)

    def _display_playlist_info(self, info):
        """Display playlist information"""
        def update_ui():
            self.info_text.config(state='normal')
            self.info_text.delete(1.0, END)

            # Format playlist info
            entries = info.get('entries', [])
            info_text = f"Playlist: {info.get('title', 'Unknown')}\n"
            info_text += f"Total Videos: {len(entries)}\n"
            info_text += f"Uploader: {info.get('uploader', 'Unknown')}\n\n"
            info_text += "Videos in playlist:\n"

            for i, entry in enumerate(entries[:10], 1):  # Show first 10
                if entry:
                    title = entry.get('title', 'Unknown')
                    duration = self._format_duration(entry.get('duration', 0))
                    info_text += f"{i}. {title} ({duration})\n"

            if len(entries) > 10:
                info_text += f"... and {len(entries) - 10} more videos"

            self.info_text.insert(1.0, info_text)
            self.info_text.config(state='disabled')

            # Load playlist thumbnail
            self._load_thumbnail(info.get('thumbnail'))

        self.root.after(0, update_ui)

    def _show_info_error(self, error_msg):
        """Show error in info display"""
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, END)
        self.info_text.insert(1.0, f"Error loading video information:\n{error_msg}")
        self.info_text.config(state='disabled')

    def _load_thumbnail(self, thumbnail_url):
        """Load and display thumbnail"""
        if not thumbnail_url:
            return

        def load_thumb():
            try:
                response = requests.get(thumbnail_url, timeout=10)
                if response.status_code == 200:
                    image = Image.open(io.BytesIO(response.content))
                    image = image.resize((120, 90), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)

                    def update_thumb():
                        self.thumbnail_label.config(image=photo, text="")
                        self.thumbnail_label.image = photo  # Keep reference

                    self.root.after(0, update_thumb)
            except Exception:
                pass  # Thumbnail loading failed, continue without it

        thread = threading.Thread(target=load_thumb)
        thread.daemon = True
        thread.start()

    def _format_duration(self, seconds):
        """Format duration in seconds to readable format"""
        if not seconds:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    # Queue management methods
    def add_to_queue(self):
        """Add URL to download queue"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return

        # Check if it's a playlist and handle accordingly
        if self.playlist_info and self.playlist_var.get():
            self._add_playlist_to_queue()
        else:
            self._add_single_to_queue(url)

        self.clear_url()
        self.update_queue_display()

    def _add_single_to_queue(self, url):
        """Add single video to queue"""
        queue_item = {
            'url': url,
            'type': 'single',
            'format': self.format_var.get(),
            'quality': self.quality_var.get(),
            'path': self.path_var.get(),
            'subtitles': self.subtitle_var.get(),
            'status': 'queued'
        }
        self.download_queue.append(queue_item)

    def _add_playlist_to_queue(self):
        """Add playlist videos to queue"""
        if not self.playlist_info:
            return

        entries = self.playlist_info.get('entries', [])
        for entry in entries:
            if entry:  # Skip None entries
                queue_item = {
                    'url': entry.get('webpage_url', entry.get('url')),
                    'type': 'playlist',
                    'title': entry.get('title', 'Unknown'),
                    'format': self.format_var.get(),
                    'quality': self.quality_var.get(),
                    'path': self.path_var.get(),
                    'subtitles': self.subtitle_var.get(),
                    'status': 'queued',
                    'playlist_title': self.playlist_info.get('title', 'Unknown Playlist')
                }
                self.download_queue.append(queue_item)

    def remove_from_queue(self):
        """Remove selected item from queue"""
        selection = self.queue_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.download_queue):
                self.download_queue.pop(index)
                self.update_queue_display()

    def clear_queue(self):
        """Clear all items from queue"""
        if messagebox.askyesno("Confirm", "Clear all items from queue?"):
            self.download_queue.clear()
            self.update_queue_display()

    def update_queue_display(self):
        """Update queue display"""
        self.queue_listbox.delete(0, END)

        for i, item in enumerate(self.download_queue):
            title = item.get('title', item['url'][:50] + '...' if len(item['url']) > 50 else item['url'])
            format_quality = f"{item['format'].upper()}"
            if item['quality'] != 'best':
                format_quality += f" ({item['quality']})"

            status = item['status'].title()
            display_text = f"{i+1}. {title} - {format_quality} [{status}]"
            self.queue_listbox.insert(END, display_text)

        # Update status
        self.queue_status_var.set(f"{len(self.download_queue)} items")

    # Download methods
    def start_download(self):
        """Start downloading from queue"""
        if not self.download_queue:
            messagebox.showinfo("Info", "Queue is empty. Add some URLs first.")
            return

        # Start download thread
        thread = threading.Thread(target=self._process_download_queue)
        thread.daemon = True
        thread.start()

    def _process_download_queue(self):
        """Process download queue"""
        max_concurrent = config.get('max_concurrent_downloads', 3)

        while self.download_queue:
            # Check how many downloads are currently active
            active_downloads = len([d for d in self.current_downloads.values() if d.get('active', False)])

            if active_downloads < max_concurrent:
                # Get next item from queue
                item = None
                for i, queue_item in enumerate(self.download_queue):
                    if queue_item['status'] == 'queued':
                        item = queue_item
                        item['status'] = 'downloading'
                        break

                if item:
                    # Start download for this item
                    download_id = f"download_{len(self.current_downloads)}"
                    self.stop_events[download_id] = threading.Event()
                    self.current_downloads[download_id] = {'item': item, 'active': True}

                    # Update UI
                    self.root.after(0, self.update_queue_display)

                    # Start download thread
                    thread = threading.Thread(target=self._download_single_item, args=(item, download_id))
                    thread.daemon = True
                    thread.start()

            # Wait a bit before checking again
            threading.Event().wait(1)

    def _download_single_item(self, item, download_id):
        """Download a single item"""
        try:
            # Update current download display
            title = item.get('title', item['url'][:50])
            self.root.after(0, lambda: self.current_download_label.config(text=f"Downloading: {title}"))

            # Prepare yt-dlp options
            ydl_opts = self._prepare_ydl_options(item, download_id)

            # Download
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(item['url'], download=False)
                filename = ydl.prepare_filename(info)

                # Download the file
                ydl.download([item['url']])

                # Add to history
                self._add_to_history(item, info, filename)

                # Update status
                item['status'] = 'completed'
                self.root.after(0, lambda: self.show_notification("Download Complete", f"Downloaded: {info.get('title', 'Unknown')}"))

        except Exception as e:
            if self.stop_events[download_id].is_set():
                item['status'] = 'stopped'
                self.root.after(0, lambda: self.show_notification("Download Stopped", "Download was stopped by user"))
            else:
                item['status'] = 'failed'
                error_msg = str(e)
                self.root.after(0, lambda: self.show_notification("Download Failed", f"Error: {error_msg}"))
                self.root.after(0, lambda: messagebox.showerror("Download Error", f"Failed to download:\n{error_msg}"))

        finally:
            # Clean up
            self.current_downloads[download_id]['active'] = False
            if item in self.download_queue:
                self.download_queue.remove(item)

            # Update UI
            self.root.after(0, self.update_queue_display)
            self.root.after(0, lambda: self.current_download_label.config(text="No active downloads"))
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.progress_label_var.set("0.00%"))
            self.root.after(0, lambda: self.speed_label_var.set(""))

    def _prepare_ydl_options(self, item, download_id):
        """Prepare yt-dlp options for download"""
        ydl_opts = {
            'outtmpl': os.path.join(item['path'], '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: self._progress_hook(d, download_id)],
        }

        format_type = item['format']
        quality = item['quality']

        # Check if ffmpeg is available
        ffmpeg_available = self._check_ffmpeg()

        if format_type in ['mp3', 'aac', 'ogg', 'wav', 'm4a']:
            # Audio format
            if ffmpeg_available:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type,
                    'preferredquality': quality if quality != 'best' else '192',
                }]
            else:
                # Fallback to best audio format available without conversion
                ydl_opts['format'] = 'bestaudio/best'
                messagebox.showwarning("FFmpeg Not Found",
                    "FFmpeg is not installed. Audio will be downloaded in its original format.\n"
                    "To enable audio conversion, please install FFmpeg.")
        else:
            # Video format
            if ffmpeg_available:
                if quality == 'best':
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                elif quality == 'worst':
                    ydl_opts['format'] = 'worstvideo+worstaudio/worst'
                else:
                    ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'
            else:
                # Fallback to single file formats that don't require merging
                if quality == 'best':
                    ydl_opts['format'] = 'best'
                elif quality == 'worst':
                    ydl_opts['format'] = 'worst'
                else:
                    ydl_opts['format'] = f'best[height<={quality}]'
                messagebox.showwarning("FFmpeg Not Found",
                    "FFmpeg is not installed. Video quality may be limited.\n"
                    "To enable high-quality video downloads, please install FFmpeg.")

        # Add subtitle options
        if item.get('subtitles', False):
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = config.get('subtitle_languages', ['en'])

        return ydl_opts

    def _check_ffmpeg(self):
        """Check if ffmpeg is available"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def show_ffmpeg_guide(self):
        """Show FFmpeg installation guide"""
        guide_window = ttk.Toplevel(self.root)
        guide_window.title("FFmpeg Installation Guide")
        guide_window.geometry("600x500")
        guide_window.resizable(True, True)

        # Create scrollable text widget
        text_frame = ttk.Frame(guide_window)
        text_frame.pack(fill='both', expand=True, padx=20, pady=20)

        text_widget = Text(text_frame, wrap='word', font=('Arial', 10))
        scrollbar = Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        guide_text = """FFmpeg Installation Guide

FFmpeg is required for:
• Converting audio to MP3, AAC, OGG formats
• Merging high-quality video and audio streams
• Downloading videos in specific qualities

WINDOWS INSTALLATION:

Method 1: Using Chocolatey (Recommended)
1. Install Chocolatey package manager from: https://chocolatey.org/install
2. Open Command Prompt as Administrator
3. Run: choco install ffmpeg
4. Restart the application

Method 2: Manual Installation
1. Go to: https://ffmpeg.org/download.html
2. Click "Windows" and download from gyan.dev or BtbN
3. Extract the zip file to C:\\ffmpeg
4. Add C:\\ffmpeg\\bin to your system PATH:
   - Press Win+R, type "sysdm.cpl", press Enter
   - Click "Environment Variables"
   - Under "System Variables", find "Path" and click "Edit"
   - Click "New" and add: C:\\ffmpeg\\bin
   - Click OK on all dialogs
5. Restart Command Prompt and this application

Method 3: Using Winget (Windows 10/11)
1. Open Command Prompt
2. Run: winget install ffmpeg
3. Restart the application

VERIFICATION:
After installation, open Command Prompt and type: ffmpeg -version
You should see version information if installed correctly.

TROUBLESHOOTING:
• Make sure to restart the application after installing FFmpeg
• If PATH is not working, try placing ffmpeg.exe in the same folder as this application
• For permission issues, run Command Prompt as Administrator

Without FFmpeg:
• Audio downloads will be in original format (usually M4A or WEBM)
• Video downloads will be limited to single-file formats
• Some quality options may not be available
"""

        text_widget.insert(1.0, guide_text)
        text_widget.config(state='disabled')

        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Buttons
        button_frame = ttk.Frame(guide_window)
        button_frame.pack(fill='x', padx=20, pady=(0, 20))

        ttk.Button(button_frame, text="Open FFmpeg Website",
                  command=lambda: webbrowser.open("https://ffmpeg.org/download.html"),
                  bootstyle=INFO).pack(side='left', padx=(0, 10))

        ttk.Button(button_frame, text="Check Again",
                  command=lambda: self.check_ffmpeg_and_update(guide_window),
                  bootstyle=SUCCESS).pack(side='left', padx=(0, 10))

        ttk.Button(button_frame, text="Close",
                  command=guide_window.destroy,
                  bootstyle=SECONDARY).pack(side='right')

    def check_ffmpeg_and_update(self, parent_window=None):
        """Check FFmpeg status and update UI"""
        if self._check_ffmpeg():
            messagebox.showinfo("Success", "FFmpeg is now installed and available!", parent=parent_window)
            if parent_window:
                parent_window.destroy()
        else:
            messagebox.showwarning("Not Found", "FFmpeg is still not found. Please check the installation.", parent=parent_window)

    def auto_install_ffmpeg(self):
        """Attempt to automatically install FFmpeg"""
        if messagebox.askyesno("Install FFmpeg",
                              "This will attempt to install FFmpeg automatically using system package managers.\n\n"
                              "Do you want to continue?"):

            # Show progress dialog
            progress_window = ttk.Toplevel(self.root)
            progress_window.title("Installing FFmpeg")
            progress_window.geometry("400x200")
            progress_window.resizable(False, False)

            # Center the window
            progress_window.transient(self.root)
            progress_window.grab_set()

            # Progress content
            ttk.Label(progress_window, text="Installing FFmpeg...",
                     font=('Arial', 12, 'bold')).pack(pady=20)

            progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
            progress_bar.pack(pady=10, padx=20, fill='x')
            progress_bar.start()

            status_label = ttk.Label(progress_window, text="Checking package managers...")
            status_label.pack(pady=10)

            # Run installation in separate thread
            def install_thread():
                try:
                    import subprocess
                    success = False

                    # Update status
                    self.root.after(0, lambda: status_label.config(text="Checking for Chocolatey..."))

                    # Try Chocolatey first
                    try:
                        result = subprocess.run(['choco', '--version'],
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            self.root.after(0, lambda: status_label.config(text="Installing via Chocolatey..."))
                            result = subprocess.run(['choco', 'install', 'ffmpeg', '-y'],
                                                  capture_output=True, text=True, timeout=300)
                            if result.returncode == 0:
                                success = True
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                    if not success:
                        # Try Winget
                        self.root.after(0, lambda: status_label.config(text="Checking for Winget..."))
                        try:
                            result = subprocess.run(['winget', '--version'],
                                                  capture_output=True, text=True, timeout=10)
                            if result.returncode == 0:
                                self.root.after(0, lambda: status_label.config(text="Installing via Winget..."))
                                result = subprocess.run(['winget', 'install', 'ffmpeg'],
                                                      capture_output=True, text=True, timeout=300)
                                if result.returncode == 0:
                                    success = True
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            pass

                    # Check if installation was successful
                    if success and self._check_ffmpeg():
                        self.root.after(0, lambda: self._show_install_success(progress_window))
                    else:
                        self.root.after(0, lambda: self._show_install_failure(progress_window))

                except Exception as e:
                    self.root.after(0, lambda: self._show_install_error(progress_window, str(e)))

            # Start installation thread
            thread = threading.Thread(target=install_thread)
            thread.daemon = True
            thread.start()

    def _show_install_success(self, progress_window):
        """Show installation success"""
        progress_window.destroy()
        messagebox.showinfo("Success",
                           "FFmpeg has been installed successfully!\n\n"
                           "You can now download videos in high quality and convert audio formats.")

    def _show_install_failure(self, progress_window):
        """Show installation failure"""
        progress_window.destroy()
        if messagebox.askyesno("Installation Failed",
                              "Automatic installation failed. This might be because:\n"
                              "• No package manager (Chocolatey/Winget) is installed\n"
                              "• Administrator privileges are required\n"
                              "• Network connectivity issues\n\n"
                              "Would you like to see the manual installation guide?"):
            self.show_ffmpeg_guide()

    def _show_install_error(self, progress_window, error_msg):
        """Show installation error"""
        progress_window.destroy()
        messagebox.showerror("Installation Error",
                           f"An error occurred during installation:\n{error_msg}\n\n"
                           "Please try the manual installation method.")

    def _progress_hook(self, d, download_id):
        """Progress hook for yt-dlp"""
        if self.stop_events[download_id].is_set():
            raise youtube_dl.utils.DownloadError("Download stopped by user.")

        if d['status'] == 'downloading':
            total_size = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)

            if total_size:
                percentage = (downloaded / total_size) * 100
                self.root.after(0, lambda: self.progress_var.set(percentage))
                self.root.after(0, lambda: self.progress_label_var.set(f"{percentage:.1f}%"))

            # Show download speed
            speed = d.get('speed')
            if speed:
                speed_text = f"{speed / 1024 / 1024:.1f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.1f} KB/s"
                self.root.after(0, lambda: self.speed_label_var.set(speed_text))

    def _add_to_history(self, item, info, filename):
        """Add download to history"""
        try:
            file_size = os.path.getsize(filename) if os.path.exists(filename) else None

            history.add_download(
                url=item['url'],
                title=info.get('title', 'Unknown'),
                format=item['format'],
                quality=item['quality'],
                file_path=filename,
                file_size=file_size,
                duration=self._format_duration(info.get('duration', 0)),
                thumbnail_url=info.get('thumbnail'),
                metadata={
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'description': info.get('description', '')[:500]  # Limit description length
                }
            )
        except Exception as e:
            print(f"Error adding to history: {e}")

    def stop_download(self):
        """Stop current downloads"""
        for stop_event in self.stop_events.values():
            stop_event.set()

        # Update queue status
        for item in self.download_queue:
            if item['status'] == 'downloading':
                item['status'] = 'stopped'

        self.update_queue_display()
        messagebox.showinfo("Info", "Download stop signal sent.")

    def pause_all_downloads(self):
        """Pause all downloads (placeholder for future implementation)"""
        messagebox.showinfo("Info", "Pause functionality will be implemented in a future version.")

    # History management methods
    def refresh_history(self):
        """Refresh download history display"""
        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Get downloads from history
            downloads = history.get_downloads(limit=100)

            for download in downloads:
                # Format file size
                size_str = "Unknown"
                if download['file_size']:
                    size_mb = download['file_size'] / (1024 * 1024)
                    size_str = f"{size_mb:.1f} MB"

                # Format date
                date_str = download['download_date'][:16] if download['download_date'] else "Unknown"

                # Check if file still exists
                status = "Available" if history.file_exists(download['file_path']) else "Missing"

                self.history_tree.insert('', 'end', values=(
                    download['title'][:50] + '...' if len(download['title']) > 50 else download['title'],
                    download['format'].upper(),
                    download['quality'],
                    size_str,
                    date_str,
                    status
                ))

            # Update statistics
            self.update_statistics()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history: {e}")

    def search_history(self):
        """Search download history"""
        search_term = self.search_var.get().strip()

        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Get filtered downloads
            downloads = history.get_downloads(limit=100, search_term=search_term if search_term else None)

            for download in downloads:
                # Format file size
                size_str = "Unknown"
                if download['file_size']:
                    size_mb = download['file_size'] / (1024 * 1024)
                    size_str = f"{size_mb:.1f} MB"

                # Format date
                date_str = download['download_date'][:16] if download['download_date'] else "Unknown"

                # Check if file still exists
                status = "Available" if history.file_exists(download['file_path']) else "Missing"

                self.history_tree.insert('', 'end', values=(
                    download['title'][:50] + '...' if len(download['title']) > 50 else download['title'],
                    download['format'].upper(),
                    download['quality'],
                    size_str,
                    date_str,
                    status
                ))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to search history: {e}")

    def update_statistics(self):
        """Update statistics display"""
        try:
            stats = history.get_statistics()

            stats_text = f"Total Downloads: {stats['total_downloads']} | "
            stats_text += f"Total Size: {stats['total_size'] / (1024**3):.2f} GB | "
            stats_text += f"Recent (7 days): {stats['recent_downloads']}"

            self.stats_label.config(text=stats_text)

        except Exception as e:
            self.stats_label.config(text="Error loading statistics")

    def open_selected_file(self):
        """Open selected file from history"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file from history")
            return

        try:
            # Get selected item index
            item = selection[0]
            index = self.history_tree.index(item)

            # Get corresponding download record
            downloads = history.get_downloads(limit=100)
            if index < len(downloads):
                file_path = downloads[index]['file_path']
                if os.path.exists(file_path):
                    os.startfile(file_path)  # Windows
                else:
                    messagebox.showerror("Error", "File not found. It may have been moved or deleted.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")

    def open_file_folder(self):
        """Open folder containing selected file"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file from history")
            return

        try:
            # Get selected item index
            item = selection[0]
            index = self.history_tree.index(item)

            # Get corresponding download record
            downloads = history.get_downloads(limit=100)
            if index < len(downloads):
                file_path = downloads[index]['file_path']
                folder_path = os.path.dirname(file_path)
                if os.path.exists(folder_path):
                    os.startfile(folder_path)  # Windows
                else:
                    messagebox.showerror("Error", "Folder not found.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")

    def delete_history_entry(self):
        """Delete selected history entry"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an entry to delete")
            return

        if messagebox.askyesno("Confirm", "Delete selected history entry?"):
            try:
                # Get selected item index
                item = selection[0]
                index = self.history_tree.index(item)

                # Get corresponding download record
                downloads = history.get_downloads(limit=100)
                if index < len(downloads):
                    download_id = downloads[index]['id']
                    history.delete_download(download_id)
                    self.refresh_history()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete entry: {e}")

    def clear_history(self):
        """Clear all download history"""
        if messagebox.askyesno("Confirm", "Clear all download history? This cannot be undone."):
            try:
                history.clear_history()
                self.refresh_history()
                messagebox.showinfo("Success", "History cleared successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {e}")

    # Settings methods
    def toggle_dark_mode(self):
        """Toggle dark mode"""
        dark_mode = self.dark_mode_var.get()
        config.set('dark_mode', dark_mode)

        # Apply theme change
        self.apply_theme_change()

    def apply_theme_change(self):
        """Apply theme changes"""
        theme_name = self.theme_var.get()
        dark_mode = self.dark_mode_var.get()

        # Save settings
        config.set('theme', theme_name)
        config.set('dark_mode', dark_mode)

        # Apply new theme
        if dark_mode:
            dark_themes = ['darkly', 'cyborg', 'vapor', 'superhero', 'solar']
            if theme_name not in dark_themes:
                theme_name = 'darkly'

        try:
            self.style = ttk.Style(theme_name)
            messagebox.showinfo("Success", "Theme applied successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply theme: {e}")

    def save_settings(self):
        """Save all settings"""
        try:
            # Save all configuration values
            config.set('default_download_path', self.default_path_var.get())
            config.set('default_quality', self.default_quality_var.get())
            config.set('audio_quality', self.audio_quality_var.get())
            config.set('max_concurrent_downloads', self.max_downloads_var.get())
            config.set('notification_enabled', self.notifications_var.get())

            messagebox.showinfo("Success", "Settings saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def run(self):
        """Run the application"""
        self.root.mainloop()


# Main application entry point
def main():
    """Main function to run the application"""
    try:
        app = YouTubeDownloaderApp()
        app.run()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Application failed to start: {e}")


if __name__ == "__main__":
    main()
