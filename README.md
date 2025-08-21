Example Print String 

Start-Process -FilePath "C:\labels\label_3x1_20250821-213711-993661.pdf" -Verb Print

& "C:\Program Files\SumatraPDF\SumatraPDF.exe" -print-to-default -silent -exit-on-print -print-settings "copies=1" "C:\labels\label_3x1_20250821-213711-993661.pdf"