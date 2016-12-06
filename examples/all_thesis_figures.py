# Compare two nights

from sodarutils.collections import SodarCollection
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as col
import matplotlib as mpl


def cyclic_colormap():
    black = '#000000'
    red = '#ff0000'
    blue = '#0000ff'
    green = '#00ff00'

    return col.LinearSegmentedColormap.from_list(
        'anglemap', [black, red, blue, green, black], N=256, gamma=1)


# NNE_MIN = 11.25
# NNE_MAX = 33.75
desired_direction = 22.5  # exact NNE direction


# we want to see how close we are to the desired direction
def closeness_gradient(a):
    # nan value
    if a == -1:
        return a

    x = (a - desired_direction) % 360

    if x <= 180.:
        return 1. - x / 180.
    else:
        return (x - 180.) / 180.


# classify the values based on some threshold
# currently just multiplies them together and maintains the no data value
def dir_classifier(a, b):
    if a == -1. or b == -1.:  # handle no-data across entries
        return -1.
    return a * b;


# vectorize the functions
v_closeness = np.vectorize(closeness_gradient)
v_dif_classifier = np.vectorize(dir_classifier)

# all the night figures in Jerilyn's thesis
nights = ['0328', '0423', '0430', '0505', '0518', '0526', '0527', '0612']
bands = ['direction', 'speed']
num_rows = 29

# raw data collections
mcrae = SodarCollection('sodar_data\Mcrae')
primet = SodarCollection('sodar_data\Primet')


def build_plots(night_date, band, generate_classifier=False):
    mcrae_data = mcrae.night_array(band)
    primet_data = primet.night_array(band)

    # Find the index of the specific night we're interested in
    m_index = [i for i, j in enumerate(mcrae_data[1]) if j['name'] == night_date][0]
    p_index = [i for i, j in enumerate(primet_data[1]) if j['name'] == night_date][0]

    # collect the data of the nights we want
    m_data = mcrae_data[0][m_index]
    p_data = primet_data[0][p_index]

    # labels across all charts
    ytick_labels = primet.heights[:num_rows][::2]
    yticks = [i for i in range(num_rows)][::2]
    y_label = 'Height (above ground level) [m]'
    xtick_labels = ['18:00', '21:00', '00:00', '03:00', '06:00']
    xticks = [0, 35, 72, 108, 144]

    if band == 'speed':
        # Create the plot, with a color key
        fig, (ax1, ax2) = plt.subplots(2, figsize=(10, 8), sharex=True)
        fig.canvas.set_window_title('Speed ({night})'.format(night=night_date))
        cax = fig.add_axes([.9, 0.1, 0.02, 0.8])
        # note the use of vmin and vmax
        # im1 = ax1.imshow(p_data.T[:num_rows], vmin=0.0, vmax=10.0, aspect='auto', origin='lower', cmap='hot', interpolation='none')
        # im2 = ax2.imshow(m_data.T[:num_rows], vmin=0.0, vmax=10.0, aspect='auto', origin='lower', cmap='hot', interpolation='none')
        im1 = ax1.imshow(p_data.T[:num_rows], vmin=0.0, vmax=10.0, aspect='auto', origin='lower', interpolation='none')
        im2 = ax2.imshow(m_data.T[:num_rows], vmin=0.0, vmax=10.0, aspect='auto', origin='lower', interpolation='none')

        spd_cbar = fig.colorbar(im1, cax=cax)
        spd_cbar.set_ticks([x for x in range(11)])
        ax1.set_yticks(yticks)
        ax1.set_yticklabels(ytick_labels)
        ax1.set_xticks(xticks)
        ax1.set_xticklabels(xtick_labels)
        ax1.set_ylabel(y_label)
        ax1.set_title('Primet Speed {night}'.format(night=night_date))
        ax2.set_yticks(yticks)
        ax2.set_yticklabels(ytick_labels)
        ax1.set_xticks(xticks)
        ax2.set_xticklabels(xtick_labels)
        ax2.set_ylabel(y_label)
        ax2.set_xlabel('Hour (1800 - 0600)')  # set the common x label
        ax2.set_title('McRae Speed {night}'.format(night=night_date))
        return

    # else: band == 'direction'

    # apply our closeness function
    dir_class_m = v_closeness(m_data)
    dir_class_p = v_closeness(p_data)

    # classify based on closeness
    classification = v_dif_classifier(dir_class_m, dir_class_p)

    # mask out no data values
    dir_class_m[dir_class_m == -1.0] = np.nan
    dir_class_p[dir_class_p == -1.0] = np.nan
    classification[classification == -1.0] = np.nan

    # look at each night independently, direction and 'closeness' to NNE
    fig1, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 8), sharex='col', sharey='row')
    fig1.subplots_adjust(left=0.09)
    fig1.canvas.set_window_title('Direction ({night})'.format(night=night_date))

    # direction plots
    im1 = ax1.imshow(p_data.T[:num_rows], aspect='auto', origin='lower', cmap=cyclic_colormap(), interpolation='none')
    ax1.set_yticks(yticks)
    ax1.set_yticklabels(ytick_labels)
    ax1.set_xticks(xticks)
    ax1.set_xticklabels(xtick_labels)
    ax1.set_ylabel(y_label)
    ax1.set_title('Primet Direction {night}'.format(night=night_date))

    im3 = ax3.imshow(m_data.T[:num_rows], aspect='auto', origin='lower', cmap=cyclic_colormap(), interpolation='none')
    ax3.set_yticks(yticks)
    ax3.set_yticklabels(ytick_labels)
    ax3.set_xticks(xticks)
    ax3.set_xticklabels(xtick_labels)
    ax3.set_ylabel(y_label)
    ax3.set_xlabel('Hour (1800 - 0600)')  # set the common x label
    ax3.set_title('McRae Direction {night}'.format(night=night_date))

    dir_cax = fig1.add_axes([0.462, 0.1, 0.02, 0.8])
    dir_cbar = fig1.colorbar(im1, cax=dir_cax)
    dir_cbar.set_ticks([0, 90, 180, 270, 359])
    dir_cbar.ax.set_yticklabels(['N', 'E', 'S', 'W', 'N'])

    # trueness to NNE direction plots; note use of vmin and vmax
    im2 = ax2.imshow(dir_class_p.T[:num_rows], vmin=0.0, vmax=1.0, aspect='auto', origin='lower', cmap='viridis',
                     interpolation='none')
    ax2.set_title('Primet "Closeness" to NNE Direction')
    im4 = ax4.imshow(dir_class_m.T[:num_rows], vmin=0.0, vmax=1.0, aspect='auto', origin='lower', cmap='viridis',
                     interpolation='none')
    ax4.set_title('McRae "Closeness" to NNE Direction')
    ax4.set_xlabel('Hour (1800 - 0600)')  # set the common x label

    true_cax = fig1.add_axes([0.905, 0.1, 0.02, 0.8])
    true_cbar = fig1.colorbar(im2, cax=true_cax)
    true_cbar.set_ticks([x / 10 for x in range(11)])

    if generate_classifier:
        fig2, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(classification.T[:num_rows], aspect='auto', origin='lower', cmap='viridis', interpolation='none')
        cax = fig2.add_axes()
        cbar = fig2.colorbar(im, cax=cax, orientation='vertical')
        ax.set_yticks(yticks)
        ax.set_yticklabels(ytick_labels)
        ax.set_xticks(xticks)
        ax.set_xticklabels(xtick_labels)
        ax.set_ylabel(y_label)
        ax.set_xlabel('Hour (1800 - 0600)')  # set the common x label
        ax.set_title('"Connectivity" in direction (blowing NNE) - {night}'.format(night=night_date))


for night in nights:
    for band in bands:
        build_plots(night, band)

plt.show()
