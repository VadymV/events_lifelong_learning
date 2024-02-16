#!/usr/bin/env python3

"""
The structure of this file and some code are copied from
https://github.com/GMvandeVen/brain-inspired-replay/blob/master/compare_CIFAR100.py

Adaptations of the code are performed by Vadym Gryshchuk (vadym.gryshchuk@protonmail.com).

"""

import os
import re

import numpy as np

import incremental_learner
import options
import utils
from data_provider.utils import get_output_classes_number
from param_stamp import get_param_stamp_from_args
from settings import Settings
from visual import plt


## Function for specifying input-options and organizing / checking them
def handle_inputs():
    # Set indicator-dictionary for correctly retrieving / checking input options
    # Define input options
    parser = options.define_args(filename="_compare_NCALTECH",
                                 description='Compare performance of continual learning strategies on different '
                                             'scenarios of incremental learning on NCALTECH.')
    parser = options.add_general_options(parser)
    parser = options.add_eval_options(parser)
    parser = options.add_task_options(parser)
    parser = options.add_model_options(parser)
    parser = options.add_train_options(parser)
    parser = options.add_replay_options(parser)
    parser = options.add_bir_options(parser)
    parser = options.add_allocation_options(parser)
    # Parse and process (i.e., set defaults for unselected options) options
    args = parser.parse_args()
    options.set_defaults(args)

    settings_filepath = args.settings_file
    settings = Settings(settings_filepath)

    args.seed = settings.seed
    args.n_seeds = settings.number_seeds
    args.experiment = settings.dataset_name
    args.tasks = settings.tasks
    args.iters = settings.iterations
    args.batch = settings.batch_size
    args.lr = settings.learning_rate
    args.dg_c = settings.strength_regulator
    args.dg_si_prop = settings.gating_proportion_decoder
    args.z_dim = settings.z_dimension
    args.habituation_decay_rate = settings.decay_rate
    args.top_hab_neurons = settings.top_neurons
    args.fc_bn = settings.batch_normalization
    args.scenario = settings.scenario

    return args


def get_results(args):
    # -get param-stamp
    param_stamp = get_param_stamp_from_args(args)
    # -check whether already run, and if not do so
    if os.path.isfile("{}/dict-{}.pkl".format(args.r_dir, param_stamp)):
        print("{}: already run".format(param_stamp))
    else:
        print("{}: ...running...".format(param_stamp))
        incremental_learner.run(args)
    # -get average precisions
    fileName = '{}/prec-{}.txt'.format(args.r_dir, param_stamp)
    file = open(fileName)
    ave = float(file.readline())
    file.close()
    # -results-dict
    dict = utils.load_object("{}/dict-{}".format(args.r_dir, param_stamp))
    # -return tuple with the results
    return (dict, ave)


def collect_all(method_dict, seed_list, args, name=None):
    # -print name of method on screen
    if name is not None:
        print("\n------{}------".format(name))
    # -run method for all random seeds
    for seed in seed_list:
        args.seed = seed
        method_dict[seed] = get_results(args)
    # -return updated dictionary with results
    return method_dict


if __name__ == '__main__':

    ## Load input-arguments & set default values
    args = handle_inputs()

    ## Store gating proportion for decoder-gates
    gating_prop = args.dg_prop
    args.dg_prop = 0

    ## Add default arguments (will be different for different runs)
    args.replay = "none"
    args.distill = False
    args.feedback = False
    args.hidden = False
    args.online = False
    args.si = False
    args.xdg = False
    args.habituation = False
    args.slowness = False
    # # args.seed will also vary!

    ## If needed, create plotting directory
    if not os.path.isdir(args.p_dir):
        os.mkdir(args.p_dir)

    # -------------------------------------------------------------------------------------------------#

    # --------------------------#
    # ----- RUN ALL MODELS -----#
    # --------------------------#

    seed_list = list(range(args.seed, args.seed + args.n_seeds))

    font_scale = 1.4
    if args.scenario == 1:

        ###----"BASELINES"----###

        ## Joint
        args.replay = "offline"
        OFF = {}
        OFF = collect_all(OFF, seed_list, args, name="Batch")

        ## None
        args.replay = "none"
        NONE = {}
        NONE = collect_all(NONE, seed_list, args, name="None")

        ###----"COMPETING METHODS"----###

        args.replay = "none"
        args.distill = False

        ###----"REPLAY VARIANTS"----###

        ## GR
        args.replay = "generative"
        args.prior = "standard"
        args.per_class = False
        args.n_modes = 1
        args.feedback = False
        args.distill = False
        GR = {}
        GR = collect_all(GR, seed_list, args, name="GR")

        ## BI-R
        args.hidden = True
        args.prior = "GMM"
        args.per_class = True
        args.feedback = True
        args.dg_gates = True
        args.dg_prop = gating_prop
        args.distill = True
        BIR = {}
        BIR = collect_all(BIR, seed_list, args, name="Brain-Inspired Replay (BI-R)")

        ## BI-R & H
        args.habituation = True
        #args.habituation_decay_rate = 0.2
        BIRpH = {}
        BIRpH = collect_all(BIRpH, seed_list, args, name="BIR + H")

        # -------------------------------------------------------------------------------------------------#

        # ---------------------------#
        # ----- COLLECT RESULTS -----#
        # ---------------------------#

        prec = {}
        ave_prec = {}

        ## Create lists for all extracted <dicts> and <lists> with fixed order
        for seed in seed_list:
            i = 0
            prec[seed] = [
                [0] * args.tasks if len(OFF) == 0 else OFF[seed][i]["average"],
                [0] * args.tasks if len(NONE) == 0 else NONE[seed][i]["average"],
                [0] * args.tasks if len(GR) == 0 else GR[seed][i]["average"],
                [0] * args.tasks if len(BIR) == 0 else BIR[seed][i]["average"],
                [0] * args.tasks if len(BIRpH) == 0 else BIRpH[seed][i]["average"],
            ]
            i = 1
            ave_prec[seed] = [
                [0] * args.tasks if len(OFF) == 0 else OFF[seed][i],
                [0] * args.tasks if len(NONE) == 0 else NONE[seed][i],
                [0] * args.tasks if len(GR) == 0 else GR[seed][i],
                [0] * args.tasks if len(BIR) == 0 else BIR[seed][i],
                [0] * args.tasks if len(BIRpH) == 0 else BIRpH[seed][i],
            ]

        # -------------------------------------------------------------------------------------------------#

        # --------------------#
        # ----- PLOTTING -----#
        # --------------------#

        # name for plot
        plot_name = "summary_{}-tasks_{}-iters_{}-lr_{}-c_{}-prop_{}-z_{}".format(
            args.experiment, args.tasks, args.iters, args.lr, args.dg_c, args.dg_si_prop, args.z_dim)
        classes_tot = int(re.search(r'\d+', args.experiment).group())
        dataset_name = "N-Caltech"
        dataset_name_suffix = ""
        if classes_tot == 12:
            dataset_name_suffix = "256-12"
        elif classes_tot == 257:
            dataset_name_suffix = "256"
        elif classes_tot == 101:
            dataset_name_suffix = "101"
        else:
            dataset_name = "N-MNIST"
            dataset_name_suffix = ""
        title = "Incremental class learning on \n {}{}: {} episodes".format(dataset_name, dataset_name_suffix,
                                                                            args.tasks)
        ylabel_all = "Average precision (after all tasks)"
        ylabel = "Average precision (on tasks seen so far)"
        x_axes = BIRpH[args.seed][0]["x_task"]

        # select names / colors / ids
        names = ["Batch", "None", "GR", "BIR", "BIR + H"]
        colors = ["orange", "black", "blue", "red", "green"]
        markers = ["X", "d", "h", "s", "o"]
        ids = [0, 1, 2, 3, 4]
    else:
        ###----"BASELINES"----###

        ## Joint
        args.replay = "offline"
        OFF = {}
        OFF = collect_all(OFF, seed_list, args, name="Joint")

        ###----"COMPETING METHODS"----###

        args.replay = "none"
        args.distill = False

        ###----"REPLAY VARIANTS"----###

        ## BI-R
        args.replay = "generative"
        #args.n_modes = 1
        args.hidden = True
        args.prior = "GMM"
        args.per_class = True
        args.feedback = True
        args.dg_gates = True
        args.dg_prop = gating_prop
        args.distill = True
        BIR = {}
        BIR = collect_all(BIR, seed_list, args, name="Brain-Inspired Replay (BIR)")

        ## BI-R & H
        args.habituation = True
        BIRpH = {}
        BIRpH = collect_all(BIRpH, seed_list, args, name="BIR + H")
        args.habituation = False

        ## BI-R & SI
        args.si = True
        args.dg_prop = args.dg_si_prop
        args.si_c = args.dg_c
        BIRpSI = {}
        BIRpSI = collect_all(BIRpSI, seed_list, args, name="BIR + SI")

        ## BI-R & SI & H
        args.habituation = True
        BIRpSIpH = {}
        BIRpSIpH = collect_all(BIRpSIpH, seed_list, args, name="BIR + SI + H")

        # -------------------------------------------------------------------------------------------------#

        # ---------------------------#
        # ----- COLLECT RESULTS -----#
        # ---------------------------#

        prec = {}
        ave_prec = {}

        ## Create lists for all extracted <dicts> and <lists> with fixed order
        for seed in seed_list:
            i = 0
            prec[seed] = [
                [0] * args.tasks if len(OFF) == 0 else OFF[seed][i]["average"],
                [0] * args.tasks if len(BIR) == 0 else BIR[seed][i]["average"],
                [0] * args.tasks if len(BIRpH) == 0 else BIRpH[seed][i]["average"],
                [0] * args.tasks if len(BIRpSI) == 0 else BIRpSI[seed][i]["average"],
                [0] * args.tasks if len(BIRpSIpH) == 0 else BIRpSIpH[seed][i]["average"],
            ]
            i = 1
            ave_prec[seed] = [
                [0] * args.tasks if len(OFF) == 0 else OFF[seed][i],
                [0] * args.tasks if len(BIR) == 0 else BIR[seed][i],
                [0] * args.tasks if len(BIRpH) == 0 else BIRpH[seed][i],
                [0] * args.tasks if len(BIRpSI) == 0 else BIRpSI[seed][i],
                [0] * args.tasks if len(BIRpSIpH) == 0 else BIRpSIpH[seed][i],
            ]

        # -------------------------------------------------------------------------------------------------#

        # --------------------#
        # ----- PLOTTING -----#
        # --------------------#

        # name for plot
        plot_name = "summary_{}-tasks_{}-iters_{}-lr_{}-c_{}-prop_{}-z_{}".format(
            args.experiment, args.tasks, args.iters, args.lr, args.dg_c, args.dg_si_prop, args.z_dim)
        if args.experiment != "NMNIST":
            classes_tot = int(re.search(r'\d+', args.experiment).group())
        else:
            classes_tot = 10
        dataset_name = "N-Caltech"
        dataset_name_suffix = ""
        if classes_tot == 12:
            dataset_name_suffix = "256-12"
        elif classes_tot == 256:
            dataset_name_suffix = "256"
        elif classes_tot == 100:
            dataset_name_suffix = "101"
        else:
            dataset_name = "N-MNIST"
            dataset_name_suffix = ""
        # title = "Incremental class learning on \n {}{}: {} episodes".format(dataset_name, dataset_name_suffix,
        #                                                                     args.tasks)
        title = "Class-incremental learning: {} episodes".format(args.tasks)
        ylabel_all = "Average precision (after all tasks)"
        ylabel = "Average precision (on tasks seen so far)"
        x_axes = BIRpSI[args.seed][0]["x_task"]

        # select names / colors / ids
        # names = ["Batch", "None", "SI", "GR", "BIR", "BIR + SI", "BIR + SI + Habituation"]
        # colors = ["orange", "black", "pink", "blue", "red", "yellow", "green"]
        # markers = ["X", "d", "*", "+", "h", "s", "v", "o"]
        names = ["Batch", "BIR", "BIR + H", "BIR + SI", "BIR + SI + H"]
        colors = ["blue", "red", "green", "gray", "orange"]
        markers = ["X", "d", "h", "s", "o"]
        # ids = [0, 1, 2, 3, 4, 5, 6]
        ids = [0, 1, 2, 3, 4]

    # open pdf
    pp = plt.open_pdf("{}/{}.pdf".format(args.p_dir, plot_name))
    figure_list = []

    # bar-plot
    means = [np.mean([ave_prec[seed][id] for seed in seed_list]) for id in ids]
    if args.n_seeds > 1:
        sems = [np.sqrt(np.var([ave_prec[seed][id] for seed in seed_list]) / (len(seed_list) - 1)) for id in ids]

    # print results to screen
    print("\n\n" + "#" * 60 + "\nSUMMARY RESULTS: {}\n".format(title) + "-" * 60)
    for i, name in enumerate(names):
        if len(seed_list) > 1:
            print("{:30s} {:5.2f}  (+/- {:4.2f}),  n={}".format(name, 100 * means[i], 100 * sems[i], len(seed_list)))
        else:
            print("{:34s} {:5.2f}".format(name, 100 * means[i]))
    print("#" * 60)

    # line-plot
    ave_lines = []
    sem_lines = []
    for id in ids:
        new_ave_line = []
        new_sem_line = []
        for line_id in range(len(prec[args.seed][id])):
            all_entries = [prec[seed][id][line_id] for seed in seed_list]
            new_ave_line.append(np.mean(all_entries))
            if args.n_seeds > 1:
                new_sem_line.append(np.sqrt(np.var(all_entries) / (len(all_entries) - 1)))
        ave_lines.append(new_ave_line)
        sem_lines.append(new_sem_line)
    ylim = (0, 0.8)
    class_per_task = int(get_output_classes_number(args.experiment) / args.tasks)
    figure = plt.plot_lines(ave_lines, x_axes=[class_per_task * i for i in x_axes],
                            line_names=names, colors=colors, title=title,
                            xlabel="Number of classes learned so far",
                            ylabel="Test accuracy",
                            list_with_errors=sem_lines if args.n_seeds > 1 else None, ylim=ylim, markers=markers,
                            font_scale=font_scale)
    figure_list.append(figure)

    # add figures to pdf
    for figure in figure_list:
        pp.savefig(figure, bbox_inches="tight")

    # close the pdf
    pp.close()

    # Print name of generated plot on screen
    print("\nGenerated plot: {}/{}.pdf\n".format(args.p_dir, plot_name))
