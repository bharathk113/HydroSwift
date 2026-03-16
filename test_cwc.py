import swift_app as swift
import pandas as pd
basins_cwc = swift.cwc.basins()
print(basins_cwc.head())

swift.cwc.download(
    basins_cwc[0:2],
    start_date="2024-01-01",
    end_date="2024-01-02",
    output_dir="data_cwc",
    format="csv",
    overwrite=True,
    merge=False,
    plot=False,
    quiet=False,
)
