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

The scripts first converts each scan page to a single raw PDF, which is then compressed and stored in 
directory `./pdf`. Once all pages are processed, the associated PDFs are merged into a single PDF document,
to which OCR is applied optionally. The intermediate single page PDFs are removed by default but may be preserved
for inspection or other use.

## File structure

The script is supposed to be run inside ScanTailor's *source folder* (referred to as `<scans>` here), 
where the original scan images are located.
When run (with *mixed* pages and the `Split output` option activated), ScanTailor creates the directories
```
  <scans>/out
  <scans>/out/background
  <scans>/out/foreground
```
which are read by this script. This in turn creates and fills the additional directory
```
  <scans>/pdf
```
and places the combined document PDF in
```
  <scans>/out.pdf
```
Directory `<scans>/pdf` is automatically removed at the end of the script if given `--keepPDFs=false`.

## Usage

Copy file `make-pdfs.py` to the ScanTailor's *source folder* (which contains the `./out` directory
filled with page output TIFFs),
then navigate to the source folder (`cd <scans>`).
To use only default parameters open a (bash) shell and call
```bash
> python3 make-pdfs.py
```
or, even simpler,
```bash
> ./make-pdfs.py
```
To override the default parameters, simply provide optional arguments.
The following example downsamples all picture content to 200 dpi (default is 300 dpi),
performs OCR with English *and* German languages active and does not remove the intermediate
page PDFs:
```bash
> ./make-pdfs.py --dpi=200 --lang=eng+deu --keepPDFs=true
```
To see all available options run
```bash
> ./make-pdfs.py --help
```

## System requirements and installation
* Linux apps:
  + `python3` `python3-pip` `python3-venv`
  + `ghostscript` `tesseract-ocr` `tesseract-ocr-eng` `tesseract-ocr-deu`
* Python packages:
  + `pip` `setuptools` `wheel`
  + `pillow` `numpy` `PyMuPDF` `ocrmypdf`
