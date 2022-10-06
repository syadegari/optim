import pprint
import argparse
from util import import_control_file
from cv_multi import get_best_param_set


def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-c', '--control-file', help="control file")
    return parser.parse_args()


def main():
    args = parse_arguments()
    cf, path_root, _ = import_control_file(args.control_file)

    with open(f'{path_root}/runs/res.txt') as f:
        result_lines = f.readlines()

    max_kge, best_iter_num, best_param_set = get_best_param_set(result_lines, cf.params)

    pp = pprint.PrettyPrinter(indent=4)
    print('Best parameter set:')
    pp.pprint(best_param_set)
    print(f'Best KGE: {max_kge}')
    print(f'Best Iteration: {best_iter_num}')

if __name__ == '__main__':
    main()
