import pandas as pd
import numpy as np
import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from torchvision import transforms
from tqdm import tqdm

# return training_set, validation_set, test_set
random_seed = 42
# the path should include the organized_dataset.csv and an images folder with all tyhe images!!!!!
PATH = r'/home/theodor/Git_Projects/DD2424-Deep_Learning-COVID-Project/covid_dataset/'
data = pd.read_csv(PATH + "organized_dataset.csv")
cl_list = list(data.columns)
cl_list[0] = "Image Index"
data.columns = cl_list
data.pop('No Finding')  # Deleting the column no findings
validation_percentage = 0.2
test_percentage = 0.2
item_for_val = validation_percentage * data.shape[0]
item_for_test = test_percentage * data.shape[0]
data_train, data_val = train_test_split(data, test_size=int(item_for_val), random_state=random_seed)
data_train, data_test = train_test_split(data_train, test_size=int(item_for_test), random_state=random_seed)

mean = [0.485, 0.456, 0.406]
std = [0.229, 0.224, 0.225]
training_transforms = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.5,0.5,0.5,0.5),
    transforms.RandomRotation((-20, 20)),
    transforms.ToTensor(),
    transforms.Normalize(mean, std)  # Guarantee that it's in RGB, it's possible to transform to grayscale afterwards
])
val_test_transforms = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean, std)
])


class XrayDataset(torch.utils.data.Dataset):
    def __init__(self, path_of_the_images, dataframe, transforms=None):
        self.path = path_of_the_images
        self.df = dataframe
        self.transforms = transforms

    def __getitem__(self, index):
        row = self.df.iloc[index]
        full_path = self.path + row.loc['Image Index']
        img_array = Image.open(full_path).convert('RGB')
        if self.transforms is not None:
            img_array = self.transforms(img_array)
        aux = np.array(row.iloc[1:].values.tolist(), dtype=float)
        return img_array, aux

    def __len__(self):
        return self.df.shape[0]


# Construct Objects
training_set = XrayDataset(PATH + "images/", data_train, training_transforms)
validation_set = XrayDataset(PATH + "images/", data_val, val_test_transforms)
test_set = XrayDataset(PATH + "images/", data_test, val_test_transforms)
