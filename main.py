import os
import shutil
import subprocess


# Get's all dirs present in the data dir and returns them as strings
import time
from math import sqrt


def get_all_dirs_present_in_data_dir(data_dir):
    return [dI for dI in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, dI))]


# Get's the full path to the files (with .gpx) present in a specific dir
def get_gpx_files_present_in_dir(data_dir, sub_data_dir):
    files = []
    for file in os.listdir(os.path.join(data_dir, sub_data_dir)):
        if file.endswith(".gpx"):
            files.append(file)
    return files


# Converts a GPX file to a CSV file containing UTM coordinates
def convert_gpx_file_to_csv(path_to_gpsbabel, path_to_gpx_file, gpx_file, prepended_data_collector_id):
    # gpsbabel -t -i gpx -f "Day_4_2019-2020.gpx" -x nuketypes,waypoints,routes -o unicsv,grid="utm" -F "Day_4_2019-2020.csv"
    output_file = prepended_data_collector_id + gpx_file
    output_file = output_file.replace(".gpx", ".csv")

    param_input_file = os.path.join(os.path.abspath(path_to_gpx_file), gpx_file)
    param_output_file = os.path.join(os.path.abspath(path_to_gpx_file), output_file)

    try:
        subprocess.check_output(
            [path_to_gpsbabel, "-t", "-i", "gpx", "-f", param_input_file, "-x", "nuketypes,waypoints,routes", '-o',
             "unicsv,grid=utm", "-F", param_output_file])
    except subprocess.CalledProcessError:
        print("Attempt to convert GPX file to CSV file for : " + os.path.join(path_to_gpx_file, gpx_file) + " failed.")

    return output_file


# Post processes the CSV
# Splits up files if previous update points was more than 15 seconds ago and more than 100 meters
def post_process_csv(path_to_csv_file, csv_file):
    max_number_of_seconds_diff = 15
    max_number_of_meters_diff = 200

    txt_file = csv_file.replace('.csv', '')

    file_counter = 1
    output_filename = os.path.join(path_to_csv_file, txt_file + "_" + str(file_counter) + '.txt')
    output_file = open(output_filename, "w")
    output_files = [output_filename]
    start_number = -1

    previous_data_row = []
    for line in open(os.path.join(path_to_csv_file, csv_file)):
        csv_row = line.split(',')
        if csv_row[0] == "No":
            continue

        # Do some filtering to remove some noise
        for i in range(len(csv_row)):
            csv_row[i] = csv_row[i].replace('\r', '').replace('\n', '')

        # Get the required info from the CSV file
        date_time = str(csv_row[6]) + " " + str(csv_row[7])
        pattern = '%Y/%m/%d %H:%M:%S'
        epoch = int(time.mktime(time.strptime(date_time, pattern)))
        if start_number < 0:
            start_number = epoch

        gps_timestamp = epoch - start_number
        data_row = [csv_row[3], csv_row[4], gps_timestamp]

        # Check for whether we need to split up the file
        if len(previous_data_row) == 3:
            seconds_diff = data_row[2] - previous_data_row[2]
            meters_diff = calculate_meters_diff(data_row, previous_data_row)

            if seconds_diff > max_number_of_seconds_diff and meters_diff > max_number_of_meters_diff:
                print("Seconds diff: " + str(seconds_diff) + " and meters diff: " + str(meters_diff))
                output_file.close()
                file_counter += 1
                output_filename = os.path.join(path_to_csv_file, txt_file + "_" + str(file_counter) + '.txt')
                output_file = open(output_filename, "w")
                output_files.append(output_filename)

        # Only add if different position
        if calculate_meters_diff(data_row, previous_data_row) >= 0.01:
            output_file.write(str(data_row[0]) + " " + str(data_row[1]) + " " + str(data_row[2]))
            output_file.write("\n")

        previous_data_row = data_row

    return output_files


# Calculates the meters difference between the two frames
def calculate_meters_diff(data_row, previous_data_row):
    x1 = int(previous_data_row[0])
    x2 = int(data_row[0])
    y1 = int(previous_data_row[1])
    y2 = int(data_row[1])
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# Prints some info regarding the UTM zone
def print_info_about_utm_zone(path_to_csv_files, csv_file):
    first = True
    for line in open(os.path.join(path_to_csv_files, csv_file)):
        if first:
            first = False
            continue
        csv_row = line.split(',')
        print ("UTM-Zone: " + csv_row[1])
        print ("UTM-Ch: " + csv_row[2])
        break


# Copy CSV to output dir
def copy_txt_to_output_dir(output_dir, path_to_txt_files, full_path_to_txt_file):
    shutil.copy2(full_path_to_txt_file, full_path_to_txt_file.replace(path_to_txt_files, output_dir))
    return True


# Main run of the program
def main(path_to_gpsbabel, data_dir, output_dir):
    if not os.path.isdir(data_dir):
        print("Error! data_dir is defined incorrectly.")
        exit()

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    counter = 1
    first = True
    for current_data_dir in get_all_dirs_present_in_data_dir(data_dir):

        data_dir_id = str(counter).zfill(4) + "_"
        path_to_gpx_files = os.path.join(data_dir, current_data_dir)

        for gpx_file in get_gpx_files_present_in_dir(data_dir, current_data_dir):
            csv_file = convert_gpx_file_to_csv(path_to_gpsbabel, path_to_gpx_files, gpx_file, data_dir_id)
            paths_to_txt_files = post_process_csv(path_to_gpx_files, csv_file)
            for path_to_txt_file in paths_to_txt_files:
                copy_txt_to_output_dir(output_dir, path_to_gpx_files, path_to_txt_file)

            if first:
                print_info_about_utm_zone(path_to_gpx_files, csv_file)
                first = False

        print(current_data_dir + " represents data identified by " + data_dir_id)
        counter += 1


main('/Applications/GPSBabelFE.app/contents/MacOS/gpsbabel', 'data/', 'output/')
