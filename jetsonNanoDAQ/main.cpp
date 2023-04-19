/**
 * @file main.cpp
 * @author Feras Alshehri (falshehri@mail.csuchico.edu)
 * @brief entry point of Jetson Nano DAQ.
 * @version 0.1
 * @date 2022-09-30
 *
 * @build_with:
 * g++ main.cpp jetsonGPIO/mpio_controller.o -o main `pkg-config --libs opencv4` -I
 * /usr/include/opencv4/
 *
 * @copyright Copyright (c) 2022
 *
 */

#include <fstream>
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/videoio.hpp>
#include <string>
#include <sys/stat.h> // for mkdir()
#include <sys/types.h>
#include <time.h>

#include "jetsonGPIO/mpio_controller.h"

#define NUM_OF_FRAMES 1300
#define SAVE_RGB false // false will save grayscale frames only
#define USE_GSTREAMER 1
// gStreamer parameters
#define CAPTURE_WIDTH 1280 // 1280
#define CAPTURE_HEIGHT 720 // 720
#define DISPLAY_WIDTH CAPTURE_WIDTH
#define DISPLAY_HEIGHT CAPTURE_HEIGHT
#define FRAMERATE 60.0
#define FLIP_MODE 0

/**
 * @brief Get timestamp in seconds (epoch)
 *
 * @return std::string epoch in seconds
 */
std::string get_time_s(void) {
    struct timespec curr_time_ns = {};

    clock_gettime(CLOCK_REALTIME, &curr_time_ns);

    return std::to_string(curr_time_ns.tv_sec);
}

/**
 * @brief Get timestamp in seconds and nanoseconds (epoch)
 *
 * @return std::string epoch time in seconds and nano seconds (s_ns)
 */
std::string get_time_ns(std::string sep = "_") {
    struct timespec curr_time_ns = {};

    clock_gettime(CLOCK_REALTIME, &curr_time_ns);

    return std::to_string(curr_time_ns.tv_sec) + sep +
           std::to_string(curr_time_ns.tv_nsec);
}

/**
 * @brief this is needed to load a CSI camera configurations via gStreamer.
 * source: https://github.com/JetsonHacksNano/CSI-Camera/blob/master/simple_camera.cpp
 *
 * @param capture_width width of captured frame.
 * @param capture_height height of captured frame.
 * @param display_width width of frame to be displayed.
 * @param display_height width of frame to be displayed.
 * @param framerate frame rate of stream.
 * @param flip_method flip frame if necessary, 90 deg intervals.
 *                    (0 = 0 deg, 1 = 90 deg, 2 = 180 deg, 3 = 270 deg).
 * @return std::string a string to be passed as gStreamer command line arguments.
 */
static std::string gstreamer_pipeline(int capture_width, int capture_height,
                                      int display_width, int display_height,
                                      int framerate, int flip_method) {

    return "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=(int)" +
           std::to_string(capture_width) + ", height=(int)" +
           std::to_string(capture_height) + ", framerate=(fraction)" +
           std::to_string(framerate) +
           "/1 ! nvvidconv flip-method=" + std::to_string(flip_method) +
           " ! video/x-raw, width=(int)" + std::to_string(display_width) +
           ", height=(int)" + std::to_string(display_height) +
           ", format=(string)BGRx ! videoconvert ! video/x-raw, format=(string)BGR ! "
           "appsink";
}

/**
 * @brief initialize and test camera stream.
 *
 * @param cam_stream VideoCapture object to tie it to the camera device.
 * @return true initialized and tested successfully.
 * @return false failed to initialize camera stream.
 */
static bool init_camera_stream(cv::VideoCapture &cam_stream) {

    cv::Mat temp_frame;
    bool    ok = false;

#if USE_GSTREAMER
    // initialize video stream from a CSI camera device
    std::string pipeline =
        gstreamer_pipeline(CAPTURE_WIDTH, CAPTURE_HEIGHT, DISPLAY_WIDTH, DISPLAY_HEIGHT,
                           FRAMERATE, FLIP_MODE);

    cam_stream.open(pipeline, cv::CAP_GSTREAMER);
#else
    // initialize video stream from a USB camera device
    cam_stream.open(0);
#endif /* USE_GSTREAMER */

    // ensure stream is open, and grab one frame to make sure it's not empty
    if (cam_stream.isOpened()) {
        cam_stream >> temp_frame;
        if (!temp_frame.empty()) { ok = true; }
    } else {
        ok = false;
    }

    // handle error if any
    // if (!ok) { handle_error(error_failed_cam_init); }

    return ok;
}

/**
 * @brief entry point.
 *
 * @return int
 */
int main(void) {
    cv::Mat     src_frame;        // source frames
    std::string out_filepath;     // should be constant per instance
    std::string out_filepath_tmp; // changes per frame
    std::string t1;
    std::string t2;
    std::string t3;

    // init camera
    std::cout << "initializing...";
    cv::VideoCapture cam_stream;
    if (!init_camera_stream(cam_stream)) {
        std::cerr << "[FAILED]" << std::endl;
        exit(-1);
    }

    // test camera
    std::cout << "[OK]" << std::endl;

    // create folder for this instance
    out_filepath = "./";
    out_filepath += "frames/";
    out_filepath += get_time_s();
    out_filepath += "/";
    mkdir(out_filepath.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IWOTH | S_IXOTH);

    // toggle GPIO 10 twice for time correlation
    std::cout << "toggling GPIO 10 twice.. then capturing " << NUM_OF_FRAMES << " frames";
    toggle_twice();
    t1 = get_time_ns(".");

    // start capturing frames and save to
    for (int i = 0; i < NUM_OF_FRAMES; ++i) {
        // save source frame
        cam_stream >> src_frame;

        if (!SAVE_RGB) { cv::cvtColor(src_frame, src_frame, cv::COLOR_BGR2GRAY); }

        if (i == 0) { t2 = get_time_ns("."); }
        // cv::extractChannel(tmp_frame, src_frames[i], CHAN_TO_EXTRACT);

        // save path+timestamp
        out_filepath_tmp = out_filepath;
        out_filepath_tmp += get_time_ns();
        out_filepath_tmp += ".png";
        cv::imwrite(out_filepath_tmp, src_frame);
    }

    t3 = get_time_ns(".");

    // post data collection statistics
    std::cout << "Saved " << NUM_OF_FRAMES << " frames" << std::endl;
    std::cout << "last image path = " << out_filepath << std::endl;
    std::cout << "t1 = " << t1 << std::endl;
    std::cout << "t2 = " << t2 << std::endl;
    long double t_1 = std::stold(t1);
    long double t_2 = std::stold(t2);
    long double t_3 = std::stold(t3);
    std::cout << "t_diff = " << t_2 - t_1 << std::endl;
    std::cout << "t_total = " << t_3 - t_1 << std::endl;

    // write out the latency recorded between toggling the GPIO line and capturing the
    // first frame
    std::ofstream f(out_filepath + "stats.txt");

    f << "t1 = " << t1 << std::endl;
    f << "t2 = " << t2 << std::endl;
    f << "t_diff = " << t_2 - t_1 << " s" << std::endl;
    f << "t_total = " << t_3 - t_1 << " s" << std::endl;

    // cleanup
    f.close();
    cam_stream.release();

    // terminate
    return 0;
}