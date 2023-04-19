"""
Script to parse dual channel encoder signal, and apply time correlation between
camera frames and encoder signal. 
"""

# need to execute first for headless plotting
import matplotlib  # nopep8
matplotlib.use("Agg")  # nopep8

import glob
import numpy as np
import pandas as pd
import common as c
import os
import matplotlib.pylab as plt
import json

# column labels in dataset
LOGIC_ANALYZER_TIMESTAMP = "#Time (s)"
LOGIC_ANALYZER_ENCODER_CHAN_A = "DIO 1"
LOGIC_ANALYZER_ENCODER_CHAN_B = "DIO 2"
LOGIC_ANALYZER_EXTERNAL_TRIGGER_SIGNAL = "DIO 0"

# encoder specifications
ENCODER_RESOLUTION = 2048.0
ENCODER_POSITION_STEP_SIZE_DEG = 360.0/ENCODER_RESOLUTION

# don't change, append only if you know what you are doing!
SUPPORTED_DATASET_CATEGORIES = [
    "flir_blackfly_s", "rpi_cam", "sbs_encoder_data"]

# datasets to skip processing -- {<category>: [<dataset_1>, <dataset_2>, <dataset_n>]}
block_list = {"flir_blackfly_s": ["0"]}


def set_dataset_format(category: str) -> bool:
    """
    set parsing parameters based on dataset category.

    :param category: dataset category -- see SUPPORTED_DATASET_CATEGORIES above
    :type category: str
    :return: true if parameters have been set correctly, false otherwise.
    :rtype: bool
    """

    assert (category in SUPPORTED_DATASET_CATEGORIES),\
        f"given category is not supported, please contact developer (got {category})"

    global LOGIC_ANALYZER_ENCODER_CHAN_A
    global LOGIC_ANALYZER_ENCODER_CHAN_B

    match category:
        case cat if cat == SUPPORTED_DATASET_CATEGORIES[0]:
            # "flir_blackfly_s"
            LOGIC_ANALYZER_ENCODER_CHAN_A = "DIO 0"
            LOGIC_ANALYZER_ENCODER_CHAN_B = "DIO 1"

        case cat if cat == SUPPORTED_DATASET_CATEGORIES[1]:
            # "rpi_cam"
            LOGIC_ANALYZER_ENCODER_CHAN_A = "DIO 1"
            LOGIC_ANALYZER_ENCODER_CHAN_B = "DIO 2"

        case cat if cat == SUPPORTED_DATASET_CATEGORIES[2]:
            # "sbs_encoder_data"
            LOGIC_ANALYZER_ENCODER_CHAN_A = "DIO 0"
            LOGIC_ANALYZER_ENCODER_CHAN_B = "DIO 1"

        case _:
            # catch all else
            print(
                f"given category [{category}] has been added to the supported categories list, but not actually supported")
            return False

    return True


def get_header_row_index(dir: str) -> int:
    """
    return the index of the header row in the csv dataset located at the path dir.

    :param dir: absolute path to csv dataset file
    :type dir: str
    :return: index of header row, a negative value if failed to locate header row.
    :rtype: int
    """

    dataset_name = dir.split(os.sep)[-1]

    with open(dir) as f:
        line_num = 0
        for l in f:
            if l.startswith("#Time (s),"):
                return line_num
            else:
                line_num += 1

    print(f"\tFailed to locate sampling rate value from [{dir}]")
    return -1


def get_time_offset(dir: str) -> str:
    """
    get time offset as measured between trigger signal (from the Jetson Nano)
    and capturing of the first frame.

    :param dir: absolute path to csv dataset file
    :type dir: str
    :return: time offset in seconds
    :rtype: str
    """

    # read in the stats.txt file, and get the "t_diff" value
    with open(f"{dir}stats.txt") as f:
        for l in f:
            if l.startswith("t_diff"):
                print(
                    f"Found t_diff value of [{l.split('=')[1].rstrip()}] seconds")
                return l.split(" = ")[1].rstrip()

    print(f"\tFailed to locate t_diff value from [{dir}stats.txt]")
    return ""


def get_sampling_frequency_hz(dir: str) -> float:
    """
    get sampling rate in Hz

    :param dir: absolute path to csv dataset file
    :type dir: str
    :return: sampling frequency in hertz, negative value if failed ot locate frequency
    :rtype: float
    """

    dataset_name = dir.split(os.sep)[-1]

    with open(dir) as f:
        for l in f:
            if l.startswith("#Sample rate: "):
                freq_hz = float(l.split(":")[-1].rstrip().replace("Hz", ""))
                c._print(1, f"Found sampling rate value of [{freq_hz}] Hz")
                return freq_hz

    print(f"\tFailed to locate sampling rate value from [{dir}]")
    return -1.0


def convert_frequency_to_period(freq_hz: float) -> float:
    """
    convert a frequency [Hz] to a period [s].

    :param feq_hz: frequency to convert, in Hz.
    :type feq_hz: str
    :return: period in seconds.
    :rtype: str
    """

    return 1.0/freq_hz


def normalize_timestamps(df: pd.DataFrame, period_s: float) -> pd.DataFrame:
    """
    normalize timestamps in a dataframe to start from 0.0 seconds, and increments upward.

    :param df: _description_
    :type df: pd.DataFrame
    :param period_s: _description_
    :type period_s: float
    :return: _description_
    :rtype: pd.DataFrame
    """

    # convert timestamp column from str to float
    df[LOGIC_ANALYZER_TIMESTAMP] = df[LOGIC_ANALYZER_TIMESTAMP].astype(float)

    # get initial timestamp
    initial_timestamp_s = df.at[0, LOGIC_ANALYZER_TIMESTAMP]

    # add a new column with normalized timestamps
    df["timestamp_normalized_s"] = df[LOGIC_ANALYZER_TIMESTAMP] - initial_timestamp_s

    return df


def detect_initial_stable_angular_position(df: pd.DataFrame,
                                           period_s: float) -> tuple[pd.DataFrame, int, int]:
    """
    find where the encoder's most stable position, and use it as an origin
    angular position (i.e., 0 deg). 

    :param df: dataframe of dataset
    :type df: pd.DataFrame
    :return: _description_
    :rtype: int
    """

    # capture the first encoder position, to be compared with
    # the following of positions and ensure stability
    initial_position_chan_a = df.at[0, LOGIC_ANALYZER_ENCODER_CHAN_A]
    initial_position_chan_b = df.at[0, LOGIC_ANALYZER_ENCODER_CHAN_B]

    # create a boolean column that compares initial position to current position of each channel
    df["matches_initial_position"] = ((df[LOGIC_ANALYZER_ENCODER_CHAN_A] == initial_position_chan_a) & (
        df[LOGIC_ANALYZER_ENCODER_CHAN_B] == initial_position_chan_b)).map({True: 1, False: 0})

    # create a boolean column to detect initial change in position
    df["change_occurred"] = df["matches_initial_position"].shift(
    ) != df["matches_initial_position"]

    # override first entry to False
    df.at[0, "change_occurred"] = False

    # find first occurrence of positional change
    idx = (df["matches_initial_position"] < 1).idxmax()

    c._print(1,
             f"initial positions are {initial_position_chan_a} and {initial_position_chan_b}")

    c._print(
        1, f"first change in position occurred at {idx}, after {idx * period_s} seconds")

    df.drop("change_occurred", axis=1, inplace=True)

    return df


def generate_encoder_position_bitmask(df: pd.DataFrame) -> pd.DataFrame:
    """
    generate a bitmask of encoder's position ('01' for when chan_a = 0 and chan_b = 1).

    :param df: original dataframe
    :type df: pd.DataFrame
    :return: updated dataframe
    :rtype: pd.DataFrame
    """

    # create and populate a column with bitmask of current encoder position
    df["current_position_bitmask"] = df.apply(
        lambda index: bin((int(index[LOGIC_ANALYZER_ENCODER_CHAN_A]) << 1) |
                          int(index[LOGIC_ANALYZER_ENCODER_CHAN_B])).replace("0b", "").zfill(2), axis=1)

    # temperately add a shifted column for both A and B channels
    # (i.e., contains previous respective channel state)
    df["shifted_A"] = df[LOGIC_ANALYZER_ENCODER_CHAN_A].shift(
        fill_value=df.at[0, LOGIC_ANALYZER_ENCODER_CHAN_A]).astype(int)
    df["shifted_B"] = df[LOGIC_ANALYZER_ENCODER_CHAN_B].shift(
        fill_value=df.at[0, LOGIC_ANALYZER_ENCODER_CHAN_B]).astype(int)

    # create and populate a column with bitmask of previous encoder position
    df["previous_position_bitmask"] = df.apply(
        lambda index: bin((index["shifted_A"] << 1) | index["shifted_B"]).replace("0b", "").zfill(2), axis=1)

    # remove shifted columns we added earlier
    df.drop("shifted_A", axis=1, inplace=True)
    df.drop("shifted_B", axis=1, inplace=True)

    return df


def detect_direction_of_motion(df: pd.DataFrame) -> pd.DataFrame:

    bitmask_cw_pattern = ["00", "01", "11", "10"]
    detect_direction_of_motion.current_direction = ""

    # create and populate a column to indicate a change in position
    df["change_occurred"] = (df["current_position_bitmask"] ==
                             df["previous_position_bitmask"]).map({True: 0, False: 1})

    def check_direction(index: pd.Series) -> str:
        current_bitmask = index["current_position_bitmask"]
        previous_bitmask = index["previous_position_bitmask"]
        current_bitmask_index = bitmask_cw_pattern.index(current_bitmask)
        previous_bitmask_index = bitmask_cw_pattern.index(previous_bitmask)

        if index["change_occurred"] == 0:
            detect_direction_of_motion.current_direction = ""  # unchanged direction
        else:
            # sanity check
            if current_bitmask not in bitmask_cw_pattern:
                raise ValueError(
                    f"encountered an undefined bitmask value (got {index['current_position_bitmask']})")

            # possible legal change in angle based on previous position
            cw_step = bitmask_cw_pattern[(
                previous_bitmask_index+1) % len(bitmask_cw_pattern)]
            ccw_step = bitmask_cw_pattern[(
                previous_bitmask_index-1) % len(bitmask_cw_pattern)]

            # detect change in direction
            if current_bitmask == cw_step:
                detect_direction_of_motion.current_direction = "CW"
            elif current_bitmask == ccw_step:
                detect_direction_of_motion.current_direction = "CCW"
            else:
                # this will catch any illegal move, indicating a glitch (e.g. due to under-sampling)
                raise ValueError(
                    f"encountered an illegal change in position (got {index['current_position_bitmask']} @ {index['timestamp_normalized_s']} normalized timestamp)")

        return detect_direction_of_motion.current_direction

    # create and populate a column with the direction of motion
    df["direction"] = df.apply(
        lambda index: check_direction(index), axis=1)

    return df


def detect_change_in_angular_position(df: pd.DataFrame) -> pd.DataFrame:
    """

    :param df: original dataframe
    :type df: pd.DataFrame
    :return: updated dataframe
    :rtype: pd.DataFrame
    """

    detect_change_in_angular_position.last_direction = None
    detect_change_in_angular_position.current_angle = 0.0

    # track change in angle
    def track_angular_change(index):
        if index["change_occurred"] == 0:
            pass
        else:
            if index["direction"] == "CW":
                detect_change_in_angular_position.current_angle += ENCODER_POSITION_STEP_SIZE_DEG
                detect_change_in_angular_position.last_direction = "CW"
            elif index["direction"] == "CCW":
                detect_change_in_angular_position.current_angle -= ENCODER_POSITION_STEP_SIZE_DEG
                detect_change_in_angular_position.last_direction = "CCW"
            else:
                # keep incrementing/decrementing in the same direction
                if detect_change_in_angular_position.last_direction == "CW":
                    detect_change_in_angular_position.current_angle += ENCODER_POSITION_STEP_SIZE_DEG
                elif detect_change_in_angular_position.last_direction == "CCW":
                    detect_change_in_angular_position.current_angle -= ENCODER_POSITION_STEP_SIZE_DEG
                else:
                    print("WTF ARE WE HERE!!")

        return detect_change_in_angular_position.current_angle

    # create a column to keep track of the angular position
    df["angle_deg"] = df.apply(
        lambda index: track_angular_change(index), axis=1)

    # reset static variables
    detect_change_in_angular_position.current_angle = 0.0
    detect_change_in_angular_position.last_direction = None

    return df


def detect_angular_velocity(df: pd.DataFrame) -> pd.DataFrame:

    # recall, omega = delta(theta) / delta(t)

    # temperately add a shifted column for both angle and timestamps
    df["previous_angle_deg"] = df["angle_deg"].shift(
        fill_value=df.at[0, "angle_deg"]).astype(float)
    df["previous_timestamp_normalized_s"] = df["timestamp_normalized_s"].shift(
        fill_value=df.at[0, "timestamp_normalized_s"]).astype(float)

    # track change in angle
    def track_angular_velocity(index):
        angular_velocity = 0
        delta_theta = index["angle_deg"] - index["previous_angle_deg"]
        delta_t = index["timestamp_normalized_s"] - \
            index["previous_timestamp_normalized_s"]

        # protect against division by zero
        if delta_t != 0.0:
            angular_velocity = (delta_theta/delta_t)

        return angular_velocity

    # create a column to keep track of the angular velocity
    df["velocity_deg_per_s"] = df.apply(
        lambda index: track_angular_velocity(index), axis=1)

    # remove shifted columns we added earlier
    df.drop("previous_angle_deg", axis=1, inplace=True)
    df.drop("previous_timestamp_normalized_s", axis=1, inplace=True)

    return df


def trim_redundant_data_points(df: pd.DataFrame) -> pd.DataFrame:

    # remove redundant data points (i.e. samples with no change)
    df = df[df.change_occurred == 0]
    return df


def plot_time_series(df: pd.DataFrame, y: str, title: str, csv_path: str) -> None:

    plt.rcParams["figure.figsize"] = (40, 20)
    plt.rcParams["font.size"] = (22)

    plt.plot(df["timestamp_normalized_s"], df[y], "-o")
    plt.title(f"{title.replace('_', ' ')} (total data points = {df.shape[0]})")
    plt.xlabel("Time [s]")
    plt.ylabel(y.replace("_", " "))

    plt.savefig(csv_path.replace(".csv", f"_{title}.png"), dpi=100)
    plt.clf()


def output_updated_dataframe(df: pd.DataFrame, csv_path: str) -> None:
    """
    write updated dataframe as a csv file to the given out_path.
    """

    out_path = f"{csv_path.split('.')[0]}_new.csv"
    c._print(1, f"outputting dataframe to {out_path}")

    df.to_csv(out_path, float_format="%f")


def main(dataset_root_dir: str, datasets_paths: str):

    if not datasets_paths:
        c._abort("no datasets found")

    for category, datasets in datasets_paths.items():
        if not set_dataset_format(category):
            c._abort(
                f"failed to set dataset parsing parameters for category {category}")

        for dataset in datasets:
            # check if this dataset is block-listed
            if category in block_list and dataset in block_list[category]:
                c._print(
                    0, f"\nSkipping dataset [{dataset}] under category [{category}] requested.")
                continue

            c._print(0,
                     f"\nProcessing dataset [{dataset}] under category [{category}]")

            # load in time-series csv file, and index based on timestamp row
            dataset_abs_path = os.path.join(
                dataset_root_dir, category, dataset)
            c._print(1,
                     f"loading {os.path.join(dataset_abs_path, f'{dataset}.csv')}")
            df = pd.read_csv(os.path.join(dataset_abs_path, f"{dataset}.csv"),
                             skiprows=get_header_row_index(os.path.join(
                                 dataset_abs_path, f"{dataset}.csv")),
                             header=0,
                             parse_dates=[LOGIC_ANALYZER_TIMESTAMP])

            freq_hz = get_sampling_frequency_hz(
                os.path.join(dataset_abs_path, f"{dataset}.csv"))

            period_s = convert_frequency_to_period(freq_hz)

            df = detect_initial_stable_angular_position(df, period_s)

            df = normalize_timestamps(df, period_s)

            df = generate_encoder_position_bitmask(df)

            df = detect_direction_of_motion(df)

            df = detect_change_in_angular_position(df)

            df = trim_redundant_data_points(df)

            df = detect_angular_velocity(df)

            plot_time_series(df, "angle_deg", "angle_deg",
                             os.path.join(dataset_abs_path, f"{dataset}.csv"))
            plot_time_series(df, "velocity_deg_per_s", "velocity_deg_per_s",
                             os.path.join(dataset_abs_path, f"{dataset}.csv"))
            plot_time_series(df, "previous_position_bitmask", "previous_position_bitmask", os.path.join(
                dataset_abs_path, f"{dataset}.csv"))
            plot_time_series(df, "current_position_bitmask", "current_position_bitmask", os.path.join(
                dataset_abs_path, f"{dataset}.csv"))
            plot_time_series(df, "direction", "direction", os.path.join(
                dataset_abs_path, f"{dataset}.csv"))

            # output_updated_dataframe(df, os.path.join(
            #     dataset_abs_path, f"{dataset}.csv"))

            # df = trim_redundant_data_points(df)

            output_updated_dataframe(df, os.path.join(
                dataset_abs_path, f"{dataset}_reduced.csv"))

            # trigger garbage collection for loaded dataframe to save RAM
            del df

            # c._print(2, f"Done after {c._timer()} seconds.")


if __name__ == "__main__":

    dataset_root_dir = c.get_dataset_path()
    datasets_paths = c.scan_for_datasets(dataset_root_dir)

    main(dataset_root_dir, datasets_paths)

    print(f"All done!")
