# pvv_gen_custom_flaps.ps1 — Generate UV print layouts for custom splitflap flaps
# Run from anywhere: .\pvv_tools\pvv_gen_custom_flaps.ps1
# (script cd's to the repo root so job paths below stay short)

Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    #python -m pvv_tools.flap_printer pvv_tools/example_job.json --dry-run
    #python -m pvv_tools.flap_printer pvv_tools/example_job.json --output-dir pvv_flap_images/
    #python -m pvv_tools.flap_printer pvv_tools/PVV_TestFlapSet_01.json --output-dir pvv_flap_images/TestFlapSet_01/

    # Current prototype: 24-module display, 12 custom flaps
    # (EP42 dash, EP43 $, EP44-EP53 placeholders) — output lands in pvv_tools/prototype_output/
    python -m pvv_tools.flap_printer pvv_tools/prototype_job.json
}
finally {
    Pop-Location
}
