import re
import subprocess
import argparse


def parse_exif_dump(path):
    """
    Parse an exiftool text dump into a dict of tag -> value.
    Lines expected in format: "Tag Name   : value".
    """
    tags = {}
    pattern = re.compile(r'^([^:]+?)\s*:\s*(.*)$')
    skip = {'exiftool version number', 'file name', 'directory',
            'file size', 'file permissions', 'error'}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            m = pattern.match(line)
            if not m:
                continue
            key, val = m.group(1).strip(), m.group(2).strip()
            if key.lower() in skip:
                continue
            tags[key] = val
    return tags


def is_model_tag(tag, new_iphone_data_val):
    """
    Identify tags related to iPhone/iOS model information.
    Keep model/version tags from new_iphone_data.
    """
    # Tag names containing 'model' or values containing 'iphone'
    if 'lens id' in tag.lower():
        return True
    if 'host computer' in tag.lower():
        return True
    if 'software' in tag.lower():
        return True
    if 'camera model name' in tag.lower():
        return True
    if 'profile copyright' in tag.lower():
        return True
    
    if 'iphone' in new_iphone_data_val.lower():
        return True
    return False


def build_exiftool_args(new_iphone_data_tags, old_iphone_data_tags):
    """
    Build exiftool args selecting model/version tags from new_iphone_data,
    and non-model tags from old_iphone_data when available.
    """
    args = []
    # Use all tags from new_iphone_data and old_iphone_data (union)
    all_tags = set(new_iphone_data_tags) | set(old_iphone_data_tags)
    for tag in sorted(all_tags):
        new_iphone_data_val = new_iphone_data_tags.get(tag)
        old_iphone_data_val = old_iphone_data_tags.get(tag)
        # Decide source
        if new_iphone_data_val is not None and is_model_tag(tag, new_iphone_data_val):
            use_val = new_iphone_data_val
        elif old_iphone_data_val is not None:
            use_val = old_iphone_data_val
        else:
            # fallback to new_iphone_data if old_iphone_data missing
            use_val = new_iphone_data_val
        # Build safe argument
        safe_val = use_val.replace('"', '\\"')
        tag_key = tag.replace(' ', '')
        args.append(f"-{tag_key}={safe_val}")
    return args


def main():
    parser = argparse.ArgumentParser(
        description="Apply EXIF metadata: keep model tags from new_iphone_data, others from old_iphone_data."
    )
    parser.add_argument('image', help='Target image file (e.g. example1.heic)')
    parser.add_argument('--new_iphone_data', default='new_iphone_data.txt', help='new_iphone_data metadata dump')
    parser.add_argument('--old_iphone_data', default='old_iphone_data.txt', help='old_iphone_data metadata dump')
    args = parser.parse_args()

    new_iphone_data_tags = parse_exif_dump(args.new_iphone_data)
    old_iphone_data_tags = parse_exif_dump(args.old_iphone_data)

    exif_args = build_exiftool_args(new_iphone_data_tags, old_iphone_data_tags)
    if not exif_args:
        print("No tags to write, exiting.")
        return

    cmd = ['exiftool', '-overwrite_original', '-XMPToolkit=""'] + exif_args + [args.image]
    print('Running:', ' '.join(cmd))
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print('Exiftool output:')
        print(result.stdout or result.stderr)
    except subprocess.CalledProcessError as e:
        print('Exiftool error:')
        print(e.stderr)

if __name__ == '__main__':
    main()
