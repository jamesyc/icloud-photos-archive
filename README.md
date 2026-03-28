# photos-compress

Local scripts for exporting large videos from Apple Photos, transcoding them to smaller HEVC files, fixing metadata for re-import, and importing them back into Photos.

## Repo-ready workflow

1. Build or refresh a candidate CSV.
   Use [`1list_big_videos.py`](./1list_big_videos.py) to generate `big-videos.csv`.
   /opt/homebrew/bin/python3 1list_big_videos.py --min-mb 300

2. Export originals from Photos.
   Use [`2export_photos_originals.py`](./2export_photos_originals.py).
   /opt/homebrew/bin/python3 2export_photos_originals.py

3. Transcode the exported originals to HEVC.
   Use [`3transcode_photos_video.py`](./3transcode_photos_video.py).
   /opt/homebrew/bin/python3 3transcode_photos_video.py originals/
   INPUT_FILE.MOV -o repo/transcoded/INPUT_FILE.hevc.mov

   For all exported files in originals/:

   for f in originals/*; do
      base="$(basename "$f")"
      stem="${base%.*}"
      /opt/homebrew/bin/python3 3transcode_photos_video.py "$f" -o "transcoded/${stem}.hevc.mov"
   done

4. Fix metadata after ffmpeg with exiftool.
   Use [`4fix_metadata.py`](./4fix_metadata.py).
   This is the critical step. Without it, Photos imported the date but dropped metadata for GPS, etc
   /opt/homebrew/bin/python3 4fix_metadata.py

5. Test importing one fixed file into Photos.
   Use [`5import_one_to_photos.py`](./5import_one_to_photos.py).
   /opt/homebrew/bin/python3 5import_one_to_photos.py
   Don't import all at this point, that eats up iCloud space. Just import one to test.
   Verify in Photos before deleting originals.
     The checks that mattered were:
      - video plays
      - capture date preserved
      - GPS preserved
      - compressed file quality acceptable

6. Manually delete the originals in Photos.
   Use [`6delete_originals_helper.py`](./6delete_originals_helper.py) to open the next original and wait for manual deletion.
   Start from the first item:
   /opt/homebrew/bin/python3 6delete_originals_helper.py --reset
   After deleting that item manually in Photos:
   /opt/homebrew/bin/python3 6delete_originals_helper.py --advance

7. Use 5import_one_to_photos.py repeatedly.
   It imports one file from "modified" and moves it into "imported" folder on success.

## Important behavior

- Inputs live in `originals/`.
- Raw transcoded files live in `transcoded/`.
- Metadata-fixed files live in `modified/`.
- Successfully imported files are moved to `imported/`.
- Paths are resolved relative to this repo directory by default.

## Tool configuration

The scripts use [`config.py`](./config.py) and support environment overrides:

- `PHOTOS_COMPRESS_LIBRARY`
- `PHOTOS_COMPRESS_PYTHON`
- `PHOTOS_COMPRESS_FFMPEG`
- `PHOTOS_COMPRESS_FFPROBE`
- `PHOTOS_COMPRESS_PERL`
- `PHOTOS_COMPRESS_EXIFTOOL`

## Default encode settings

- HEVC / H.265 in `.mov`
- `30 fps`
- long edge capped at `1080`
- `CRF 20`
- `preset medium`
- audio copied
