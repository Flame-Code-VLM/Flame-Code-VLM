import argparse
from evaluator.gen.index import run_gen
from evaluator.gen.index_multi_thrd import run_gen_multi_thrd
from evaluator.eval.index import run_eval
import time


def parse_arguments():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--gen_num', type=int)
    parser.add_argument('--gen_only', action='store_true')
    parser.add_argument('--gen_with_num_thrds', type=int)
    parser.add_argument('--eval_only', action='store_true')
    parser.add_argument('--gen_and_eval', action='store_true')
    parser.add_argument('--gen_img_only', action='store_true')
    parser.add_argument('--exp_num', type=int)
    parser.add_argument('--model_path', type=str)
    parser.add_argument('--chrome_path', type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    gen_func = run_gen_multi_thrd if args.gen_with_num_thrds > 1 else run_gen

    if args.gen_only:
        gen_func(args.gen_num, args.model_path, args.exp_num,
                 args.gen_with_num_thrds, args.chrome_path, args.gen_img_only)
    elif args.eval_only:
        run_eval(args.model_path)
    elif args.gen_and_eval:
        gen_func(args.gen_num, args.model_path, args.exp_num,
                 args.gen_with_num_thrds, args.chrome_path, args.gen_img_only)
        time.sleep(5)
        run_eval(args.model_path)

    print('done')
