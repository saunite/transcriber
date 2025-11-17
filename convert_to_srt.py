#!/usr/bin/env python3
"""
Convert timestamped transcript to SRT subtitle format.

Takes a transcript file with timestamps like:
[00:05 -> 00:08] This is the text
[00:08 -> 00:12] More text here

And converts to SRT format:
1
00:00:05,000 --> 00:00:08,000
This is the text

2
00:00:08,000 --> 00:00:12,000
More text here

License: GPLv2
"""

import re
import sys
import argparse
from pathlib import Path


def parse_timestamp(timestamp_str):
    """
    Parse timestamp string like '00:05' or '17:32' to seconds.
    
    Args:
        timestamp_str: String in format MM:SS or HH:MM:SS
        
    Returns:
        Float seconds
    """
    parts = timestamp_str.strip().split(':')
    if len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        hours = 0
    elif len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")
    
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def seconds_to_srt_time(seconds):
    """
    Convert seconds to SRT timestamp format: HH:MM:SS,mmm
    
    Args:
        seconds: Float seconds
        
    Returns:
        String in SRT format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def convert_transcript_to_srt(input_path, output_path=None):
    """
    Convert timestamped transcript to SRT format.
    
    Args:
        input_path: Path to input transcript file
        output_path: Path to output SRT file (default: same name with .srt extension)
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return 1
    
    if output_path is None:
        output_path = input_path.with_suffix('.srt')
    else:
        output_path = Path(output_path)
    
    # Read input file
    print(f"Reading: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Parse transcript entries
    # Pattern matches: [00:05 -> 00:08] Text or [00:05 -> 00:08] [SYS] Text
    timestamp_pattern = re.compile(r'^\[(\d{1,2}:\d{2}(?::\d{2})?)\s*->\s*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?:\[(SYS|MIC)\]\s*)?(.+)$')
    
    entries = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        match = timestamp_pattern.match(line)
        if match:
            start_str, end_str, label, text = match.groups()
            try:
                start_seconds = parse_timestamp(start_str)
                end_seconds = parse_timestamp(end_str)
                
                # Add label to text if present
                if label:
                    text = f"[{label}] {text}"
                
                entries.append({
                    'start': start_seconds,
                    'end': end_seconds,
                    'text': text.strip()
                })
            except ValueError as e:
                print(f"⚠️  Skipping line (invalid timestamp): {line[:50]}...")
                continue
    
    if not entries:
        print("❌ Error: No valid timestamped entries found in input file")
        print("Expected format: [MM:SS -> MM:SS] Text")
        return 1
    
    # Write SRT file
    print(f"Writing: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(entries, start=1):
            f.write(f"{i}\n")
            f.write(f"{seconds_to_srt_time(entry['start'])} --> {seconds_to_srt_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n")
            f.write("\n")
    
    print(f"✓ Converted {len(entries)} entries to SRT format")
    print(f"✓ Saved to: {output_path}")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert timestamped transcript to SRT subtitle format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert transcript to SRT
  python convert_to_srt.py transcript.txt
  
  # Specify output file
  python convert_to_srt.py transcript.txt --output subtitles.srt
  
Input format (from live transcription):
  [00:05 -> 00:08] Welcome to the meeting
  [00:08 -> 00:12] [SYS] Thank you for joining
  [17:30 -> 17:35] [MIC] I have a question
  
Output format (SRT):
  1
  00:00:05,000 --> 00:00:08,000
  Welcome to the meeting
  
  2
  00:00:08,000 --> 00:00:12,000
  [SYS] Thank you for joining
"""
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Input transcript file with timestamps'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output SRT file (default: input filename with .srt extension)'
    )
    
    args = parser.parse_args()
    
    try:
        return convert_transcript_to_srt(args.input, args.output)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
