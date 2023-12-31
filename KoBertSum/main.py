import os
import sys
import time
import argparse
#from src.others.test_rouge_score import RougeScorer

PROBLEM = 'ext'
PROJECT_DIR = os.getcwd()
   
DATA_DIR = f'{PROJECT_DIR}/{PROBLEM}/data'
RAW_DATA_DIR = DATA_DIR + '/raw'
JSON_DATA_DIR = DATA_DIR + '/json_data'
BERT_DATA_DIR = DATA_DIR + '/bert_data' 
LOG_DIR = f'{PROJECT_DIR}/{PROBLEM}/logs'
LOG_PREPO_FILE = LOG_DIR + '/preprocessing.log' 

MODEL_DIR = f'{PROJECT_DIR}/{PROBLEM}/models' 
RESULT_DIR = f'{PROJECT_DIR}/{PROBLEM}/results' 

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-task", default='test', type=str, choices=['install', 'make_data', 'train', 'valid', 'test'])
    parser.add_argument("-n_cpus", default='2', type=str)
    parser.add_argument("-target_summary_sent", default='abs', type=str)
    parser.add_argument("-visible_gpus", default='0', type=str)
    
    parser.add_argument("-train_from", default=None, type=str)
    parser.add_argument("-model_path", default=None, type=str)
    parser.add_argument("-test_from", default=None, type=str)
    parser.add_argument("-now", default=None, type=str)
    args = parser.parse_args()
 
    now = args.now

    # python main.py -task install
    if args.task == 'install':
        os.chdir(PROJECT_DIR)
        os.system("pip install -r requirements.txt")
        os.system("pip install Cython")
        os.system("python src/others/install_mecab.py")
        os.system("pip install -r requirements_prepro.txt")

    # python main.py -task make_data -n_cpus 2
    elif args.task == 'make_data':
        os.chdir(PROJECT_DIR + '/src')
        os.system("python make_data.py -task df")
        os.system(f"python make_data.py -task train_bert -target_summary_sent ext -n_cpus {args.n_cpus}")
        os.system(f"python make_data.py -task test_bert -n_cpus {args.n_cpus}")

    elif args.task == 'train':
        """
        파라미터별 설명은 trainer_ext 참고
        """
        os.chdir(PROJECT_DIR + '/src')
        
        do_str = f"python train.py -task ext -mode train"  \
            + f" -bert_data_path {BERT_DATA_DIR}/train_ext"  \
            + f" -save_checkpoint_steps 500 -visible_gpus 0 -report_every 100 -encoder baseline"

        param = " -ext_dropout 0.1 -lr 2e-3 -warmup_steps 8000 -batch_size 512 -accum_count 2 -train_steps 10000  -use_interval true"  
        do_str += param
  
        if args.train_from is None:
            os.system(f'mkdir {MODEL_DIR}/{now}')
            do_str += f" -model_path {MODEL_DIR}/{now}"  \
                + f" -log_file {LOG_DIR}/train_{now}.log"
        else:
            model_folder, model_name = args.train_from.rsplit('/', 1)
            do_str += f" -train_from {MODEL_DIR}/{args.train_from}"  \
                + f" -model_path {MODEL_DIR}/{model_folder}"  \
                + f" -log_file {LOG_DIR}/train_{model_folder}.log"

        print(do_str)
        os.system(do_str)

    # python main.py -task valid -model_path 1209_1236
    elif args.task == 'valid':
        os.chdir(PROJECT_DIR + '/src')
        
        os.system(f"python train.py -task ext -mode validate -test_all True"
            + f" -model_path {MODEL_DIR}/{args.model_path}"
            + f" -bert_data_path {BERT_DATA_DIR}/valid_ext"
            + f" -result_path {RESULT_DIR}/result_{args.model_path}"
            + f" -log_file {LOG_DIR}/valid_{args.model_path}.log"
            + f" -test_batch_size 256  -batch_size 512"
            + f" -sep_optim true -use_interval true -visible_gpus {args.visible_gpus}"
            + f" -max_pos 512 -max_length 150 -alpha 0.95 -min_length 15"
            + f" -report_rouge False"
            + f" -max_tgt_len 140"
        )

    # python main.py -task test -test_from 1209_1236/model_step_7000.pt -visible_gpus 0
    elif args.task == 'test':
        os.chdir(PROJECT_DIR + '/src')
        
        model_folder, model_name = args.test_from.rsplit('/', 1)
        model_name = model_name.split('_', 1)[1].split('.')[0]
        os.system(f"""\
            python train.py -task ext -mode test \
            -test_from {MODEL_DIR}/{args.test_from} \
            -bert_data_path {BERT_DATA_DIR}/test \
            -result_path {RESULT_DIR}/result_{model_folder} \
            -log_file {LOG_DIR}/test_{model_folder}.log \
            -test_batch_size 8  -batch_size 512 \
            -sep_optim true -use_interval true -visible_gpus {args.visible_gpus} \
            -report_rouge False \
            -max_tgt_len 140
        """)
        os.system(f"python make_submission.py result_{model_folder}_{model_name}.candidate")

