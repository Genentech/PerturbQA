import os
import sys
import yaml
import argparse

from utils import printt


def get_parser():
    parser = argparse.ArgumentParser("Meow meow!")

    # configuration
    parser.add_argument("--debug",
                        action="store_true",
                        help="Set flag true to load smaller dataset")
    parser.add_argument("--config_file",
                        type=str, default=None,
                        help="YAML file")
    parser.add_argument("--args_file",
                        type=str, default="args.yaml",
                        help="Dump arguments for reproducibility")
    parser.add_argument("--results_file",
                        type=str, default="results.pkl",
                        help="Save outputs here")

    # ======== data ========
    # include path to pdb protein files, splits
    parser.add_argument("--data_file",
                        type=str, default="",
                        help="Perturbation data")
    parser.add_argument("--pathway_file",
                        type=str, default="",
                        help="Pathway annotations")
    parser.add_argument("--graph_config_file",
                        type=str, default="",
                        help="List of knowledge graph paths")
    parser.add_argument("--path_cache",
                        type=str, default="",
                        help="Precomputed paths")
    parser.add_argument("--save_path",
                        type=str, default="",
                        help="Root to model checkpoints")

    # data loading
    parser.add_argument("--num_workers",
                        type=int, default=0,
                        help="data loader workers")
    parser.add_argument("--batch_size",
                        type=int, default=16,
                        help="number of graphs per batch")
    # logging
    parser.add_argument("--run_name",
                        type=str, default="kg-sanity",
                        help=("wandb experiment name"
                              "field. used for dispatcher"))
    parser.add_argument("--log_frequency",
                        type=int, default=5,
                        help="log to wandb every [n] batches")
    parser.add_argument("--val_proportion",
                        type=float, default=0.1,
                        help="proportion of train as validation")

    # ====== training ======
    parser.add_argument("--epochs",
                        type=int, default=200,
                        help="Max epochs to train")
    parser.add_argument("--min_epochs",
                        type=int, default=0,
                        help="Min epochs to train")
    parser.add_argument("--patience",
                        type=int, default=50,
                        help="Lack of validation improvement for [n] epochs")
    parser.add_argument("--metric",
                        type=str, default="Val/loss")
    parser.add_argument("--top_k",
                        type=int, default=3,
                        help="top k models to save")

    parser.add_argument("--gpu",
                        type=int, default=0,
                        help="GPU id")
    parser.add_argument("--num_gpu",
                        type=int, default=1,
                        help="number of GPUs")
    parser.add_argument("--seed",
                        type=int, default=0,
                        help="Initial seed")

    parser.add_argument("--save_pred",
                        action="store_true",
                        help="Save predictions on test set")
    parser.add_argument("--no_tqdm",
                        action="store_true",
                        help="dispatcher mode")

    # ======== model =======
    parser.add_argument("--vocab_size",
                        type=int,
                        default=1000,
                        help="number of genes")
    parser.add_argument("--num_neighbors",
                        type=int,
                        default=10,
                        help="number of neighbors in KG")
    parser.add_argument("--max_path_length",
                        type=int,
                        default=8,
                        help="max path length, excluding start/end")

    parser.add_argument("--model",
                        type=str, default="mlp",
                        choices=["mlp", "kg_gnn", "kg_tf"])
    parser.add_argument("--task",
                        type=str, default="binary",
                        choices=["binary", "ternary"])

    parser.add_argument("--embed_dim",
                        type=int,
                        default=64,
                        help="gene embedding size")
    parser.add_argument("--ffn_embed_dim",
                        type=int,
                        default=512,
                        help="ffn size")
    parser.add_argument("--n_heads",
                        type=int,
                        default=8,
                        help="attention heads for Transformer")
    parser.add_argument("--num_layers",
                        type=int,
                        default=4,
                        help="number of Transformer blocks")
    parser.add_argument("--dropout",
                        type=float, default=0.1,
                        help="dropout probability")

    # (optional)
    parser.add_argument("--checkpoint_path",
                        type=str, default="",
                        help="Checkpoint for entire model for test/finetune")

    # ==== optimization ====
    parser.add_argument("--accumulate_batches",
                        type=int, default=1,
                        help="accumulate gradient")

    # optimizer
    parser.add_argument("--lr",
                        type=float, default=1e-4,
                        help="Learning rate")
    parser.add_argument("--weight_decay",
                        type=float, default=1e-6,
                        help="L2 regularization weight")
    return parser


def parse_args():
    args = get_parser().parse_args()
    process_args(args)
    return args


def process_args(args):
    # used for dispatcher only (bash script auto-formats to config)
    ## process run_name
    if args.run_name is None:
        args.run_name = args.save_path.split("/")[-1]

    # load configuration = override specified values
    ## load config_file
    if args.config_file is not None:
        with open(args.config_file) as f:
            config = yaml.safe_load(f)
        override_args(args, config)

    # prepend output root
    args.args_file = os.path.join(args.save_path, args.args_file)
    args.results_file  = os.path.join(args.save_path, args.results_file)

    # finally load all saved parameters
    if len(args.checkpoint_path) > 0:
        if not os.path.exists(args.checkpoint_path):
            printt("invalid checkpoint_path", args.checkpoint_path)
            sys.exit(0)
        if os.path.exists(args.args_file):
            with open(args.args_file) as f:
                config = yaml.safe_load(f)
        # do not overwrite certain args
        k_to_skip = ["gpu", "debug", "num_workers"]
        for k in config:
            if "file" in k:
                k_to_skip.append(k)
            if "path" in k:
                k_to_skip.append(k)
            if "batch" in k:
                k_to_skip.append(k)
        for k in k_to_skip:
            if k in config:
                del config[k]
        override_args(args, config)


def override_args(args, config):
    """
        Recursively copy over config to args
    """
    for k,v in config.items():
        if type(v) is dict:
            override_args(args, v)
        else:
            args.__dict__[k] = v
    return args

