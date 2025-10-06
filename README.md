# scantailor-advanced-tools

A set of helper scripts for processing [`ScanTailor Advanced`](https://github.com/ScanTailor-Advanced/scantailor-advanced) 
output to PDF.

[`ScanTailor Advanced`](https://github.com/ScanTailor-Advanced/scantailor-advanced) is an incredibly useful
interactive tool for post-processing scanned pages.
It provides operations such as page splitting, deskewing, content selection, managing page borders, de-warping and 
high-resolution output rendering to TIFF images.
This repository adds some helper scripts for processing output pages produced by *ScanTailor Advanced*, e.g., 
to render and overlay pictures and text with different modes and resolutions, to combine pages
into document PDFs and to perform OCR.

## `make-pdfs.py`

This Python script assumes use of *ScanTailor Advanced* (1.0.19 or higher), with
the `Split output` option applied to *mixed* pages, putting marked picture regions into RGB background TIFFs
and the remaining text content into B/W foreground TIFFs.
Note that each Scantailor output page has *one* specific image resolution (dpi), which can be
set in ScanTailor Advanced and applies to all (background, foreground and combined) TIFFs associated with that page. 

* For *standard* (i.e., non-mixed monochromatic, grayscale or color) pages a single combined output TIFF is found in `out`,
but no corresponding TIFFs in `out/background` or `out/foreground`. The script converts this combined TIFF 
straightforward to the associated PDF page.

* For *mixed* pages, the associated TIFFs in `out/background` and `out/foreground` are merged by **overlaying**
the monochrome text image (foreground) transparently on top of the RGB picture image (background).
The background image is usually **subsampled** (typ. to 150&ndash;300 dpi) to reduce file size.
Background subsampling may be suppressed by passing option `--dpi=0`. Note that the foreground text is *never* sub-sampled but
keeps its original resolution. Thus high-resolution text (with typ. 600&ndash;1200 dpi) can be combined with reasonable
size images on the same PDF page.

The scripts first converts each scan page to a single raw PDF, which is then compressed and stored in 
 `./pdf`. Once all pages are processed, the associated PDFs are merged into a single PDF document,
to which OCR is applied optionally. The intermediate single page PDFs are removed by default but may be preserved
for inspection or other use.

## File structure

The script is supposed to be run inside *ScanTailor*'s *source folder* (referred to as `<scans>` here), 
i.e., where the original scan images are located.
When run (with options `Mixed` output page and `Split output` activated), *ScanTailor* creates the directories
```
  <scans>/out
  <scans>/out/background
  <scans>/out/foreground
```
which are read by this script. Directory `out` contains output TIFFs for *all* pages,
while `foreground` and `background` contain separate TIFFs for the text part and the picture regions, 
respectively, for mixed pages. The script will raise an error if any images are missing in `out` or if
images in `foreground` and `background` have different size and/or resolution.

The script creates and fills the additional directory
```
  <scans>/pdf
```
and places the combined document PDF in
```
  <scans>/out.pdf
```
Directory `<scans>/pdf` is automatically removed at the end of the script if given `--keepPDFs=false`.

## Usage

Copy file `make-pdfs.py` to the *ScanTailor*'s *source folder* ( `<scans>`, containing the `./out` directory
filled with page output TIFFs), then navigate to this folder (`cd <scans>`).
Open a (bash) shell and call
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
* Required Linux apps:
  + `python3` `python3-pip` `python3-venv`
  + `ghostscript` `tesseract-ocr` `tesseract-ocr-eng` `tesseract-ocr-deu`
* Required Python packages:
  + `pip` `setuptools` `wheel`
  + `pillow` `numpy` `PyMuPDF` `ocrmypdf`
