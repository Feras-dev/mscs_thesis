# need to execute first for headless plotting
import matplotlib  # nopep8
matplotlib.use('Agg')  # nopep8

import os
import common as c
import glob
import matplotlib.pylab as plt


# def is_sudo():
#     '''
#     Confirm current user has elevated permission.
#     '''

#     if os.geteuid() is 0:
#         return True
#     else:
#         return False


def main():
    '''
    Entry point
    '''

    # if not is_sudo():
    #     print(f"Must invoke this script with elevated permissions (e.g., sudo)...Exiting!")
    #     exit()

    dataset_root_dir = c.get_dataset_path()
    # datasets_list = c.scan_for_datasets(dataset_root_dir)
    datasets_list = [dataset_root_dir]

    for folder in datasets_list:
        print(f"Processing [{dataset_root_dir}] dataset...", end="")

        frames_filenames_list_raw = [f for f in glob.glob(f"{dataset_root_dir}/temp-*.pgm")]

        print(f"found {len(frames_filenames_list_raw)} data points in current dataset")

        # strip timestamp only from each frame full path
        frame_timestamp_list = []
        for frame in frames_filenames_list_raw:
            if 'fps' in frame:
                continue
            frame_timestamp = frame.split(
                "/")[-1]  # remove full abs path except for timestamp
            frame_timestamp = frame_timestamp.split("-")[1]  # remove extension
            frame_timestamp_list.append(frame_timestamp[8:])
            # print(f'{frame_timestamp[8:]}')

        # split s and ns timestamp
        # frame_timestamps_s_ns_list = []
        # for frame in frame_timestamp_list:
        #     frame_timestamps_s_ns_list.append(
        #         [int(frame.split("_")[0]), int(frame.split("_")[1])]
        #     )
        # frame_timestamps_s_ns_list.sort()

        # find frequency of each second
        fps_dict = {}
        for ts in frame_timestamp_list:
            if ts in fps_dict:
                fps_dict[ts] += 1
            else:
                fps_dict[ts] = 1

        fps_lists = sorted(fps_dict.items())
        x, y = zip(*fps_lists)

        plt.figure(figsize=(15,10))
        plt.plot(x, y)
        plt.xticks(rotation = 90)
        plt.savefig(os.path.join(f"{dataset_root_dir}", "fps.png"))
        plt.close()

        print(f"Saved FPS plot to {os.path.join(dataset_root_dir, 'fps.png')}")
        print(f"Done!")


if __name__ == "__main__":
    main()
