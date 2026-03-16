import swift_app as swift
import pandas as pd
import pathlib

basins_cwc = swift.cwc.basins()
swift.cwc.download(
    basins_cwc[0:2],
    start_date="2024-01-01",
    end_date="2024-01-02",
    output_dir="data_cwc_2",
    format="csv",
    overwrite=True,
    merge=False,
    plot=False,
    quiet=False,
)

print("Directory structure:")
for p in pathlib.Path("data_cwc_2").rglob("*"):
    print(p)
