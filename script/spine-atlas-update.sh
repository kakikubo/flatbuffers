#!/bin/sh

# move to repository top dir
cd "`dirname $0`/../"

TexturePacker=/usr/local/bin/TexturePacker
spine_dir=bundled/preload/files/spine
options="--texture-format png --format spine --trim-mode None"

# character faces
character_dirs=`find $spine_dir/face -type d -depth 1`
for character_dir in $character_dirs; do
  character=`basename $character_dir`
  dir=$spine_dir/face
  echo $character_dir
  find $character_dir -name '*.png' | xargs $TexturePacker --sheet $dir/$character.png --data $dir/$character.atlas $options
  if [ $? -ne 0 ]; then
    echo "fail to create texture: $character_dir"
    exit 1
  fi
done

# weapons
weapon_dir=$spine_dir/weapon
echo $weapon_dir
find $weapon_dir -name '*.png' | xargs $TexturePacker --sheet $spine_dir/weapon.png --data $spine_dir/weapon.atlas $options
if [ $? -ne 0 ]; then
  echo "fail to create texture: $weapon_dir"
  exit 1
fi

exit 0
