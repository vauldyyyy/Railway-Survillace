#!/bin/bash
# youtube_mass_download.sh
# RailGuard — Tier 3 Mass YouTube Data Harvester (Bash version)

# Use associative array for queries (Requires Bash 4.0+)
declare -A QUERIES=(
  ["night_01"]="Indian railway station night CCTV footage"
  ["night_02"]="train platform night surveillance camera India"
  ["night_03"]="railway station late night footage 4K"
  ["night_04"]="metro station night platform camera"
  ["night_05"]="railway junction night operations India"
  
  ["fog_01"]="railway platform heavy rain monsoon India"
  ["fog_02"]="train station fog India visibility"
  ["fog_03"]="railway platform flood India footage"
  ["fog_04"]="train arriving fog station footage"
  
  ["crowd_01"]="Mumbai CST station rush hour crowd"
  ["crowd_02"]="Howrah station crowd stampede"
  ["crowd_03"]="New Delhi railway station overcrowding"
  ["crowd_04"]="Indian railway station peak hour footage"
  ["crowd_05"]="train platform crowd surge emergency"
  
  ["intrusion_01"]="person trespassing railway track India caught CCTV"
  ["intrusion_02"]="person falls railway track India"
  ["intrusion_03"]="railway track trespassing accident India"
  ["intrusion_04"]="cow animal on railway track India"
  ["intrusion_05"]="child on railway track India CCTV"
  
  ["object_01"]="debris object on railway track India"
  ["object_02"]="train hits obstacle on track footage"
  ["object_03"]="fallen tree railway track India"
  ["object_04"]="plastic bag on railway track"
  ["object_05"]="stone on railway track India"
  
  ["fire_01"]="train fire smoke India railway"
  ["fire_02"]="railway station fire emergency India"
  ["fire_03"]="train coach fire India footage"
  
  ["baggage_01"]="abandoned bag suspicious railway station India"
  ["baggage_02"]="unattended luggage railway platform India"
  ["baggage_03"]="suspicious package train station India"

  ["diversity_01"]="Tokyo train station platform overhead CCTV"
  ["diversity_02"]="London Underground platform surveillance footage"
  ["diversity_03"]="European railway station CCTV footage"
  ["diversity_04"]="elevated railway track aerial view"
  ["diversity_05"]="rural railway crossing India footage"
  ["diversity_06"]="metro train platform camera angle"
  ["diversity_07"]="subway station security camera footage"

  ["negative_01"]="empty railway platform no people timelapse"
  ["negative_02"]="train arriving empty station footage"
  ["negative_03"]="railway track clear no obstacles"
  ["negative_04"]="train station normal operations timelapse"
  ["negative_05"]="platform normal passengers walking footage"
)

OUT_BASE="datasets/youtube_raw"
mkdir -p "$OUT_BASE"

# Alphabetical sorting for predictable execution
mapfile -d '' sorted_keys < <(printf '%s\0' "${!QUERIES[@]}" | sort -z)

for key in "${sorted_keys[@]}"; do
  query="${QUERIES[$key]}"
  key_dir="$OUT_BASE/$key"
  mkdir -p "$key_dir"
  
  echo -e "\n⬇️  Downloading: $query"
  
  yt-dlp "ytsearch5:$query" \
    -f "best[height<=480][ext=mp4]" \
    -o "$key_dir/%(title)s.%(ext)s" \
    --no-playlist \
    --ignore-errors \
    --sleep-interval 3 \
    --max-sleep-interval 6
done

echo -e "\n✅ Download complete"
echo "📊 Run frame extraction next:"
echo "   python scripts/extract_all_frames.py"
