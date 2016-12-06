from sodarutils.collections import SodarCollection
import matplotlib.pyplot as plt
import numpy as np

sodars = SodarCollection('data/Primet')
data = sodars.night_array('speed')

# Find the index of the specific night we're interested in
index = [i for i, j in enumerate(data[1]) if j['name']=='0519'][0]

# Get the data for just that night
night = np.transpose(data[0][index])[:]

# Create the plot, with a color key
fig, ax = plt.subplots(figsize=(8,8))
cax = fig.add_axes([1.0, 0.1, 0.05, 0.8])
im = ax.imshow(night, aspect='auto', origin='lower', cmap='Reds', interpolation='none')
fig.colorbar(im, cax=cax)
plt.show()