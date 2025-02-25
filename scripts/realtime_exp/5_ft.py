import argparse
import src.utils_finetune_closedloop as utils_finetune
from pathlib import Path

def execution(test_subject, session):
    print(f'Initializing for Finetune Transfer learning for closed loop experiments...')
    for model_type in ['best_pretrain', 'best_finetune']:
        # fine tune model for different training / validation sets
        train_trial = [[1, 2], [0, 1], [0,2]]
        val_trials = [0,2,1]

        # uncomment these lines and comment the different train val set lines to run final best model
        #train_trials = [0,1]
        #val_trial = 2

        
        # here, best_finetune is the most recent fine_tuned model, thus for session 2 this is FTsession1
        #session_num = int(session[-1])
        session_num = 1

        # model path and subjpath for future sessions
        # model_path = f"scripts/cl/final_models/{model_type}\{session}/EEGNET_{test_subject}"
        savepath_newmodel = Path(f"scripts/cl/final_models/models_for_closedloop")
        savepath_newmodel.mkdir(exist_ok=True, parents=True)

        # data path below
        testsubj_path = Path(f'./scripts/cl\intermediate_files/{session}/{test_subject}_riemann.pkl') #adjust pipeline type
        print(f'Getting {model_type} for {test_subject}..')
        for i in range(3):
            train_trials = train_trial[i]
            val_trial = val_trials[i]


            config={
            'batch_size' : 256,
            'epochs': 20,
            'receptive_field': 64, 
            'mean_pool':  8,
            'activation_type':  'elu',
            'network' : 'EEGNET',
            'model_type': model_type,
            #'model_path': model_path,
            'savepath_newmodel': savepath_newmodel,
            'test_subj_path' : testsubj_path,
            'test_subject': test_subject,
            'train_trials': train_trials,
            'val_trial': val_trial,
            'CLsession': session_num,
            'ablation': 'all',
            'seed':  42,    
            'learning_rate': 0.001,
            'filter_sizing':  8,
            'D':  2,
            'dropout': 0.25}
            utils_finetune.train(config)
    print('Finished')

def main():
    for subj in FLAGS.subject:
        print(subj)
        execution(subj, FLAGS.session)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run offline BCI analysis experiments.")
    parser.add_argument("--subject", nargs='+', default=['X06'], help="Subject.")
    parser.add_argument("--session", type=str, default='session1', help="Subject.")
    FLAGS, unparsed = parser.parse_known_args()
    main()