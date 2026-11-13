# Store images progress
- DONE: tools/store_images.py + tools/store_common.py (identical shared plumbing in all three repos) generate store/images/*.
- Run: python3 tools/store_images.py [capture] [compose]  (capture = headless Chrome with the unpacked extension, raw PNGs in tools/store_raw/ (gitignored); compose = layouts to exact sizes, 24-bit RGB, icon RGBA).
- All 8 files verified from PNG headers (sizes, 8-bit RGB; store-icon is RGBA by design) and viewed.
- listing.md section 10 updated to the final file list.
