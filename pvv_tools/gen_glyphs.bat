@echo off
:: Generate per-character flap SVGs for each font preset.
:: Each line is independent -- copy, comment out, or add lines as needed.
:: Output: assets/flap_glyphs/<font>/flap_NN.svg  (auto-derived from --font)
:: Fonts available: see 3d/flap_fonts.scad for all preset names.

cd /d "%~dp0\.."
call .venv\Scripts\activate.bat

rem python pvv_tools\generate_epilogue_flap_svgs.py --font Epilogue
python pvv_tools\generate_epilogue_flap_svgs.py --font Roboto
