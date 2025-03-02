#!/usr/bin/env python3
"""
Stormgate Replay Analyzer

This script analyzes Stormgate replay files to determine their structure and format.
Run it on a replay file to get detailed information about its contents.

Usage: python replay_analyzer.py path/to/replay.SGReplay
"""

import sys
import os
import struct
import binascii
import math
from pathlib import Path
from collections import Counter

def analyze_replay(replay_path):
    """Analyze the structure of a replay file to determine its format."""
    try:
        with open(replay_path, 'rb') as f:
            # Get file size
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()
            f.seek(0)  # Go back to beginning
            
            print(f"== Analyzing {replay_path} ==")
            print(f"File size: {file_size} bytes")
            
            # Read the first 64 bytes to examine header
            header = f.read(64)
            print("\n== Header Analysis ==")
            print(f"First 64 bytes (hex):")
            for i in range(0, len(header), 16):
                line_bytes = header[i:i+16]
                hex_str = ' '.join(f"{b:02x}" for b in line_bytes)
                ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in line_bytes)
                print(f"{i:04x}: {hex_str:<48} | {ascii_str}")
            
            # Try to extract build number using current method
            f.seek(12)
            build_bytes = f.read(4)
            if len(build_bytes) == 4:
                build_number = struct.unpack("<i", build_bytes)[0]
                print(f"\nBuild number (from offset 12): {build_number}")
            
            # Sample data from throughout the file
            print("\n== File Structure Analysis ==")
            sample_points = [16, 32, 64, 128, 256, 512, 1024]
            for offset in sample_points:
                if offset < file_size:
                    f.seek(offset)
                    sample = f.read(16)
                    hex_sample = ' '.join(f"{b:02x}" for b in sample)
                    print(f"Bytes at offset {offset}: {hex_sample}")
            
            # Read the entire file for analysis
            f.seek(0)
            data = f.read()
            
            # Check for common file signatures
            print("\n== Format Detection ==")
            signatures = {
                b'\x1f\x8b': "gzip",
                b'\x78\x01': "zlib (no compression)",
                b'\x78\x9c': "zlib (default compression)",
                b'\x78\xda': "zlib (best compression)",
                b'\x50\x4b\x03\x04': "zip/jar/apk",
                b'\x42\x5a\x68': "bzip2",
                b'\xfd\x37\x7a\x58\x5a\x00': "xz",
                b'\x4f\x67\x67\x53': "ogg",
                b'\x52\x61\x72\x21': "rar",
                b'\x37\x7a\xbc\xaf\x27\x1c': "7z",
                b'\x89\x50\x4e\x47': "png"
            }
            
            # Check original header (assume 16 bytes)
            at_offset_16 = data[16:16+20]
            print("Checking for known signatures after 16-byte header:")
            signature_found = False
            for sig, fmt in signatures.items():
                if at_offset_16.startswith(sig):
                    print(f"  - Found {fmt} signature at offset 16")
                    signature_found = True
            
            if not signature_found:
                print("  - No known compression format signatures found at offset 16")
                
            # Try other common offsets
            for offset in [0, 8, 24, 32]:
                if offset + 10 < len(data):
                    block = data[offset:offset+20]
                    for sig, fmt in signatures.items():
                        if block.startswith(sig):
                            print(f"  - Found {fmt} signature at offset {offset}")
            
            # Statistical analysis
            print("\n== Statistical Analysis ==")
            # Count byte frequency
            byte_counts = Counter(data)
            total_bytes = len(data)
            
            # Calculate entropy (randomness measure)
            entropy = 0
            for count in byte_counts.values():
                probability = count / total_bytes
                entropy -= probability * math.log2(probability)
            
            print(f"Shannon entropy: {entropy:.2f} bits/byte (max 8.0)")
            print(f"Interpretation:")
            if entropy > 7.5:
                print("  - Very high entropy: likely encrypted or compressed data")
            elif entropy > 6.0:
                print("  - High entropy: likely compressed or binary data")
            elif entropy > 4.0:
                print("  - Medium entropy: mixed content or structured binary")
            else:
                print("  - Low entropy: possibly plain text or structured data")
            
            # Most common bytes (can help identify patterns)
            print("\nMost common bytes:")
            for byte, count in byte_counts.most_common(10):
                percentage = (count / total_bytes) * 100
                print(f"  0x{byte:02x}: {count} occurrences ({percentage:.2f}%)")
                
            # Try to find patterns
            print("\n== Pattern Detection ==")
            
            # Look for potential protobuf structure (common 0x0A, 0x12, 0x1A byte patterns)
            protobuf_markers = sum(1 for i in range(len(data)-1) 
                                if data[i] in [0x0A, 0x12, 0x1A, 0x22, 0x2A] 
                                and i+1 < len(data) and data[i+1] < 128)
            
            if protobuf_markers > len(data) / 100:  # At least 1% of bytes are potential markers
                print("  - Detected possible Protocol Buffer patterns")
            
            # Check for repeated sequences
            seq_len = 4  # Look for 4-byte sequences
            repeated_seqs = Counter()
            for i in range(len(data) - seq_len):
                seq = data[i:i+seq_len]
                repeated_seqs[seq] += 1
            
            print("\nMost common 4-byte sequences:")
            for seq, count in repeated_seqs.most_common(5):
                if count > 10:  # Only show if it appears multiple times
                    hex_seq = ' '.join(f"{b:02x}" for b in seq)
                    print(f"  {hex_seq}: {count} occurrences")
            
            print("\n== Recommendations ==")
            if entropy > 7.0:
                print("The file appears to be compressed or encrypted.")
                print("Possible approaches:")
                print("1. Check if the game has changed its compression algorithm")
                print("2. Look for a different header size than 16 bytes")
                print("3. Investigate if encryption has been added to the format")
            else:
                print("The file appears to have some structure.")
                print("Possible approaches:")
                print("1. The header size might have changed")
                print("2. Try parsing the file without decompression first")
                print("3. Check for a new file format entirely")
            
    except Exception as e:
        print(f"Error analyzing replay: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} path/to/replay.SGReplay")
        sys.exit(1)
    
    replay_path = sys.argv[1]
    analyze_replay(replay_path)