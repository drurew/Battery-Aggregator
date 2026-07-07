#!/usr/bin/env python3
"""
SOC Calibration: syncs the Victron house shunt SOC from the Super-B BMS.

The house shunt measures combined current accurately but its SOC drifts
because internal cell balancing by the Super-B nodes reads as external
charging current at the shunt level. The BMS knows true SOC from
cell-level voltage tracking.

The BMV only accepts SOC writes at 100% (synchronisation). This script
monitors the BMS and triggers a sync when the battery reaches full charge.
Between syncs the shunt's coulomb counter runs freely, which is accurate
for tracking discharge Ah. The occasional drift is corrected at each full
charge event.
"""

import dbus
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('soc-sync')

BMS_SERVICE = 'com.victronenergy.battery.canopen_bms_node1'
SHUNT_SERVICE = 'com.victronenergy.battery.ttyS5'
SYNC_THRESHOLD = 99.0   # sync when BMS reports >= this SOC
SYNC_INTERVAL = 60       # seconds between checks

bus = dbus.SystemBus()

last_sync = 0

def get_bms_soc():
    try:
        obj = bus.get_object(BMS_SERVICE, '/Soc')
        return float(obj.GetValue())
    except Exception as e:
        log.error(f"BMS SOC read failed: {e}")
        return None

def sync_shunt():
    try:
        obj = bus.get_object(SHUNT_SERVICE, '/Soc')
        iface = dbus.Interface(obj, 'com.victronenergy.BusItem')
        iface.SetValue(100.0)
        return True
    except Exception as e:
        log.error(f"Shunt SOC sync failed: {e}")
        return False

log.info(f"SOC sync starting: {BMS_SERVICE} -> {SHUNT_SERVICE} (at 100% only)")

while True:
    soc = get_bms_soc()
    if soc is not None:
        if soc >= SYNC_THRESHOLD and time.time() - last_sync > 3600:
            if sync_shunt():
                last_sync = time.time()
                log.info(f"Synced shunt to 100%% at BMS SOC {soc:.1f}%%")
    time.sleep(SYNC_INTERVAL)
