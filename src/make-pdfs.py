#!/usr/bin/env python3
# Python scipt for converting Scantailor output TIFFs to PDFs
# Author: W. Burger (imagingbook)
# GitHub: https://github.com/imagingbook/scantailor-advanced-pdf
#
# Assumed directory structure:
# <scans> ...... ...............contains original page scans (already processed by ScanTailor)
# <scans>/out ................. Scantailor output TIFFs (all pages)
# <scans>/out/background ...... Scantailor background TIFFs (mixed pages only)
# <scans>/out/foreground ...... Scantailor foreground TIFFs (mixed pages only)
# <scans>/pdf ................. PDFs produced by this script, one for each page
# <scans>/out.pdf ............. the combined document PDF
#
# Usage:
#   Assumes that Scantailor's root folder (with original scan images) is <scans>.
#   For example, <scans> = "~/scan-projects/book1/orig-all".
#   If a virtual Python environment is used ("scaintailor-env" here), activate it:
#   > source ~/lensfun-env/bin/activate (only once, echo $VIRTUAL_ENV gives current env)
#   Copy this script to the <cans> directory:
#   > cp make-pdfs.py <scans>
#   Navigate to the <cans> directory:
#   > cd <scans>
#   Run the script:
#   > python3 make-pdfs.py
#   > python3 make-pdfs.py --list-only
#   > python3 make-pdfs.py --dpi=300 --lang=eng --keepPDFs=true
#   > python3 make-pdfs.py --lang=eng+deu                           # do OCR in english and german
#   > python3 make-pdfs.py --lang=none                              # skip OCR
#   > python3 make-pdfs.py --help
#   Deactivate the virtual environment (if used):
#   > deactivate (optional at end)
#
# This script assumes use of ScanTailor-Advanced (1.0.19 or higher), with
# the 'Split output' option applied to 'Mixed' pages, putting marked picture regions into RGB background TIFFs
# and the remaining text content into B/W foreground TIFFs.
# Note that each Scantailor output page has one specific image resolution (dpi), which applies
# to all (background, foreground and combined) TIFFs associated with that page. 
# For standard (i.e., non-mixed) pages a single output TIFF (in ./out) is produced, but no associated
# TIFFs in .out/background and .out/foreground.
# For mixed pages, the associated TIFFs in .out/background and .out/foreground are merged by overlaying
# the monochrome text image (foreground) transparently on top of the RGB picture image (background).
# The background image is usually subsampled (typ. to 300 dpi), which may be suppressed by passing
# option "--dpi=0".
# 
# The script is supposed to be run inside ScanTailor's source folder <scans>, where the original scan images are
# located. When run, ScanTailor creates the directories
#   <scans>/out
#   <scans>/out/background
#   <scans>/out/foreground
# which are read by this script. This in turn creates and fills the additional directory
#   <scans>/pdf
# and puts the combined document PDF in
#   <scans>/out.pdf
# Directory <scans>/pdf is automatically removed at the end if given "--keepPDFs=false".
#
# System requirements:
#   Linux apps:
#       python3 python3-pip python3-venv
#       ghostscript tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu
#   Python packages:
#       pip setuptools wheel
#       pillow numpy PyMuPDF ocrmypdf
 

import sys
import os
import argparse
from io import BytesIO
from PIL import Image
import numpy as np
import fitz  # PyMuPDF
import shutil
import subprocess
import tempfile
import glob

# ----------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Convert ScanTailor output to PDFs")

parser.add_argument("--lang", type=str, default="deu",
                    help="OCR language(s), e.g., 'eng', 'deu' (default), or multiple: 'eng+deu'. Use 'none' to skip OCR.")
                    
parser.add_argument("--dpi", type=int, default=300,
                    help="target DPI for picture downsampling (default: 300). Use 0 to skip resampling.")
                    
parser.add_argument("--quality", type=str, default="/printer",
                    choices=["/screen", "/ebook", "/printer", "/prepress"],
                    help="Ghostscript quality preset for final page PDFs (default: /printer).")
                    # see https://ghostscript.readthedocs.io/en/gs10.0.0/VectorDevices.html#the-family-of-pdf-and-postscript-output-devices
                    
parser.add_argument("--keepPDFs", type=str, default="false",
                    choices=["true", "false"],
                    help="Whether to keep the ./pdf directory (true/false). Default: false")

parser.add_argument("--list-only", action="store_true",
                    help="Only list TIFF files to be processed and exit")



args = parser.parse_args()

background_dpi = args.dpi   # 300
ocr_language = args.lang    # "deu"
do_ocr = (ocr_language.lower() != "none")
ghostscript_quality = args.quality     # /screen, /ebook, /printer, /prepress, /default
keep_pdfs = args.keepPDFs.lower() in ("1", "true", "yes")

# --- Color codes for terminal output ---
COLOR_RESET  = "\033[0m"
COLOR_YELLOW = "\033[93m"
COLOR_GREEN  = "\033[92m"
COLOR_CYAN   = "\033[96m"
COLOR_BOLD   = "\033[1m"

# ----------------------------------------------------------------------------------------

def collect_tiff_files(out_dir, foreground_dir, background_dir, verbose=False):
    """
    Collects all TIFF files from the main output directory and classifies
    them as 'standard' or 'mixed' depending on the presence of associated
    foreground/background files.

    Returns a list of dicts, each with:
        {
            'filename': 'im0001.tif',
            'path': 'out/im0001.tif',
            'type': 'mixed' or 'standard',
            'size': (width_px, height_px),
            'dpi': (x_dpi, y_dpi),
            'fgpath': 'path/to/foreground' or None,
            'bgpath': 'path/to/background' or None
        }
    """
    
# Collect main output TIFFs
    tiff_files = sorted([
        f for f in os.listdir(out_dir)
        if f.lower().endswith(('.tif', '.tiff'))
    ])

    if not tiff_files:
        print(f"\n{COLOR_BOLD}No TIFF files found in {out_dir}.{COLOR_RESET}\n")
        return []

    # Also list mixed-page sources
    fg_files = set([
        f for f in os.listdir(foreground_dir)
        if f.lower().endswith(('.tif', '.tiff'))
    ]) if os.path.exists(foreground_dir) else set()

    bg_files = set([
        f for f in os.listdir(background_dir)
        if f.lower().endswith(('.tif', '.tiff'))
    ]) if os.path.exists(background_dir) else set()

    # Warn if a mixed page exists but not in ./out
    mixed_missing = (fg_files | bg_files) - set(tiff_files)
    for missing in sorted(mixed_missing):
        print(f"{COLOR_RED}Mixed page '{missing}' has no matching file in {out_dir}!{COLOR_RESET}")
        

    pages = []
    mixed_count = 0
    standard_count = 0

    if verbose:
        print(f"\n{COLOR_BOLD}{COLOR_CYAN}TIFF files to be processed:{COLOR_RESET}\n")

    for fname in tiff_files:
        page_path = os.path.join(out_dir, fname)
        fg_path = os.path.join(foreground_dir, fname)
        bg_path = os.path.join(background_dir, fname)

        # Classify page type
        if os.path.exists(fg_path) and os.path.exists(bg_path):
            page_type = "mixed"
            mixed_count += 1
            color = COLOR_YELLOW
        else:
            page_type = "standard"
            standard_count += 1
            color = COLOR_GREEN

        # Read image metadata
        try:
            with Image.open(page_path) as img:
                size = img.size  # (width_px, height_px)
                dpi = img.info.get("dpi", (0, 0))
        except Exception as e:
            size = (0, 0)
            dpi = (0, 0)
            print(f"{COLOR_YELLOW}Warning:{COLOR_RESET} Could not read image {fname}: {e}")
        
        # For mixed pages, check consistency
        if page_type == "mixed":
            try:
                with Image.open(fg_path) as fg_img, Image.open(bg_path) as bg_img:
                    fg_size, fg_dpi = fg_img.size, fg_img.info.get("dpi", (0, 0))
                    bg_size, bg_dpi = bg_img.size, bg_img.info.get("dpi", (0, 0))
                    if fg_size != bg_size or fg_dpi != bg_dpi:
                        warnings += 1
                        print(f"{COLOR_RED}Mismatch in {fname}:{COLOR_RESET} "
                              f"FG {fg_size}@{fg_dpi} vs BG {bg_size}@{bg_dpi}")
            except Exception as e:
                print(f"{COLOR_RED}Error checking mixed page {fname}: {e}{COLOR_RESET}")

        # Display info if requested
        if verbose:
            print(f"  {color}{fname:<15}{COLOR_RESET} ({page_type}, {size[0]}×{size[1]} px, {int(dpi[0])} dpi)")

        pages.append({
            "filename": fname,
            "path": page_path,
            "type": page_type,
            "size": size,
            "dpi": dpi,
            "fgpath": fg_path if page_type == "mixed" else None,
            "bgpath": bg_path if page_type == "mixed" else None,
        })

    if verbose:
        print(f"\n{COLOR_BOLD}Summary:{COLOR_RESET}")
        print(f"  {COLOR_GREEN}{standard_count}{COLOR_RESET} standard pages")
        print(f"  {COLOR_YELLOW}{mixed_count}{COLOR_RESET} mixed pages")
        print(f"  Total: {len(pages)} pages\n")

    return pages

# ---------------------------------------------------------------------------------------

def resample_image_to_dpi(img_path, target_dpi):
    # see https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-filters
    # Image.Resampling.BICUBIC, Image.Resampling.BILINEAR, Image.Resampling.HAMMING, Image.Resampling.LANCZOS
    mode = Image.Resampling.LANCZOS       
    # print(f"{indent}Resampling image {img_path} to {target_dpi} dpi ({mode.name})")
    img = Image.open(img_path)
    if target_dpi == 0:
        # Skip resampling
        return img  # return original
    dpi_orig = img.info.get("dpi", (300, 300))
    x_inch = img.width / dpi_orig[0]
    y_inch = img.height / dpi_orig[1]
    new_size = (int(x_inch * target_dpi), int(y_inch * target_dpi))
    img_resized = img.resize(new_size, mode)
    img_resized.info['dpi'] = (target_dpi, target_dpi)
    return img_resized
    
# ---------------------------------------------------------------------------------------

out_dir = "./out"                                           # ScanTailor's output TIFFs are assumed here
foreground_dir = os.path.join(out_dir, "foreground")        # 1-bit text TIFFs from ScanTailor
background_dir = os.path.join(out_dir, "background")        # color/grayscale TIFF
pdf_dir = "./pdf"                                           # directory to store individual page PDFs
combined_pdf = "out-combined.pdf"                           # temporary PDF from merging all page PDFs
final_pdf = "out.pdf"                                       # final PDF with or without OCR
indent = "    "

if not os.path.exists(out_dir):
    sys.exit(f"The directory '{out_dir}' does not exist. Please run ScanTailor first.")

# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

# Collect page files from out_dir:
tiff_files = collect_tiff_files(out_dir, foreground_dir, background_dir, verbose=True)

if not tiff_files:
    sys.exit(f"No TIFF files found in '{out_dir}'")
    
if args.list_only:
    sys.exit(0)

# ------- actual page processing starts here --------------------------------------------

# Create new ./pdf/ directory
if os.path.exists(pdf_dir):
    shutil.rmtree(pdf_dir)
os.makedirs(pdf_dir, exist_ok=True)

count_standard = 0
count_mixed = 0

# Page by page loop
for tiff_file in tiff_files:
    base_name = base_name = os.path.splitext(tiff_file["filename"])[0]
    output_pdf_path = os.path.join(pdf_dir, f"{base_name}.pdf")
    
    with tempfile.NamedTemporaryFile(prefix=base_name+"-", suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name
    
    # if os.path.exists(fg_path) and os.path.exists(bg_path):
    if tiff_file["type"] == "mixed":
        fg_path = tiff_file["fgpath"]
        bg_path = tiff_file["bgpath"]
        # Mixed page: overlay foreground over background TIFF
        count_mixed += 1
        print(f"Processing MIXED page {base_name} ......")
                
        # Open background image and save to in-memory PNG
        bg_img = resample_image_to_dpi(bg_path, background_dpi).convert("RGB")
        bg_bytes = BytesIO()
        bg_img.save(bg_bytes, format="PNG")
        bg_bytes.seek(0)
        
        # Open foreground image and create in-memory RGBA mask
        fg_img = Image.open(fg_path).convert("L")
        fg_data = np.array(fg_img)
        alpha = np.where(fg_data < 128, 255, 0).astype(np.uint8)
        black = np.zeros_like(alpha)
        rgba = np.dstack((black, black, black, alpha))
        fg_rgba = Image.fromarray(rgba)

        fg_bytes = BytesIO()
        fg_rgba.save(fg_bytes, format="PNG")
        fg_bytes.seek(0)

        bg_width_pt  = bg_img.width  * 72.0 / background_dpi
        bg_height_pt = bg_img.height * 72.0 / background_dpi
        
        # Create raw PDF (files may be big!)
        doc = fitz.open()
        page = doc.new_page(width=bg_width_pt, height=bg_height_pt)
        page.insert_image(page.rect, stream=bg_bytes)
        page.insert_image(page.rect, stream=fg_bytes, overlay=True)   
        doc.save(tmp_pdf_path)
        doc.close()
    else:
        # Standard page (non-mixed monochrome or grayscale/color TIFF)
        std_path = tiff_file["path"]
        count_standard += 1
        print(f"Processing STANDARD page {base_name} ......")
        img = Image.open(std_path)
        dpi = img.info.get("dpi", (300,300))[0]
        # print(f"image size = {float(img.width) / dpi} x {float(img.height) / dpi} inches")
        width_pt  = img.width  * 72.0 / dpi
        height_pt = img.height * 72.0 / dpi
                
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        doc = fitz.open()
        page = doc.new_page(width=width_pt, height=height_pt)
        page.insert_image(page.rect, stream=img_bytes)
        doc.save(tmp_pdf_path)
        doc.close()

    # Compress raw PDF via Ghostscript (not necessary for standard pages but good to have same PDF specs)
    try:
        print(f"{indent}Compressing raw PDF to {output_pdf_path}")
        subprocess.run([
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={ghostscript_quality}",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_pdf_path}",
            tmp_pdf_path
        ], check=True)
        
    finally: # Cleanup temp files even if GS fails
        try:
            os.remove(tmp_pdf_path)
        except FileNotFoundError:
            pass   
# End of page-by-page loop

# Summary
total_pages = count_standard + count_mixed
print("\nProcessing complete!")
print(f" - Standard pages: {count_standard}")
print(f" - Mixed pages: {count_mixed}")
print(f" - Total pages: {total_pages}")

# ------- Now merge all page PDFs into a single document: ---------------------------------

print(f"\nMerging all page PDFs into {combined_pdf}")
pdf_files = sorted(glob.glob("pdf/*.pdf"))
if not pdf_files:
    sys.exit("No PDF files found in ./pdf — nothing to merge.")

merge_command = [
    "gs",
    "-dBATCH",
    "-dNOPAUSE",
    "-q",
    "-sDEVICE=pdfwrite",
    #"-dAutoRotatePages=/None",
    f"-sOutputFile={combined_pdf}",
] + pdf_files

subprocess.run(merge_command, check=True)

# ------- Optionally perform OCR on the merged and compressed PDF without any further optimization

if do_ocr:
    print(f"Running OCR on {combined_pdf} writing result to {final_pdf} (lang={ocr_language})")
    ocr_command = [
        "ocrmypdf",
        "--quiet",                      # remove to get verbose output
        "--output-type", "pdf",         # plain PDF, for efficiency
        "--fast-web-view", "999999",    # turn off for efficiency
        "--language", ocr_language,     # OCR language
        "--redo-ocr",
        "--optimize", "0",
        #"--jbig2-lossless",
        "--rotate-pages", "--rotate-pages-threshold", "2",
        f"{combined_pdf}",
        f"{final_pdf}"
    ]
    subprocess.run(ocr_command, check=True)
else:
    print(f"Skipping OCR, creating {final_pdf}")
    shutil.move(combined_pdf, final_pdf)

# ------- Final cleanup --------------------------------------------------------------------

if os.path.exists(combined_pdf):
    print(f"Removing file {combined_pdf}")
    os.remove(combined_pdf)
    
if keep_pdfs:
    print(f"Keeping single page PDFs in {pdf_dir} directory")
else:
    print(f"Removing {pdf_dir} directory")
    shutil.rmtree(pdf_dir)
    
print("Done.")