import numpy as np
import pandas as pd
from tqdm import tqdm

PATH = r"xray_dataset/"
df = pd.read_csv(PATH + "Data_Entry_2017.csv")
train_val = pd.read_csv(PATH + "train_val_list.txt", names = ['Image Index'])
train_val['Dataset'] = 'train'
test = pd.read_csv(PATH + "test_list.txt", names = ['Image Index'])
test['Dataset'] = 'test'
datasets = train_val.append(test)
findings_dict = {}
for i, sample in tqdm(df.iterrows()):
    findings = sample['Finding Labels'].split('|')
    for finding in findings:
        if finding not in findings_dict.keys():
            findings_dict[finding] = len(findings_dict.keys())
    
cols = list(findings_dict.keys())
# cols.extend(findings_dict.keys())

new_df = pd.DataFrame(df['Image Index'])
for col in cols:
    new_df[col] = 0

new_df = new_df.set_index('Image Index')
datasets = datasets.set_index('Image Index')
new_df  = pd.merge(datasets, new_df, on="Image Index", how="right")

for i, sample in tqdm(df.iterrows()):
    findings = sample['Finding Labels'].split('|')
    for finding in findings:
        new_df[finding].iloc[i] = 1

new_df.to_csv(PATH + "organized_dataset.csv")