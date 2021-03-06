import numpy as np
import pickle
import cv2
from tqdm import tqdm
from matplotlib import pyplot as plt
import matplotlib.pylab as pylab
from matplotlib.pyplot import cm
from PIL import Image
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import pandas as pd
import itertools

class myData:
    def __init__(self,data,labels):
        self.data=data
        self.labels=labels

def distance(grid, sample):
    return np.sum((grid - sample)**2, axis=2)

class SOM:
    def __init__(self, inputs, grid_width, grid_height, max_learning_rate = 0.8, min_learning_rate = 0.05, radious = 10): # input should be flattened
        np.random.seed(42)
        mean = np.mean(inputs, axis=0)
        std = np.std(inputs, axis=0)
        self.grid_height = grid_height
        self.grid_width = grid_width
        #self.grid = np.random.randn(grid_dim, grid_dim, mean.shape[0])*std*0.5 + mean
        # Try different initialization
        self.grid = np.random.normal(mean, std*0.25, (grid_width, grid_height, mean.shape[0]))
        self.max_learning_rate = max_learning_rate
        self.min_learning_rate = min_learning_rate
        self.radious = radious
        
    def find_winner(self, samples):
        winners = np.zeros((len(samples), 2))
        for i, sample in enumerate(samples):
            dis = distance(self.grid, sample)
            winners[i] = np.unravel_index(np.argmin(dis), dis.shape)
        return winners

    def update_grid(self, samples, lr, current_radious):
        winners = self.find_winner(samples)
        for (win_x, win_y), sample in zip(winners, samples):
            for candidate_x, candidate_y in np.ndindex(self.grid_width, self.grid_height):
                distance_from_winner = (candidate_x - win_x)**2 + (candidate_y - win_y)**2
                if distance_from_winner <= current_radious**2:
                    self.grid[candidate_x, candidate_y] += lr*(sample - self.grid[candidate_x, candidate_y])*np.exp(-distance_from_winner / 2*current_radious**2)
            
    def train(self, inputs, epochs, batch_size):
        tau = epochs**2/(np.log(4*self.radious))
        for epoch in tqdm(range(epochs)): 
            current_radious = int(self.radious*np.exp(-(epoch)**2/tau))
            lr = self.max_learning_rate - (self.max_learning_rate - self.min_learning_rate)*epoch/epochs
            for i in tqdm(range(0, inputs.shape[0], batch_size)):
                batch = inputs[i:i+batch_size]
                self.update_grid(batch, lr, current_radious)

# Reading Covid
path2covid = 'covid_dataset/'
df_covid = pd.read_csv(path2covid + "metadata.csv")
df_covid = df_covid[(df_covid['modality'] == "X-ray") & (df_covid['view'] != "L") & (df_covid['finding'] == "COVID-19")]
df_covid = df_covid[['finding', 'filename']]
covid_list = df_covid['finding'].values
covid_image_list = df_covid['filename'].values
amount_of_covid = len(df_covid)
path2covid_images = 'covid_dataset/images/'

# Read the other diseases dataset
df = pd.read_csv("xray_dataset/organized_dataset.csv")
df.pop('No Finding')  # Deleting the column no findings
cols = np.array(df.columns)
diseases_list = cols[2:]
df.loc[:,'sum'] = df[cols[2:]].sum(axis=1)
df = df[df['sum'] == 1]
df.pop('sum')
df.pop('Dataset')

image_list = []
image_labels = []
sample_num = amount_of_covid
counter = np.zeros(len(diseases_list))
for i, row in tqdm(df.iterrows()):
    disease_index = np.argmax(list(row[1:].values))
    disease_name = diseases_list[disease_index]
    if counter[disease_index] < sample_num:
        counter[disease_index] += 1
        image_list.append(row[0])
        image_labels.append(disease_name)

image_list.extend(covid_image_list)
image_labels.extend(covid_list)

try:
    print("Findind data")
    data = pickle.load(open('data_som.pickle', 'rb'))
except IOError:
    print("Couldn't find data")
    model_path = 'final_model_16.pt'

    def generateMap(model, pathImageFile, device):

        # Prepare image
        mean = [0.485, 0.456, 0.406]
        std = [0.229, 0.224, 0.225]
        image_transform = transforms.Compose([
            transforms.Resize((224,224)),
            transforms.ToTensor(),
            transforms.Normalize(mean, std)
        ])

        imageData = Image.open(pathImageFile).convert('RGB')
        imageData = image_transform(imageData)
        imageData = imageData.unsqueeze_(0)
        imageData = imageData.to(device)

        # Walk the image through the model
        output = model(imageData)
        #plt.imshow(output.detach().numpy().reshape((32,32)))
        #plt.show()
        flat_output = output.detach().numpy()
        return flat_output

    flatten = []
    print("START WALKING THE IMAGES THROUGH THE MODEL")
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model= torch.load(model_path, map_location='cpu')
    model.to(device)
    model.classifier = torch.nn.Identity()
    model.eval() # Doesn't store gradients
    for i in tqdm(range(len(image_list))):
        if image_labels[i] == 'COVID-19':
            pathInputImage = path2covid_images + image_list[i]
        else:
            pathInputImage = 'images_small/' + image_list[i]
        flatten.append(generateMap(model, pathInputImage, device))

    flattened = np.array(flatten)
    data = myData(flattened, image_labels)
    pickle.dump(data, open('data_som.pickle', 'wb'))

print("start SOMS")
# Train SOM
grid_height = 15
grid_width = 15
epochs = 100
batch_size = 1
# Shuffling the data
data_flattened = data.data # array
data_labels = data.labels # list
shuffling_index = np.random.permutation(data_flattened.shape[0])
data_flattened = data_flattened[shuffling_index]
data_flattened = data_flattened.reshape(-1, data_flattened.shape[2])
data_labels = np.array(data_labels)[shuffling_index]

som = SOM(data_flattened, grid_width, grid_height)
som.train(data_flattened, epochs, batch_size)
all_diseases_labels = set(image_labels)

# Plot the clusters, This is going to take much time
print("START CLUSTERS PLOTS")
dictionary = {0:'Atelectasis', 1:'Cardiomegaly', 2:'Consolidation', 3:'Edema', 4:'Effusion', 5:'Emphysema', 6:'Fibrosis', 7:'Hernia', 8:'Infiltration', 9:'Mass', 10:'COVID-19', 11:'Nodule', 12:'Pleural_Thickening', 13:'Pneumonia', 14:'Pneumothorax'}
ranking = np.zeros((grid_width, grid_height, 15))
print(list(dictionary.values()).index('Cardiomegaly'))
for sample, label in tqdm(zip(data_flattened, data_labels)):
    pos_x, pos_y = som.find_winner([sample])[0]
    ranking[int(pos_x), int(pos_y), list(dictionary.values()).index(label)] += 1
ranking_winners = np.array(np.argmax(ranking, axis=2), dtype=int)
number_of_points = np.sum(ranking, axis=2)
percentage_of_winner = np.max(ranking, axis=2)/number_of_points
number_of_points /= np.sum(number_of_points)

n = len(all_diseases_labels)
color= cm.rainbow(np.linspace(0,1,n))
c=np.array(color)
color_labels = np.zeros(len(all_diseases_labels))
marker = itertools.cycle((',', '+', '.', 'o', '*'))
disease_marker = []
for i in range(n):
    disease_marker.append(next(marker))

fig, ax = plt.subplots()
for i, j in np.ndindex(grid_width, grid_height):
    label = dictionary[ranking_winners[i,j]]
    if color_labels[ranking_winners[i,j]] == 0: 
        plt.scatter(i,j, c=c[ranking_winners[i,j]], marker = disease_marker[list(dictionary.values()).index(label)], alpha=0.7, s=number_of_points[i,j]*1e4, edgecolors='none', label=label)
        color_labels[ranking_winners[i,j]] += 1
    else:
        plt.scatter(i,j, c=c[ranking_winners[i,j]], marker = disease_marker[list(dictionary.values()).index(label)], alpha=0.7, s=number_of_points[i,j]*1e4, edgecolors='none')


lgnd = plt.legend(markerscale=1, loc='center left', bbox_to_anchor=(1, 0.5), scatterpoints=1, fontsize=10)
for handle in lgnd.legendHandles:
    handle.set_sizes([30.0])

# show the figure
fig.tight_layout()
plt.show()