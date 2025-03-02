#!/usr/bin/env python3
"""
Standalone test for Stormgate replay decompression
"""

import sys
import gzip
import struct
from io import BytesIO
from pathlib import Path

def decompress(replay_path):
    """Modified decompress function with dynamic header size."""
    with open(replay_path, 'rb') as replay:
        # Read the header size from the file itself (at offset 8)
        replay.seek(8)
        (header_size,) = struct.unpack("<i", replay.read(4))
        
        # As a safety check, ensure header_size is reasonable
        if header_size < 16 or header_size > 256:
            print(f"Unusual header size detected: {header_size}, falling back to 24")
            header_size = 24  # Fall back to known working size
        
        # Get the build number for reference
        replay.seek(12)
        (build_number,) = struct.unpack("<i", replay.read(4))
        print(f"Build number: {build_number}, header size: {header_size}")
        
        # Skip header and decompress
        replay.seek(header_size)
        data = replay.read()
        try:
            decompressed = gzip.decompress(data)
            print(f"Successfully decompressed {len(decompressed)} bytes")
            return BytesIO(decompressed)
        except Exception as e:
            print(f"Error decompressing with header size {header_size}: {e}")
            # Try fallback sizes
            for size in [16, 24, 32]:
                if size != header_size:
                    try:
                        print(f"Trying fallback header size: {size}")
                        replay.seek(size)
                        decompressed = gzip.decompress(replay.read())
                        print(f"Successfully decompressed with fallback size {size}")
                        return BytesIO(decompressed)
                    except Exception as fallback_error:
                        print(f"Failed with size {size}: {fallback_error}")
                        continue
            raise Exception("All decompression attempts failed")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python standalone_test.py path/to/replay.SGReplay")
        sys.exit(1)
    
    replay_path = sys.argv[1]
    try:
        decompressed = decompress(replay_path)
        print("Test successful! Decompression works correctly.")
        
        # Examine the first few bytes of the decompressed data
        first_bytes = decompressed.read(32)
        hex_bytes = ' '.join(f"{b:02x}" for b in first_bytes)
        print(f"First 32 bytes of decompressed data: {hex_bytes}")
    except Exception as e:
        print(f"Test failed: {e}")