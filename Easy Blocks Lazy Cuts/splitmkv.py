import os
import random
import subprocess
import re
import json
from pathlib import Path
from moviepy import VideoFileClip
from tqdm import tqdm

# Directories
SHOWS_DIR = Path("Shows")
BUMPERS_DIR = Path("Bumpers")
COMMERCIALS_DIR = Path("Commercials")
PROMOS_DIR = Path("Promos")
OUTPUT_DIR = Path("Output")
TMP_DIR = Path("Temp")
PROCESSED_DIR = TMP_DIR / "processed"

OUTPUT_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# Overlay setup for Shows
IMAGE_FOLDER = Path("Screenbug")
OVERLAY_IMAGE = next((f for f in IMAGE_FOLDER.glob("*.png")), None)
OVERLAY_PATH = IMAGE_FOLDER / OVERLAY_IMAGE if OVERLAY_IMAGE else None

VIDEO_EXTENSIONS = (".mp4", ".mkv")

def sanitize_filename(name):
    return re.sub(r'[^\w\.-]', '_', name)

def get_video_files(folder, extensions=VIDEO_EXTENSIONS):
    return [f for ext in extensions for f in Path(folder).glob(f"*{ext}")]

def get_video_properties(path):
    try:
        clip = VideoFileClip(str(path))
        w, h, fps = clip.size
        clip.close()
        return w, h, fps
    except Exception as e:
        print(f"Error reading video properties of {path}: {e}")
        return None, None, None

def get_video_duration(video_path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'format=duration', '-of', 'json', str(video_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    info = json.loads(result.stdout)
    return float(info['format']['duration'])

def overlay_screenbug(input_path, output_path, overlay_path):
    duration = get_video_duration(input_path)
    end_time = duration - 3
    filter_complex = (
        f"[1][0]scale2ref[img][vid];"
        f"[vid][img]overlay=enable='between(t,3,{end_time:.2f})'"
    )
    command = [
        'ffmpeg', '-y', '-i', str(input_path), '-i', str(overlay_path),
        '-filter_complex', filter_complex,
        '-preset', 'fast', '-codec:a', 'copy', str(output_path)
    ]
    subprocess.run(command, check=True)

def convert_to_720p_30fps(input_file, output_file):
    print(f"  Converting {input_file.name} to 720p 30fps AAC...")
    command = [
        "ffmpeg", "-y", "-i", str(input_file),
        "-vf", "scale=1280:720,fps=30", "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-af", "aformat=sample_fmts=fltp", str(output_file)
    ]
    subprocess.run(command, check=True)

def process_clip_if_needed(input_path):
    try:
        relative_path = input_path.relative_to(SHOWS_DIR) if SHOWS_DIR in input_path.parents else input_path
    except ValueError:
        relative_path = input_path

    safe_name = sanitize_filename(str(relative_path).replace(input_path.suffix, "_processed.mp4"))
    processed_file = PROCESSED_DIR / safe_name

    if processed_file.exists():
        print(f"Processed file exists: {processed_file}")
        return processed_file

    w, h, fps = get_video_properties(input_path)
    is_show_clip = any(input_path.match(f"{SHOWS_DIR}/**/*{ext}") for ext in VIDEO_EXTENSIONS)

    if is_show_clip:
        print(f"  Applying fade in/out for show clip: {input_path.name}")
        clip = VideoFileClip(str(input_path))
        duration = clip.duration
        clip.close()

        fade_duration = 0.5
        command = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", f"scale=1280:720,fps=30,fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration - fade_duration}:d={fade_duration}",
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-af", "aformat=sample_fmts=fltp", str(processed_file)
        ]
        subprocess.run(command, check=True)

        if processed_file.exists():
            print(f"Created processed show file with fade: {processed_file}")
            if OVERLAY_PATH and OVERLAY_PATH.exists():
                overlayed_file = processed_file.with_name("overlayed_" + processed_file.name)
                overlay_screenbug(processed_file, overlayed_file, OVERLAY_PATH)
                if overlayed_file.exists():
                    print(f"Applied overlay to: {overlayed_file}")
                    return overlayed_file
            return processed_file

    if input_path.parent in [BUMPERS_DIR, COMMERCIALS_DIR, PROMOS_DIR] or w != 1280 or h != 720 or round(fps) != 30:
        convert_to_720p_30fps(input_path, processed_file)
        if processed_file.exists():
            return processed_file
        return None

    return input_path

def select_videos_for_duration(folders, min_duration_sec=180):
    all_videos = []
    for folder in folders:
        all_videos.extend(get_video_files(folder))
    random.shuffle(all_videos)
    selected, total = [], 0
    for video in all_videos:
        try:
            clip = VideoFileClip(str(video))
            duration = clip.duration
            clip.close()
        except:
            duration = 0
        if total + duration <= min_duration_sec + 15:
            selected.append(video)
            total += duration
        if total >= min_duration_sec:
            break
    return selected

def generate_ffmpeg_list_file(video_paths, list_file_path):
    with open(list_file_path, "w", encoding="utf-8") as f:
        for path in video_paths:
            f.write(f"file '{path.resolve().as_posix()}'\n")

def concat_videos_ffmpeg(list_file_path, output_path):
    with open(list_file_path, "r", encoding="utf-8") as f:
        files = [line.strip().replace("file '", "").replace("'", "") for line in f.readlines()]
    inputs = []
    for file in files:
        inputs.extend(["-i", file])
    n = len(files)
    filter_complex = f"concat=n={n}:v=1:a=1[outv][outa]"
    command = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        str(output_path)
    ]
    subprocess.run(command, check=True)

def are_clips_compatible_for_stream_copy(video_paths):
    def get_stream_info(path):
        v = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name,width,height,r_frame_rate,pix_fmt",
                            "-of", "default=noprint_wrappers=1:nokey=1", path],
                           capture_output=True, text=True)
        video_info = v.stdout.strip().split('\n')
        a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                            "-show_entries", "stream=codec_name,sample_rate,channels",
                            "-of", "default=noprint_wrappers=1:nokey=1", path],
                           capture_output=True, text=True)
        audio_info = a.stdout.strip().split('\n')
        return video_info, audio_info

    if not video_paths:
        return False

    first_video_info, first_audio_info = get_stream_info(str(video_paths[0]))
    for path in video_paths[1:]:
        video_info, audio_info = get_stream_info(str(path))
        if video_info != first_video_info or audio_info != first_audio_info:
            return False
    return True

def process_all_shows():
    show_folders = [f for f in SHOWS_DIR.iterdir() if f.is_dir()]
    if not show_folders:
        print("❌ No show folders found.")
        return

    selected_shows = random.sample(show_folders, min(len(show_folders), 4))
    all_clips = []

    for i, show in enumerate(tqdm(selected_shows, desc="Processing selected shows")):
        video_files = get_video_files(show)
        if not video_files:
            print(f"⚠️ No video files found in {show.name}")
            continue

        chosen_file = random.choice(video_files)
        print(f"\n📺 Processing {show.name} - {chosen_file.name}")

        processed_full = process_clip_if_needed(chosen_file)
        if not processed_full:
            continue

        duration = get_video_duration(processed_full)
        midpoint = duration / 2

        first_half = TMP_DIR / f"{sanitize_filename(chosen_file.stem)}_part1.mp4"
        second_half = TMP_DIR / f"{sanitize_filename(chosen_file.stem)}_part2.mp4"

        subprocess.run(["ffmpeg", "-y", "-i", str(processed_full), "-t", f"{midpoint:.2f}", "-c", "copy", str(first_half)], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(processed_full), "-ss", f"{midpoint:.2f}", "-c", "copy", str(second_half)], check=True)

        all_clips.append(first_half)

        # Mid-show ads
        all_clips.append(process_clip_if_needed(random.choice(get_video_files(BUMPERS_DIR))))
        for ad in select_videos_for_duration([COMMERCIALS_DIR, PROMOS_DIR]):
            all_clips.append(process_clip_if_needed(ad))
        all_clips.append(process_clip_if_needed(random.choice(get_video_files(BUMPERS_DIR))))

        all_clips.append(second_half)

        # Post-show ads (except after last show)
        if i < len(selected_shows) - 1:
            all_clips.append(process_clip_if_needed(random.choice(get_video_files(BUMPERS_DIR))))
            for ad in select_videos_for_duration([COMMERCIALS_DIR, PROMOS_DIR]):
                all_clips.append(process_clip_if_needed(ad))
            all_clips.append(process_clip_if_needed(random.choice(get_video_files(BUMPERS_DIR))))

    # Final break
    all_clips.append(process_clip_if_needed(random.choice(get_video_files(BUMPERS_DIR))))
    for ad in select_videos_for_duration([COMMERCIALS_DIR, PROMOS_DIR]):
        all_clips.append(process_clip_if_needed(ad))

    final_list_file = TMP_DIR / "final_stitch_list.txt"
    generate_ffmpeg_list_file(all_clips, final_list_file)
    final_output_file = OUTPUT_DIR / "Final_Stitched_Show.mp4"

    if are_clips_compatible_for_stream_copy(all_clips):
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(final_list_file), "-c", "copy", str(final_output_file)], check=True)
    else:
        concat_videos_ffmpeg(final_list_file, final_output_file)

    print(f"✅ Done! Final file saved to: {final_output_file.resolve()}")

if __name__ == "__main__":
    process_all_shows()