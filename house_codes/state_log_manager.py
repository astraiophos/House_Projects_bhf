#!/usr/bin/python3
"""
Author:         Jacob B Fullerton
Date:           November 24, 2020
Usage:          This code is meant to provide functionality for managing the state log.
"""

import datetime

class StateLogManager:
    def __init__(self, log_data):
        """
        Expects a dictionary representing the state log information to be recorded
        :param log_data: A dictionary with at least one keyword with information to be recorded in the log
        """
        self.log_data = log_data
        self.get_time_data()
        self.accepted_keys = get_accepted_keys()
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
        else:
            return

    def write_state(self):
        """
        Write down the information provided to the state log (accepting only the keys
        :return:
        """


def get_accepted_keys():
    """
    This function determines the keys that are accepted, which are used in turn for writing the variables of
    interest to the state log.
    :return:
    """
    key_list = ['door_state', 'time']
    return key_list