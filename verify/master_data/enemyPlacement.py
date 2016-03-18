#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import codecs
from collections import OrderedDict
from logging import info, debug, warning, error
from base import Base

class enemyPlacement(Base):
    def __init__(self):
        self.table = 'enemyPlacement'

    def verify(self, data, schema = {}, references = {}, file_references = {}, validations = {}):
        group_incidence_map = OrderedDict()
        for d in data:
            group_id = d['groupId']
            if not group_incidence_map.has_key(group_id):
                group_incidence_map[group_id] = 0
            group_incidence_map[group_id] += d['incidence']

        result = True
        for group_id, incidence_total in group_incidence_map.iteritems():
            if not incidence_total in (0, 10000):
                self.error(u".incidence: グループ '%d' の確率の和が 100%% (10000) ではありません: %d" % (group_id, incidence_total))
                result = False

        return result
