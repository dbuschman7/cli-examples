#!/usr/bin/env python3
import pandas as pd

df = pd.read_parquet("example_output.parquet")

print(df.info())
print(df.head(50))
