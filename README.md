# 📺 Easy Blocks Lazy Cuts Version

This Python script compiles a series of shows, bumpers, commercials, and promos into a single stitched video file with consistent formatting (720p/30fps), transitions. It's ideal for creating retro-style TV blocks or automated video compilations.

---

## 🔧 Features

- Automatically scans folders for content (Shows, Bumpers, Commercials, Promos)
- Normalizes all clips to 720p, 30fps, AAC audio
- Applies fade-in/out effects to shows
- Inserts bumpers and ads between show halves
- Ensures clip compatibility for fast or re-encoded FFmpeg concatenation
- Outputs a final, stitched `.mp4` video

---

## 📁 Folder Structure

Place your videos into the following folders relative to the script:

```
.
├── Bumpers/
├── Commercials/
├── Promos/
├── Shows/             # Show Folders In Here Only No Sub Folders
│   ├── Show1/         # Just Video Files In Here No Folders
│   └── Show2/         # Just Video Files In Here No Folders
├── Output/            # Final video gets saved here
├── Temp/              # Intermediate files go here
└── splitmkv.py
```

---

## ▶️ How to Run

### Requirements

Install dependencies:

```bash
pip install moviepy tqdm
```

Ensure `ffmpeg` and `ffprobe` are installed and accessible in your PATH.

### Run the Script

```bash
python splitmkv.py
```

It will:
1. Select up to 4 shows at random.
2. Process and split each show.
3. Insert bumpers and ads in between.
4. Output a stitched video as `Output/Final_Stitched_Show.mp4`.

---

## 🛠 Customization

- **Minimum duration for ad segments**: Change the sec= in def select_videos_for_duration(folders, min_duration_sec=180)
- **Video quality settings**: Modify FFmpeg parameters in `convert_to_720p_30fps()` or `concat_videos_ffmpeg()`.
- **Number of shows used**:  Change the number from 4 in the row selected_shows = random.sample(show_folders, min(len(show_folders), 4))
---

## 📝 Notes

- The script processes only `.mp4` and `.mkv` files by default.
- It skips incompatible clips or clips with unreadable metadata.
- It checks stream compatibility before deciding between stream-copy or re-encode concatenation.
- Must be in x264 format
---

## 📌 License

MIT License – feel free to use, modify, and distribute.
