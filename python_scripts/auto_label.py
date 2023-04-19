"""
script to detect the tilt angle of a pendulum, and label each frame with the actual angle.
"""

import cv2
import numpy as np
import natsort as ns
import os
import sys
import shapely
from shapely.geometry import Point, LineString
from shapely.ops import split
import time

welcome_str = f">> Using:\n\t " +\
    f"- Python v{sys.version} \n\t " +\
    f"- OpenCV v{cv2.__version__} \n\t " +\
    f"- numpy v{np.__version__} \n\t " +\
    f"- shapely v{shapely.__version__} \n\t " +\
    f"- natsort v{ns.__version__}\n"

# variables used to detect and set ROI
roi_x, roi_y, roi_r = None, None, 1


def select_pivot(list_frames_abs_path):
    select_pivot.src = cv2.imread(list_frames_abs_path[0])
    select_pivot.win_name = "Select CoM of pivot"
    select_pivot.modified_frame = select_pivot.src.copy()
    selected_toi = ('none', 'none', 'none')

    cv2.imshow(select_pivot.win_name, select_pivot.src)

    print(">> click on CoM of the pivot point manually on the image shown. Use the following controls:\n\t" +
          "mouse left button = record coordinates of CoM\n\t" +
          "'z' = increase diameter\n\t" +
          "'x' = decrease diameter\n\t" +
          "ENTER key = proceed to the next step\n\t" +
          "'s' = save frame to disk\n\t" +
          "'c' = clear recorded CoM\n\t" +
          "ESC key = quit\n")

    def update_roi():
        global roi_x, roi_y, roi_r
        select_pivot.modified_frame = select_pivot.src.copy()

        print(f"({roi_x}, {roi_y}), r = {roi_r}")

        # displaying the selected pivot ROI
        cv2.circle(select_pivot.modified_frame,
                   (roi_x, roi_y), roi_r, (0, 255, 0), 2)
        # draw the center of the circle
        cv2.circle(select_pivot.modified_frame,
                   (roi_x, roi_y), 2, (0, 0, 255), 3)

        cv2.imshow(select_pivot.win_name, select_pivot.modified_frame)

    def click_event(event, x, y, flags, params):
        global roi_x, roi_y

        # checking for left mouse clicks
        if event == cv2.EVENT_LBUTTONDOWN:
            # update coordinates
            roi_x, roi_y = x, y
            update_roi()

    # set up the mouse clicks event handler
    cv2.setMouseCallback("Select CoM of pivot", click_event)

    while True:
        user_input = cv2.waitKey(0) & 0xFF
        if user_input in [ord('z'), ord('x')]:
            global roi_r
            if user_input == ord('x'):
                # decrease circle diameter
                if roi_r > 0:
                    roi_r = roi_r - 1
            else:
                # increase circle diameter
                roi_r = roi_r + 1
            update_roi()

        elif user_input == ord('s'):
            # dump current images to memory
            save_to_path = input(
                ">> Enter absolute path of directory to save frames under:\n<<")
            cv2.imwrite(os.path.join(
                save_to_path, select_pivot.win_name)+'.jpg', select_pivot.modified_frame)
            print(
                f">> saved frame under {save_to_path}")

        elif user_input == ord('c'):
            # clear all drawn ROI
            cv2.imshow(select_pivot.win_name, select_pivot.src)

        elif user_input == 13:  # ENTER key
            # proceed to next step in script
            if roi_x and roi_y:
                cv2.destroyAllWindows()
                print(">> ROI selection recorded!")
                return
            else:
                print(
                    ">> Can't proceed without ROI parameters! If you want to quit, press ESC key")

        elif user_input == 27:  # ESC key
            # quit
            cv2.destroyAllWindows()
            exit(">> User request exiting during pivot manual selection")

        else:
            pass


def check_for_lines_intersection_with_roi(list_of_lines, x_max, y_max):

    # Define the ROI as Shapely objects
    roi_com = Point(roi_x, roi_y)
    roi = roi_com.buffer(roi_r)

    roi_intersected_lines = []
    counter = 0

    for line in list_of_lines:
        counter += 1
        for x_i, y_i, x_f, y_f in line:
            # define the line equation based on given cartesian coordinates

            # since a vertical line's slop is undefined, we need to cover that corner case to avoid division by zero
            if (x_f - x_i) != 0:
                # calculate line equation parameters to extended the line
                m = ((y_f - y_i) / (x_f - x_i))  # slope
                b = y_i - m * x_i   # y-intercept

                # extend the line to cover the full frame
                x_i_new = 0
                y_i_new = int(b)
                x_f_new = x_max
                y_f_new = int(m * x_max + b)
            else:
                # line is vertical, so just extend it vertically to cover the full frame
                x_i_new = x_i
                x_f_new = x_f

                if y_i < y_f:
                    y_i_new = 0
                    y_f_new = y_max
                else:
                    y_i_new = y_max
                    y_f_new = 0

            # define the extended hough line as a Shapely object
            line = LineString([(x_i_new, y_i_new), (x_f_new, y_f_new)])

            # determine if the extended line intersects with the circle
            if not line.intersection(roi).is_empty:
                roi_intersected_lines.append([x_i, y_i, x_f, y_f])

    return roi_intersected_lines


def detect_equilibrium(list_frames_abs_path):

    win_1_title = "Source"
    win_2_title = "All Hough Lines"
    win_3_title = "Lines that intersect with pivot point"
    frame_num = 0

    for frame in list_frames_abs_path:
        print(f">> Processing frame #{frame_num}")
        frame_num += 1

        src = cv2.imread(frame)
        gray_img = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

        img_canny = cv2.Canny(gray_img, 50, 100, apertureSize=3)
        img_cannyL2 = cv2.Canny(
            gray_img, 50, 150, apertureSize=3, L2gradient=True)

        linesP = cv2.HoughLinesP(image=img_canny,
                                 rho=1,
                                 theta=np.pi / 180, # find limitation
                                 threshold=80,
                                 lines=None,
                                 minLineLength=50,
                                 maxLineGap=5)

        if linesP is not None:
            # print(f'>> found {len(linesP)} lines')
            y_max, x_max = src.shape[:2]
            linesP_filtered = check_for_lines_intersection_with_roi(
                linesP, x_max, y_max)
            # print(
            #     f'>> found {len(linesP_filtered)} lines that intersect with selected ROI')

            src_all_hough_lines = src.copy()
            src_intersected_lines = src.copy()

            for i in range(0, len(linesP)):
                l = linesP[i][0]
                cv2.line(src_all_hough_lines, (l[0], l[1]), (l[2], l[3]),
                         (0, 0, 255), 1, cv2.LINE_AA)

            for line in linesP_filtered:
                x_i, y_i, x_f, y_f = line[0], line[1], line[2], line[3]
                cv2.line(src_intersected_lines, (x_i, y_i), (x_f, y_f),
                         (0, 0, 255), 1, cv2.LINE_AA)

            cv2.imshow(win_1_title, src)
            cv2.imshow(win_2_title, src_all_hough_lines)
            cv2.imshow(win_3_title, src_intersected_lines)
            
            timeout = time.time() + 0.1   # 0.1 second per frame

            while time.time() < timeout:
                user_input = cv2.waitKey(10) & 0xFF
                if user_input == ord('s'):
                    # dump current images to memory
                    save_to_path = input(
                        ">> Enter absolute path of directory to save frames under:\n<<")
                    cv2.imwrite(os.path.join(
                        save_to_path, win_1_title)+'.jpg', src)
                    cv2.imwrite(os.path.join(
                        save_to_path, win_2_title)+'.jpg', src_all_hough_lines)
                    cv2.imwrite(os.path.join(
                        save_to_path, win_3_title)+'.jpg', src_intersected_lines)
                    print(f">> saved images under {save_to_path}")

                else:
                    # proceed to next step in script
                    cv2.destroyAllWindows()
                    break

        else:
            print(f">> failed to detect any lines in {frame}")


def scan_folder_for_images(root_dir_path, verbose=False):
    supported_formats = ['.ppm', '.pgm', '.png', '.jpeg', '.jpg']

    # Get a list of all items in the root directory, sort files "naturally" by their name
    all_files = ns.os_sorted(os.listdir(root_dir_path))

    # Filter the list to only include files with supported formats
    frames = []
    for file in all_files:
        _, file_extension = os.path.splitext(file)

        if file_extension in supported_formats:
            frames.append(os.path.join(root_dir_path, file))
            if verbose:
                print(f'found frame: {os.path.join(root_dir_path, file)}')

    print(f">> found a total of {len(frames)} frames.")

    return frames


def estimate_angle()


def main():

    print(welcome_str)
    # The parent directory that contains the frames in the same dataset
    root_dir_path = input(
        '>> Enter absolute path of root directory containing sub-sets of frames:\n<<')

    # scan folder for images
    frames = scan_folder_for_images(root_dir_path)

    if len(frames) < 1:
        print(f'No frames found under {root_dir_path}')
        exit("exiting")

    # allow user ot manually select the center of the pivot point
    select_pivot(frames)

    # detect pendulum at equilibrium position
    detect_equilibrium(frames)

    # start estimating angle
    


if __name__ == '__main__':
    main()
