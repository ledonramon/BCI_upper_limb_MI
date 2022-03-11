import argparse
import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
from meegkit.asr import ASR
from scipy import signal
import pickle
import src.unicorn_utils as utils

pd.options.mode.chained_assignment = None  # default='warn'

def execution(pipeline_type, list_of_freq_lim, freq_limits_names_list, filt_orders, window_sizes):
    print(f'Preprocessing for {pipeline_type} experimentation...')
    # INIT
    sampling_frequency = 250 
    # testing here for 8 electrodes:
    electrode_names =  ['FZ', 'C3', 'CZ', 'C4', 'PZ', 'PO7', 'OZ', 'PO8']
    asr = False
    subject = 'X01_wet'  
    folder_path = Path(f'./data/pilots/{subject}/openloop')
    env_noise_path = Path(f'./data/pilots/{subject}/Envdata')
    result_path = Path(f'./data/pilots/intermediate_datafiles/preprocess/{subject}')
    result_path.mkdir(exist_ok=True, parents=True)  
    dataset_full = {}
    trials_amount = 0

    #asr stuff
    asr = None
    for instance in os.scandir(env_noise_path):
        if instance.path.endswith('.csv'): 
            env_noise_X = pd.read_csv(instance.path)
    env_noise_X = env_noise_X.loc[:,electrode_names].T
    b_env,a_env = signal.butter(2, 0.5/(sampling_frequency/2), 'highpass')
    env_noise_X_filt = signal.filtfilt(b_env, a_env, env_noise_X)
    # Initialize ASR!
    asr = ASR(method='euclid')
    asr.fit(env_noise_X_filt)

    for instance in os.scandir(folder_path):
        if instance.path.endswith('.csv'): 
            trials_amount +=1
            print(f'adding_{instance} to dataset...')
            sig = pd.read_csv(instance.path)
            X = sig.loc[:,electrode_names]
            y = sig.loc[:,'Class']
            dataset_full[str(instance)] = pd.concat([X,y], axis=1)
  
    for window_size in window_sizes:
        for filt_ord in filt_orders:
            for freq_limit_instance in range(len(list_of_freq_lim)):
                freq_limits = np.asarray(list_of_freq_lim[freq_limit_instance]) 
                freq_limits_names = freq_limits_names_list[freq_limit_instance]
                print(f'experimenting with filter order of {filt_ord}, freq limits of {freq_limits_names}, \
                        and ws of {window_size}.')

                filters = utils.init_filters(freq_limits, sampling_frequency, filt_type = 'bandpass', order=filt_ord)
                data_dict = {'data' : {}, 'labels': {}}

                df_num = 0
                for df in dataset_full:
                    print(df)
                    data_dict['data'][df_num], data_dict['labels'][df_num] = [], []
                    X_temp, y_temp = utils.unicorn_segmentation_overlap_withfilt(dataset_full[df], window_size, filters,
                    electrode_names, freq_limits_names, pipeline_type, sampling_frequency, asr)
                    for segment in range(len(X_temp)): 
                        data_dict['data'][df_num].append(X_temp[segment])
                        data_dict['labels'][df_num].append(y_temp[segment]) 
                    df_num += 1

                results_fname = f'{subject}_{pipeline_type}_filtord{filt_ord}_freqlimits{freq_limits_names}_ws{window_size}.pkl'
                save_file = open(result_path / results_fname, "wb")
                pickle.dump(data_dict, save_file)
                save_file.close()
                print('Finished a preprocess pipeline.')

def main():
    if 'csp' in FLAGS.pline:
        # filterbank
        list_of_freq_lim = [[[4, 8], [8, 12], [12, 16], [16, 20], [20,24], [24,28], [28,32], [32,36], [36,40]],
        [[5, 10], [10, 15], [15, 20], [20, 25]], [[5, 10], [10, 15], [15, 20], [20, 25], [25, 30], [30, 35]]]
        freq_limits_names_list = [['4_8Hz', '8_12Hz','12_16Hz','16_20Hz', '20_24Hz','24_28Hz', '28_32Hz', '32_36Hz', '36_40Hz'],
        ['5_10Hz', '10_15Hz','15_20Hz','20_25Hz'], ['5_10Hz', '10_15Hz','15_20Hz','20_25Hz', '25_30Hz', '30_35Hz']]
        filt_orders = [2,3,4]
        window_sizes = [250,375,500]
        execution('csp', list_of_freq_lim, freq_limits_names_list, filt_orders, window_sizes)
    if 'deep' in FLAGS.pline or 'riemann' in FLAGS.pline:
        list_of_freq_lim = [[[4,35]], [[8, 35]], [[4,40]], [[8,40]]]
        freq_limits_names_list = [['4-35Hz'], ['8_35Hz'], ['4-40Hz'], ['8-40Hz']]
        filt_orders = [2,3,4]
        window_sizes = [250,375, 500]
        execution('deep_or_riemann', list_of_freq_lim, freq_limits_names_list, filt_orders, window_sizes)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run offline BCI analysis experiments.")
    parser.add_argument("--pline", nargs='+', default=['csp'], help="The variant of pipelines used for after preprocessing. \
    This variable is a list containing the name of the variants. Options are: 'csp', 'riemann', 'deep'")
    FLAGS, unparsed = parser.parse_known_args()
    main()

    
