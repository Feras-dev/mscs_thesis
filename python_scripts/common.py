#!/usr/bin/env python
"""
This module contains common constants and functions. Invoke as needed.
"""

import glob
import os
from typing import List
import time

# default_path = "/home/feras/jetsonNanoDAQ/frames/"
# default_path = os.path.normcase(os.path.join("C:\\", "Users", "14084", "Videos"))
default_path = os.path.normcase(os.path.join(
    "C:\\", "Users", "14084", "Desktop", "thesis_datasets"))


def _print(level: int, msg: str) -> None:
    """
    print msg with proper indentation level.

    :param msg: message to print
    :type msg: str
    :param level: indentation level
    :type level: int
    """

    print(level*"\t", end="")
    print(f"{msg}")


def _abort(msg: str = "") -> None:
    """
    terminate the program.

    :param msg: message to print, defaults to an empty string
    :type msg: str, optional
    """
    print(f"{msg} exiting!")
    exit()


def _timer(start: bool = False) -> float:
    """
    Asynchronously time a duration between different points during execution.

    :param start: set to True to start timer and False to stop timer, defaults to False
    :type start: _type_, optional
    :return: if a timer has been started, the duration (in seconds) will be returned 
            upon stopping the timer. Otherwise, a negative value will be returned. 
    :rtype: float
    """

    _timer.t_i = None

    if start:
        if _timer.t_i is not None:
            print("a timer has already been started -- unable to start a timer.")
            return -1.0
        else:
            _timer.t_i = time.time()
            return 0.0  # to be ignored by user
    else:
        if _timer.t_i is not None:
            duration = (time.time() - _timer.t_i)
            _timer.t_i = None
            return duration
        else:
            print("no timer has been started -- unable to stop a timer.")
            return -1.0


def set_datasets_format() -> int:
    """
    set the appropriate dataset format. For more on this, see readme file.

    :return: 
    :rtype: int
    """

    return 0


def get_dataset_path() -> str:
    """
    get target folder absolute path containing datasets.

    :return: absolute path to directory containing datasets
    :rtype: str
    """

    path = input(
        f"please enter absolute path of root folder containing catagories with their datasets (default='{default_path}'):\n")

    if path and not path.endswith("/"):
        path += "/"
    else:
        path = default_path

    print(f"Targeting datasets under [{path}]")

    return path


def scan_for_datasets(dir: str) -> dict[str, List[str]]:
    """
    scan for folders in current directory each folder should represent a single sequential
    dataset with an epoch timestamp in seconds as the folder name.

    :param dir: absolute path to directory containing datasets
    :type dir: str
    :return: a dictionary containing each dataset format as a key, and dataset under each format as values
    :rtype:  dict[str, List[str]]
    """

    print(f"Scanning [{dir}] for datasets...", end="")

    dataset_category_list = [f for f in os.listdir(os.path.join(dir))]
    dataset_category_list.sort()

    print(f"found [{len(dataset_category_list)}] dataset catagories!")

    datasets_dict = {}

    for category_dir in dataset_category_list:
        temp_folders_list = [f for f in os.listdir(os.path.join(
            dir, category_dir)) if os.path.isdir(os.path.join(dir, category_dir, f))]
        temp_folders_list.sort()
        datasets_dict[category_dir] = temp_folders_list
        print(
            f"\tfound [{len(temp_folders_list)}] datasets of under category [{category_dir}]!")

    print("removing dataset catagories with no datasets...", end="")
    keys_to_remove = []
    for k, _ in datasets_dict.items():
        if not datasets_dict[k]:
            keys_to_remove.append(k)

    for k in keys_to_remove:
        del datasets_dict[k]

    print(f"Done removing {len(keys_to_remove)} empty catagories")

    return datasets_dict
