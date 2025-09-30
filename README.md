# scantailor-advanced-pdf

A single Python script for processing [`ScanTail Advanced`](https://github.com/ScanTailor-Advanced/scantailor-advanced) output TIFFs to PDF. 

## How this software works

This script assumes use of `ScanTailor Advanced` (1.0.19 or higher), with
the `Split output` option applied to *mixed* pages, putting marked picture regions into RGB background TIFFs
and the remaining text content into B/W foreground TIFFs.
Note that each Scantailor output page has one specific image resolution (dpi), which applies
to all (background, foreground and combined) TIFFs associated with that page. 
For *standard* (i.e., non-mixed) pages a single output TIFF (in `./out`) is produced, but no 
associated TIFFs in `.out/background` and
`.out/foreground`.

For *mixed* pages, the associated TIFFs in `.out/background` and `.out/foreground` are merged by overlaying
the monochrome text image (foreground) transparently on top of the RGB picture image (background).
The background image is usually subsampled (typ. to 300 dpi), which may be suppressed by passing
option `--dpi=0`.

The script is supposed to be run inside ScanTailor's *source folder* `<scans>`, where the original scan images are
located. When run (with *mixed* pages and the `Split output` option activated), ScanTailor creates the directories
```
  <scans>/out
  <scans>/out/background
  <scans>/out/foreground
```
which are read by this script. This in turn creates and fills the additional directory
```
  <scans>/pdf
```
and puts the combined document PDF in
```
  <scans>/out.pdf
```
Directory `<scans>/pdf` is automatically removed at the end of the script if given `--keepPDFs=false`.

## System requirements
* Linux apps:
      + `python3` `python3-pip` `python3-venv`
      + `ghostscript` `tesseract-ocr` `tesseract-ocr-eng` `tesseract-ocr-deu`
* Python packages:
      + `pip` `setuptools` `wheel`
      + `pillow` `numpy` `PyMuPDF` `ocrmypdf`
