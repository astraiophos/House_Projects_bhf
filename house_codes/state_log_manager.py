#!/usr/bin/python3
"""
Author:         Jacob B Fullerton
Date:           November 24, 2020
Usage:          This code is meant to provide functionality for managing the state log.
"""

import datetime
from pathlib import Path


class StateLogManager:
    def __init__(self, log_data, log_loc='../data/state_log.txt'):
        """
        Expects a dictionary representing the state log information to be recorded
        :param log_data: A dictionary with at least one keyword with information to be recorded in the log
        """
        self.log_data = log_data
        self.log_path = log_loc
        self.get_time_data()
        if hasattr(self.log_data, 'door_state'):
            self.state_log_text = self.set_door_state()
        if hasattr(self, 'state_log_text'):
            self.write_state()

    def get_time_data(self):
        """
        First verify that the incoming information doesn't have time data, if it doesn't then generate it and add it
        to the log data
        :return:
        """
        if 'time' not in self.log_data:
            self.log_data['time'] = datetime.datetime.now()
        return

    def set_door_state(self, str_fmt='%m/%d/%Y, %H:%M:%S'):
        """
        This will store the door state as text for writing to the state log file.
        :return:    String for writing to the state log
        """
        log_text = 'door_state: {}\n'.format(self.log_data['door_state'])
        log_text += 'time: {}'.format(datetime.datetime.strftime(self.log_data['time'], str_fmt))
        return log_text

    def write_state(self):
        """
        Write down the information provided to the state log (accepting only the keys
        :return:
        """
        file_path = Path(self.log_path)
        file_path.write_text(self.state_log_text)
