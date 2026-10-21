#!/usr/bin/env python3
"""Start the controller app (os-ken has no osken-manager launcher, so we start it here).
    python3 run_controller.py
"""
import os
from os_ken import cfg, log
from os_ken.base.app_manager import AppManager

here = os.path.dirname(os.path.abspath(__file__))
cfg.CONF(args=[], project='os_ken', version='1', default_config_files=[])
log.init_log()
AppManager.run_apps([os.path.join(here, 'controller_app.py'),
                     'os_ken.controller.ofp_handler'])
