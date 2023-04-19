'''
Script to analyze jitter in camera fps.
'''

import common as c

def calculate_jitter_in_camera(datasets_list: list[str]):
    """_summary_

    :param datasets_list: _description_
    :type datasets_list: list[str]
    """


def main():
    dataset_root_dir = c.get_dataset_path()
    datasets_list = c.scan_for_datasets(dataset_root_dir)
    

    return

if __name__ == "__main__":
    main()
