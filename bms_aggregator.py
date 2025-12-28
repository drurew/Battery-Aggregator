#!/usr/bin/env python3
"""
BMS Aggregator Service for Victron Venus OS
Aggregates SOC and voltage from multiple BMS units (battery/1, battery/2, battery/3)
Presents aggregated data as a virtual battery service for VE.Bus control
"""

import sys
import os
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import logging
import traceback

# Victron packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("BMSAggregator")

class BMSAggregator:
    def __init__(self):
        # Use device instance 280 (next available after HOUSE=277, FRONT=278)
        self.device_instance = 280
        self.servicename = 'com.victronenergy.battery.socketcan_can0_di280_uc1537'  # Mimic real battery naming
        self.bms_services = [
            'com.victronenergy.battery.canopen_bms_node1',
            'com.victronenergy.battery.canopen_bms_node2', 
            'com.victronenergy.battery.canopen_bms_node3'
        ]
        
        log.info("Starting BMS Aggregator Service")
        
        # Create D-Bus service
        DBusGMainLoop(set_as_default=True)
        self.dbusservice = VeDbusService(self.servicename)
        self.bus = dbus.SystemBus()
        
        # Add mandatory paths for battery service
        self.dbusservice.add_path('/DeviceInstance', self.device_instance)
        self.dbusservice.add_path('/ProductId', 0)
        self.dbusservice.add_path('/ProductName', 'BMS Aggregator')
        self.dbusservice.add_path('/FirmwareVersion', '1.0.0')
        self.dbusservice.add_path('/HardwareVersion', '1.0.0')
        self.dbusservice.add_path('/Connected', 1)
        self.dbusservice.add_path('/CustomName', 'BMS Aggregator', writeable=True)
        
        # Battery data paths
        self.dbusservice.add_path('/Dc/0/Voltage', None, writeable=False, gettextcallback=lambda p, v: "{:.2f}V".format(v))
        self.dbusservice.add_path('/Dc/0/Current', None, writeable=False, gettextcallback=lambda p, v: "{:.1f}A".format(v))
        self.dbusservice.add_path('/Dc/0/Power', None, writeable=False, gettextcallback=lambda p, v: "{:.0f}W".format(v))
        self.dbusservice.add_path('/Dc/0/Temperature', None, writeable=False, gettextcallback=lambda p, v: "{:.1f}C".format(v))
        self.dbusservice.add_path('/Soc', None, writeable=False, gettextcallback=lambda p, v: "{:.0f}%".format(v))
        self.dbusservice.add_path('/TimeToGo', None, writeable=False)
        self.dbusservice.add_path('/ConsumedAmphours', None, writeable=False)
        self.dbusservice.add_path('/Capacity', 450.0, writeable=False)  # 3x 150Ah = 450Ah
        
        # BMS-specific paths
        self.dbusservice.add_path('/System/MinCellVoltage', None, writeable=False)
        self.dbusservice.add_path('/System/MaxCellVoltage', None, writeable=False)
        self.dbusservice.add_path('/System/MinVoltageCellId', None, writeable=False)
        self.dbusservice.add_path('/System/MaxVoltageCellId', None, writeable=False)
        self.dbusservice.add_path('/System/MinCellTemperature', None, writeable=False)
        self.dbusservice.add_path('/System/MaxCellTemperature', None, writeable=False)
        
        # Charge/discharge limits
        self.dbusservice.add_path('/Info/MaxChargeVoltage', 14.2, writeable=False)
        self.dbusservice.add_path('/Info/MaxChargeCurrent', 150.0, writeable=False)  # 3x 50A
        self.dbusservice.add_path('/Info/MaxDischargeCurrent', 150.0, writeable=False)
        self.dbusservice.add_path('/Info/BatteryLowVoltage', 11.5, writeable=False)
        
        # Dynamic charge current reduction on imbalance
        self.nominal_charge_current = 150.0  # Normal: 3x 50A
        self.reduced_charge_current = 50.0   # Imbalanced: 1x 50A (slow balance charge)
        
        # Alarms
        self.dbusservice.add_path('/Alarms/LowVoltage', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/HighVoltage', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/LowSoc', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/HighChargeCurrent', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/HighDischargeCurrent', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/CellImbalance', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/InternalFailure', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/HighChargeTemperature', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/LowChargeTemperature', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/HighTemperature', 0, writeable=False)
        self.dbusservice.add_path('/Alarms/LowTemperature', 0, writeable=False)
        
        log.info("BMS Aggregator service registered on D-Bus")
        
        # Update every 2 seconds
        GLib.timeout_add(2000, self.update)
        
    def get_bms_value(self, service, path, default=None):
        """Read a value from a BMS service"""
        try:
            obj = self.bus.get_object(service, path)
            return obj.GetValue()
        except Exception as e:
            log.debug(f"Could not read {path} from {service}: {e}")
            return default
    
    def update(self):
        """Aggregate data from all BMS units"""
        try:
            voltages = []
            socs = []
            currents = []
            temps = []
            all_cell_voltages = []
            bms_data = []
            
            # Read from each BMS with detailed info
            for idx, service in enumerate(self.bms_services):
                voltage = self.get_bms_value(service, '/Dc/0/Voltage')
                soc = self.get_bms_value(service, '/Soc')
                current = self.get_bms_value(service, '/Dc/0/Current', 0.0)
                temp = self.get_bms_value(service, '/Dc/0/Temperature')
                
                # BMS internal cell alarms (not raw voltages)
                cell_imbalance_alarm = self.get_bms_value(service, '/Alarms/CellImbalance', 0)
                high_cell_alarm = self.get_bms_value(service, '/Alarms/HighCellVoltage', 0)
                low_cell_alarm = self.get_bms_value(service, '/Alarms/LowCellVoltage', 0)
                
                bms_info = {
                    'id': idx + 1,
                    'service': service,
                    'voltage': voltage,
                    'soc': soc,
                    'current': current,
                    'temp': temp,
                    'cell_imbalance_alarm': cell_imbalance_alarm,
                    'high_cell_alarm': high_cell_alarm,
                    'low_cell_alarm': low_cell_alarm
                }
                bms_data.append(bms_info)
                
                if voltage is not None:
                    voltages.append(voltage)
                if soc is not None:
                    socs.append(soc)
                if current is not None:
                    currents.append(current)
                if temp is not None:
                    temps.append(temp)
            
            # Detect BMS internal cell alarms (cells within a single battery)
            bms_cell_alarm = False
            for bms in bms_data:
                if bms['cell_imbalance_alarm'] or bms['high_cell_alarm'] or bms['low_cell_alarm']:
                    bms_cell_alarm = True
                    log.warning(f"BMS{bms['id']} cell alarm detected! Imbalance:{bms['cell_imbalance_alarm']}, High:{bms['high_cell_alarm']}, Low:{bms['low_cell_alarm']}")
            
            # Note: SuperB BMS does not expose individual cell voltages, only alarms
            spike_detected = bms_cell_alarm
            
            # Aggregate values
            if voltages:
                # Average voltage across all batteries
                avg_voltage = sum(voltages) / len(voltages)
                self.dbusservice['/Dc/0/Voltage'] = round(avg_voltage, 3)
                log.debug(f"Voltages: {[f'{v:.2f}' for v in voltages]} -> Avg: {avg_voltage:.2f}V")
            
            if socs:
                # Use LOWEST SOC for safety (most conservative)
                min_soc = min(socs)
                max_soc = max(socs)
                self.dbusservice['/Soc'] = round(min_soc, 1)
                log.info(f"SOCs: {[f'{s:.0f}%' for s in socs]} -> Using lowest: {min_soc:.0f}% (range: {max_soc-min_soc:.0f}%)")
            
            if currents:
                # Sum currents (parallel batteries)
                total_current = sum(currents)
                self.dbusservice['/Dc/0/Current'] = round(total_current, 2)
            
            if temps:
                # Average temperature
                avg_temp = sum(temps) / len(temps)
                self.dbusservice['/Dc/0/Temperature'] = round(avg_temp, 1)
            
            # Power calculation
            voltage = self.dbusservice['/Dc/0/Voltage']
            current = self.dbusservice['/Dc/0/Current']
            if voltage is not None and current is not None:
                self.dbusservice['/Dc/0/Power'] = round(voltage * current, 1)
            
            # Aggregate cell info note: SuperB BMS doesn't expose raw cell voltages
            # Only monitors internal alarms which are checked above
            
            # Imbalance detection with BMS cell alarm override
            if socs and len(socs) > 1:
                soc_diff = max(socs) - min(socs)
                
                # If BMS internal cell alarm detected, escalate to alarm
                if spike_detected:
                    self.dbusservice['/Alarms/CellImbalance'] = 2  # Alarm
                    self.dbusservice['/Info/MaxChargeCurrent'] = self.reduced_charge_current
                    log.warning(f"BMS CELL ALARM: Internal cell issue detected - forcing alarm and reducing charge to {self.reduced_charge_current}A!")
                elif soc_diff > 15:
                    # Critical battery imbalance
                    self.dbusservice['/Alarms/CellImbalance'] = 2  # Alarm
                    self.dbusservice['/Info/MaxChargeCurrent'] = self.reduced_charge_current
                    log.warning(f"Critical battery imbalance: {soc_diff:.0f}% difference - reducing charge to {self.reduced_charge_current}A")
                elif soc_diff > 10:
                    # Moderate battery imbalance - warning
                    self.dbusservice['/Alarms/CellImbalance'] = 1  # Warning
                    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.66  # 2/3 current
                    log.info(f"Battery imbalance warning: {soc_diff:.0f}% difference - reducing charge to {self.nominal_charge_current * 0.66:.0f}A")
                elif soc_diff > 5:
                    # Minor battery imbalance - info only
                    self.dbusservice['/Alarms/CellImbalance'] = 0  # OK
                    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.85  # 85% current
                    log.debug(f"Minor battery variance: {soc_diff:.0f}% - slightly reducing charge to {self.nominal_charge_current * 0.85:.0f}A")
                else:
                    self.dbusservice['/Alarms/CellImbalance'] = 0  # OK
                    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current
                    
        except Exception as e:
            log.error(f"Error updating aggregated values: {e}")
            log.error(traceback.format_exc())
        
        return True  # Keep timer running

def main():
    try:
        log.info("="*50)
        log.info("BMS Aggregator Service Starting")
        log.info("="*50)
        
        aggregator = BMSAggregator()
        
        log.info("Entering main loop")
        mainloop = GLib.MainLoop()
        mainloop.run()
        
    except KeyboardInterrupt:
        log.info("Shutting down on CTRL+C")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        log.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
