Quantum Launcher 🚀
A sleek, AI-powered app launcher built in Python with PyQt5, designed to launch multiple apps and web links in one click. With a futuristic neon aesthetic (dark theme, cyan/pink accents), drag-and-drop link support, and persistent storage, Quantum Launcher is the ultimate productivity tool for coders and tech enthusiasts. Simplify your workflow with multi-app launching, pinned items, and a responsive GUI inspired by modern IDEs like VS Code.
Launch your workflow with neon-charged speed! ✨
Features

One-Click Launching: Open multiple applications (e.g., VS Code, Spotify, Notion) and web URLs (e.g., GitHub, YouTube) simultaneously.
Drag-and-Drop Links: Add custom web URLs or app shortcuts effortlessly.
Neon Aesthetic GUI: Dark theme with glowing cyan/pink accents, animations, and particle effects for a futuristic vibe.
Persistent Storage: Save links, pinned items, and recent apps across sessions using JSON or SQLite.
Multi-Selection: Select multiple apps/links with glowing checkboxes for batch operations.
Quick Search: Spotlight-style search to find apps and links instantly.
System Tray Integration: Minimize to tray for quick access.
Cross-Platform Potential: Windows-tested, with plans for macOS/Linux support.

Installation
Prerequisites

Python 3.8+
PyQt5
win32com (Windows only, for app detection)
PIL (Pillow, for image handling)
fuzzywuzzy (for search)

Setup

Clone the repository:git clone https://github.com/vamanbhanushali/quantum-launcher.git
cd quantum-launcher


Install dependencies:pip install -r requirements.txt


Run the app:python quantum_launcher.py



Windows Notes

Ensure app paths (e.g., Edge, VS Code) are accessible in your system’s PATH or specify full paths in the config.
Install python-Levenshtein for faster fuzzywuzzy search:pip install python-Levenshtein



Usage

Launch Apps/Links: Select apps or URLs via checkboxes, then click “Run” to open all at once.
Add Links: Drag-and-drop URLs or use the “Add Link” dialog to save custom web links.
Pin Favorites: Right-click items to pin them for quick access.
Search: Use the spotlight search bar to find apps/links by name or tag.
Customize: Tweak themes or animations in the settings panel.

Check out the demo video for a neon-powered walkthrough! 🚀
Contributing
We love contributions! To get started:

Fork the repo.
Create a feature branch (git checkout -b feature/neon-animation).
Commit changes (git commit -m "Add neon glow effect").
Push to your fork (git push origin feature/neon-animation).
Open a pull request.

Please follow the code of conduct and check issues for tasks.
Roadmap

macOS/Linux support
Cloud sync for links/pins
Customizable neon themes
Keyboard shortcuts for power users
Real-time resource monitoring

Troubleshooting

ModuleNotFoundError: Ensure all dependencies are installed (pip install -r requirements.txt).
System Tray Icon Missing: Verify a valid .ico file in the assets/ folder.
App Not Found: Check app paths in config.json or update your system PATH.

For more help, open an issue or DM @vamanbhanushali on Instagram.
License
MIT License – Free to use, modify, and share.
About
Built by @vamanbhanushali, a coder passionate about productivity tools, coding hacks, and automation scripts. Quantum Launcher combines Python’s power with a neon aesthetic to make your workflow faster and flashier. ✨
Star ⭐ the repo if you love it! Drop a ‘LAUNCH’ in the discussions to join the community.
