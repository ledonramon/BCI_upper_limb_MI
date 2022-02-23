import copy
import glob
import os
import shutil
import time
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import dump, load
from mne.decoding import CSP
from pyriemann.classification import MDM, FgMDM
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from scipy import signal, stats
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.ensemble import RandomForestClassifier as RFC
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

def init_filters(freq_lim, sample_freq, filt_type = 'bandpass', order=2, state_space=True):
    filters = []
    z = []
    if state_space:
        for f in range(freq_lim.shape[0]):
            A, B, C, D, Xnn  = init_filt_coef_statespace(freq_lim[f], fs=sample_freq, filtype=filt_type, order=order)
            filters.append([A, B, C, D, Xnn ])
    else:
        for f in range(freq_lim.shape[0]):
            b, a = init_filt_coef(freq_lim[f], fs=sample_freq, filtype=filt_type, order=order)
            filters.append([b, a])
            # some z stuff
    return filters, z

def init_filt_coef_statespace(cuttoff, fs, filtype, order,len_selected_electrodes=27):
    if filtype == 'lowpass':
        b,a = signal.butter(order, cuttoff[0]/(fs/2), filtype)
    elif filtype == 'bandpass':
        b,a = signal.butter(order, [cuttoff[0]/(fs/2), cuttoff[1]/(fs/2)], filtype)
    elif filtype == 'highpass':
        b,a = signal.butter(order, cuttoff[0]/(fs/2), filtype)
    # getting matrices for the state-space form of the filter from scipy and init state vector
    A, B, C, D = signal.tf2ss(b,a)
    Xnn = np.zeros((1,len_selected_electrodes,A.shape[0],1))
    #print(Xnn[0,2])
    #print('h')
    return A, B, C, D, Xnn 

def init_filt_coef(cuttoff, fs, filtype, order):
    if filtype == 'lowpass':
        b,a = signal.butter(order, cuttoff[0]/(fs/2), filtype)
    elif filtype == 'bandpass':
        b,a = signal.butter(order, [cuttoff[0]/(fs/2), cuttoff[1]/(fs/2)], filtype)
    elif filtype == 'highpass':
        b,a = signal.butter(order, cuttoff[0]/(fs/2), filtype)
    # getting matrices for the state-space form of the filter from scipy.
    return b, a 

def apply_filter(sig, b, a, zi):
    # Substract mean as the signal has to be centered at zero before filtering.
    # https://stackoverflow.com/questions/69728320/setting-parameters-for-a-butterworth-filter
    sig -= sig.mean()
    #NOTE: when I want to change back to filfilt or to lfilter, only have to comment/uncomment
    filt_sig = signal.filtfilt(b, a, sig)
    #filt_sig, zi = signal.lfilter(b, a, sig, zi=zi)
    return filt_sig, zi

def apply_filter_statespace(sig, A, B, C, D, Xnn):
    # Substract mean for centering around 0
    # as the signal has to be centered at zero before filtering (for better comparison in plots).
    # https://stackoverflow.com/questions/69728320/setting-parameters-for-a-butterworth-filter
    sig -= sig.mean()
    # sig = min_max_scale(sig)
    # State space with scipy's matrices
    filt_sig = np.array([])
    for sample in sig: 
        filt_sig = np.append(filt_sig, C.dot(Xnn) + D * sample)
        Xnn = A@Xnn + B * sample
    return filt_sig, Xnn

def pre_processing(segment,selected_electrodes_names ,filters, sample_duration, freq_limits_names,z, state_space=True):
    curr_segment = segment
    outlier = 0
    #TODO add notch filter 50Hz for Unicorn BCI experiments??? --> is needed?
    # 1 OUTLIER DETECTION --> https://www.mdpi.com/1999-5903/13/5/103/html#B34-futureinternet-13-00103
    for i, j in curr_segment.iterrows():
        if stats.kurtosis(j) > 4*np.std(j) or (abs(j - np.mean(j)) > 125).any():
            outlier +=1
    # 2 APPLY COMMON AVERAGE REFERENCE (CAR) per segment:    
    curr_segment -= curr_segment.mean()
    # 3 FILTERING filter bank / bandpass
    if state_space == True:
        segment_filt, filters = filter_1seg_statespace(curr_segment, selected_electrodes_names, filters, sample_duration, 
        freq_limits_names)
    else:
        segment_filt, z = filter_1seg(curr_segment, selected_electrodes_names, filters, sample_duration, freq_limits_names, z)

    if outlier > 0:
        return 0, outlier, filters
    else:
        return segment_filt, outlier, filters

def filter_1seg_statespace(segment, selected_electrodes_names,filters, sample_duration, freq_limits_names):
    # filters dataframe with 1 segment of 1 sec for all given filters
    # returns a dataframe with columns as electrode-filters
    filter_results = {}
    segment = segment.transpose()
    for electrode in range(len(selected_electrodes_names)):
        for f in range(len(filters)):
            A, B, C, D, Xnn = filters[f] 
            filter_results[selected_electrodes_names[electrode] + '_' + freq_limits_names[f]] = []
            if segment.shape[0] == sample_duration:      
                # apply filter ánd update Xnn state vector       
                # print(f'this should be a vector of size len(A): {Xnn[0,electrode]}. Boem.') 
                filt_result_temp, Xnn[0,electrode] = apply_filter_statespace(segment[selected_electrodes_names[electrode]], 
                A, B, C, D, Xnn[0,electrode])         
                for data_point in filt_result_temp:
                    filter_results[selected_electrodes_names[electrode] + '_' + freq_limits_names[f]].append(data_point) 
            filters[f] = [A, B, C, D, Xnn]
            #print('made it to here')
    filtered_dataset = pd.DataFrame.from_dict(filter_results).transpose()    
    return filtered_dataset, filters
  
def filter_1seg(segment, selected_electrodes_names,filters, sample_duration, freq_limits_names, z):
    # filters dataframe with 1 segment of 1 sec for all given filters
    # returns a dataframe with columns as electrode-filters
    filter_results = {}
    for electrode in selected_electrodes_names:
        for f in range(len(filters)):
            b, a = filters[f] 
            zi = z[f]
            filter_results[electrode + '_' + freq_limits_names[f]] = []
            if segment.shape[0] == sample_duration:                
                filt_result_temp, zi = apply_filter(segment[electrode],b,a,zi)            
                for data_point in filt_result_temp:
                    filter_results[electrode + '_' + freq_limits_names[f]].append(data_point) 
                z[f] = zi #update z
    filtered_dataset = pd.DataFrame.from_dict(filter_results)        
    return filtered_dataset, z
    
def segmentation_all(dataset,sample_duration):
    segments = []
    labels = []
    true = 0
    false = 0
    dataset_c = copy.deepcopy(dataset)

    for _, segment in dataset_c.groupby(np.arange(len(dataset)) // sample_duration):
        segments.append(segment.iloc[:,:-1].transpose())
        labels.append(segment['label'].mode()) 
        if segment['label'].mode()[0] == 1:
            true +=1
        else:
            false +=1
    print(f'true:{true}, false: {false}')
    ''' #below is code for segmentation with overlap. But as I use state space filters 
    # this doesnt work rn I think.
    window_size = sample_duration
    window_hop = 100
    start_frame = sample_duration 
    end_frame = window_hop * math.floor(float(dataset_c.shape[0]) / window_hop)

    for frame_idx in range(start_frame, end_frame+window_hop, window_hop):
        segments.append(dataset_c.iloc[frame_idx-window_size:frame_idx, :-1].transpose())
        labels.append(dataset_c.iloc[frame_idx-window_size:frame_idx, -1].mode()[0]) 
        if labels[-1] == 1:
            true +=1
        elif labels[-1] == 0:
            false +=1
    print(f'true:{true}, false: {false}')
    '''
    return segments, labels

def init_pipelines(pipeline_name = ['csp']):
    pipelines = {}
    if 'csp' in pipeline_name:
    # standard / Laura's approach + variations
        for n_comp in [8, 10, 11, 12, 13]:
            pipelines["csp+lda_n" + str(n_comp)] = Pipeline(steps=[('csp', CSP(n_components=n_comp)), 
                                            ('lda', LDA())])
                                            
            # Using Ledoit-Wolf lemma shrinkage, which is said to outperform standard LDA
            pipelines["csp+s_lda_n" + str(n_comp)] = Pipeline(steps=[('csp', CSP(n_components=n_comp)), 
                                            ('slda', LDA(solver = 'lsqr', shrinkage='auto'))])
            
            pipelines["csp+svm_n" + str(n_comp)] = Pipeline(steps=[('csp', CSP(n_components=n_comp)), 
                                                ('svm', SVC())])

            pipelines["csp+rf_n" + str(n_comp)] = Pipeline(steps=[('csp', CSP(n_components=n_comp)), 
                                                ('rf', RFC(random_state=42))])
    
    # Riemannian approaches
    if 'riemann' in pipeline_name:
        pipelines["tgsp+svm"] = Pipeline(steps=[('cov', Covariances("oas")), 
                                            ('tg', TangentSpace(metric="riemann")),
                                            ('svm', SVC(gamma = 0.05, C=10))])
                                
        pipelines["tgsp+rf"] = Pipeline(steps=[('cov', Covariances("oas")), 
                                            ('tg', TangentSpace(metric="riemann")),
                                            ('rf', RFC(random_state=42))])
        
        # Minimum distance to riemanian mean (MDRM) --> directly on the manifold --> parameter-free!
        pipelines["mdm"] = Pipeline(steps=[('cov', Covariances("oas")), 
                                    ('mdm', MDM(metric="riemann"))])
        pipelines["fgmdm"] = Pipeline(steps=[('cov', Covariances("oas")), 
                                    ('mdm', FgMDM(metric="riemann"))])

    return pipelines

def init_pipelines_grid(pipeline_name = ['csp']):
    pipelines = {}
    if 'csp' in pipeline_name:
        pipe = Pipeline(steps=[('csp', CSP()), ('svm', SVC())])
        param_grid = {"csp__n_components": [10,11,12],
            "svm__C": [1, 10],
            "svm__gamma": [0.1, 0.01, 0.001]
                }
        pipelines["csp+svm"] = GridSearchCV(pipe, param_grid, cv=4, scoring='accuracy',n_jobs=-1)

        pipe = Pipeline(steps=[('csp', CSP()), ('rf', RFC(random_state=42))])
        param_grid = {"csp__n_components": [10,11,12],
            "rf__min_samples_leaf": [1, 2],
            "rf__n_estimators": [50, 100, 200],
            "rf__criterion": ['gini', 'entropy']}
        pipelines["csp+rf"] = GridSearchCV(pipe, param_grid, cv=4, scoring='accuracy',n_jobs=-1)

    if 'riemann' in pipeline_name:  
        pipe = Pipeline(steps=[('cov', Covariances("oas")), 
                                            ('tg', TangentSpace(metric="riemann")),
                                            ('svm', SVC())])
        param_grid = {"svm__C": [0.1, 1, 10, 100],
            "svm__gamma": [0.1, 0.01, 0.001],
            "svm__kernel": ['rbf', 'linear']
                }
        pipelines["tgsp+svm"] = GridSearchCV(pipe, param_grid, cv=4, scoring='accuracy',n_jobs=-1)  

        pipe = Pipeline(steps=[('cov', Covariances("oas")), 
                                            ('tg', TangentSpace(metric="riemann")),
                                            ('rf', RFC(random_state=42))])
        param_grid = {"rf__min_samples_leaf": [1, 2, 50, 100],
            "rf__n_estimators": [10, 50, 100, 200],
            "rf__criterion": ['gini', 'entropy']}
        pipelines["tgsp+rf"] = GridSearchCV(pipe, param_grid, cv=4, scoring='accuracy',n_jobs=-1)
    return pipelines  

def grid_search_execution(X_np, y_np, chosen_pipelines, clf):
    start_time = time.time()
    preds = np.zeros(len(y_np))
    X_train, X_test, y_train, y_test = train_test_split(X_np, y_np, test_size=0.2, shuffle=True, random_state=42)
    chosen_pipelines[clf].fit(X_train, y_train)
    print(chosen_pipelines[clf].best_params_)
    preds = chosen_pipelines[clf].predict(X_test)
    acc = np.mean(preds == y_test)
    print("Classification accuracy: %f " % (acc))
    elapsed_time = time.time() - start_time
    return acc, elapsed_time, chosen_pipelines

def plot_dataset(data_table, columns, match='like', display='line'):
    names = list(data_table.columns)

    # Create subplots if more columns are specified.
    if len(columns) > 1:
        f, xar = plt.subplots(len(columns), sharex=True, sharey=False)
    else:
        f, xar = plt.subplots()
        xar = [xar]

    f.subplots_adjust(hspace=0.4)

    # Pass through the columns specified.
    for i in range(0, len(columns)):
        xar[i].set_prop_cycle(color=['b', 'g', 'r', 'c', 'm', 'y', 'k'])
        # if a column match is specified as 'exact', select the column name(s) with an exact match.
        # If it's specified as 'like', select columns containing the name.

        # We can match exact (i.e. a columns name is an exact name of a columns or 'like' for
        # which we need to find columns names in the dataset that contain the name.
        if match[i] == 'exact':
            relevant_cols = [columns[i]]
        elif match[i] == 'like':
            relevant_cols = [name for name in names if columns[i] == name[0:len(columns[i])]]
        else:
            raise ValueError("Match should be 'exact' or 'like' for " + str(i) + ".")

        max_values = []
        min_values = []

        point_displays = ['+', 'x'] #'*', 'd', 'o', 's', '<', '>']
        line_displays = ['-'] #, '--', ':', '-.']
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k']


        # Pass through the relevant columns.
        for j in range(0, len(relevant_cols)):
        
            # Create a mask to ignore the NaN and Inf values when plotting:
            mask = data_table[relevant_cols[j]].replace([np.inf, -np.inf], np.nan).notnull()
            max_values.append(data_table[relevant_cols[j]][mask].max())
            min_values.append(data_table[relevant_cols[j]][mask].min())

            # Display point, or as a line
            if display[i] == 'points':
                xar[i].plot(data_table.index[mask], data_table[relevant_cols[j]][mask],
                            point_displays[j%len(point_displays)])
            else:
                xar[i].plot(data_table.index[mask], data_table[relevant_cols[j]][mask],
                            line_displays[j%len(line_displays)])

        xar[i].tick_params(axis='y', labelsize=10)
        xar[i].legend(relevant_cols, fontsize='xx-small', numpoints=1, loc='upper center',
                        bbox_to_anchor=(0.5, 1.3), ncol=len(relevant_cols), fancybox=True, shadow=True)

        xar[i].set_ylim([min(min_values) - 0.1*(max(max_values) - min(min_values)),
                            max(max_values) + 0.1*(max(max_values) - min(min_values))])

    # Make sure we get a nice figure with only a single x-axis and labels there.
    plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
    plt.xlabel('time')
    plt.show()