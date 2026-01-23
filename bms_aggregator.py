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
import configparser

# Victron packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("BMSAggregator")

class BMSAggregator:
    def __init__(self, config_file='/data/bms_aggregator/config.ini'):
        # Load configuration
        self.config = configparser.ConfigParser()
        
        # Set defaults
        self.config['Battery'] = {
            'capacity': '450.0',
            'max_charge_voltage': '14.2',
            'max_discharge_current': '150.0',
            'battery_low_voltage': '11.5'
        }
        self.config['ChargeLimits'] = {
            'nominal_charge_current': '150.0',
            'reduced_charge_current': '50.0'
        }
        self.config['ImbalanceThresholds'] = {
            'imbalance_ok_threshold': '5.0',
            'imbalance_warning_threshold': '15.0',
            'imbalance_alarm_threshold': '20.0'
        }
        self.config['BMS'] = {
            'bms1_service': 'com.victronenergy.battery.canopen_bms_node1',
            'bms2_service': 'com.victronenergy.battery.canopen_bms_node2',
            'bms3_service': 'com.victronenergy.battery.canopen_bms_node3',
            'device_instance': '280'
        }
        self.config['Logging'] = {
            'update_interval': '2.0',
            'debug': 'false'
        }
        
        # Try to load config file
        if os.path.exists(config_file):
            try:
                self.config.read(config_file)
                log.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                log.warning(f"Error reading config file {config_file}: {e}, using defaults")
        else:
            log.info(f"Config file {config_file} not found, using defaults")
        
        # Apply configuration
        self.device_instance = self.config.getint('BMS', 'device_instance')
        self.servicename = f'com.victronenergy.battery.socketcan_can0_di{self.device_instance}_uc1537'
        self.bms_services = [
            self.config.get('BMS', 'bms1_service'),
            self.config.get('BMS', 'bms2_service'),
            self.config.get('BMS', 'bms3_service')
        ]
        
        # Charge current limits
        self.nominal_charge_current = self.config.getfloat('ChargeLimits', 'nominal_charge_current')
        self.reduced_charge_current = self.config.getfloat('ChargeLimits', 'reduced_charge_current')
        
        # Imbalance thresholds
        self.imbalance_ok_threshold = self.config.getfloat('ImbalanceThresholds', 'imbalance_ok_threshold')
        self.imbalance_warning_threshold = self.config.getfloat('ImbalanceThresholds', 'imbalance_warning_threshold')
        self.imbalance_alarm_threshold = self.config.getfloat('ImbalanceThresholds', 'imbalance_alarm_threshold')
        
        # Battery parameters
        self.capacity = self.config.getfloat('Battery', 'capacity')
        self.max_charge_voltage = self.config.getfloat('Battery', 'max_charge_voltage')
        self.max_discharge_current = self.config.getfloat('Battery', 'max_discharge_current')
        self.battery_low_voltage = self.config.getfloat('Battery', 'battery_low_voltage')
        
        # Logging
        update_interval_sec = self.config.getfloat('Logging', 'update_interval')
        self.update_interval_ms = int(update_interval_sec * 1000)
        debug_mode = self.config.getboolean('Logging', 'debug')
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)
            log.setLevel(logging.DEBUG)
        
        log.info("Starting BMS Aggregator Service v1.1.0")
        log.info(f"Imbalance thresholds: OK<{self.imbalance_ok_threshold}%, Warning<{self.imbalance_warning_threshold}%, Alarm>={self.imbalance_alarm_threshold}%")
        log.info(f"Charge currents: Nominal={self.nominal_charge_current}A, Reduced={self.reduced_charge_current}A")
        
        # Create D-Bus service
        DBusGMainLoop(set_as_default=True)
        self.dbusservice = VeDbusService(self.servicename)
        self.bus = dbus.SystemBus()
        
        # Add mandatory paths for battery service
        self.dbusservice.add_path('/DeviceInstance', self.device_instance)
        self.dbusservice.add_path('/ProductId', 0)
        self.dbusservice.add_path('/ProductName', 'BMS Aggregator')
        self.dbusservice.add_path('/FirmwareVersion', '1.2.0')
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
        self.dbusservice.add_path('/Capacity', self.capacity, writeable=False)
        
        # BMS-specific paths
        self.dbusservice.add_path('/System/MinCellVoltage', None, writeable=False)
        self.dbusservice.add_path('/System/MaxCellVoltage', None, writeable=False)
        self.dbusservice.add_path('/System/MinVoltageCellId', None, writeable=False)
        self.dbusservice.add_path('/System/MaxVoltageCellId', None, writeable=False)
        self.dbusservice.add_path('/System/MinCellTemperature', None, writeable=False)
        self.dbusservice.add_path('/System/MaxCellTemperature', None, writeable=False)
        
        # Charge/discharge limits
        self.dbusservice.add_path('/Info/MaxChargeVoltage', self.max_charge_voltage, writeable=False)
        self.dbusservice.add_path('/Info/MaxChargeCurrent', self.nominal_charge_current, writeable=False)
        self.dbusservice.add_path('/Info/MaxDischargeCurrent', self.max_discharge_current, writeable=False)
        self.dbusservice.add_path('/Info/BatteryLowVoltage', self.battery_low_voltage, writeable=False)
        
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
        
        # Update at configured interval
        GLib.timeout_add(self.update_interval_ms, self.update)
        
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
            bms_has_cell_alarm = any([
                bms['cell_imbalance_alarm'] or bms['high_cell_alarm'] or bms['low_cell_alarm']
                for bms in bms_data
            ])
            
            # Calculate aggregated values
            if not socs or not voltages:
                log.warning("No data available from BMS units")
                return True
            
            # AGGREGATION LOGIC:
            # 1. Use LOWEST SOC for safety (prevents overcharging weaker battery)
            # 2. Average voltages (parallel configuration)
            # 3. Sum currents (parallel configuration)
            aggregated_soc = min(socs)
            aggregated_voltage = sum(voltages) / len(voltages)
            aggregated_current = sum(currents)
            aggregated_temp = sum(temps) / len(temps) if temps else None
            
            # Calculate imbalance (SOC range across batteries)
            soc_min = min(socs)
            soc_max = max(socs)
            imbalance_percent = soc_max - soc_min
            
            # Determine alarm status and charge current based on imbalance
            if imbalance_percent >= self.imbalance_alarm_threshold:
                # Severe imbalance: Alarm (2) + severely reduced charge current
                alarm_level = 2
                charge_current = self.reduced_charge_current
                log.warning(f"Battery imbalance ALARM: {imbalance_percent:.0f}% difference - reducing charge to {charge_current:.0f}A")
            elif imbalance_percent >= self.imbalance_warning_threshold:
                # Moderate imbalance: Warning (1) + moderately reduced charge current
                alarm_level = 1
                charge_current = self.nominal_charge_current * 0.66  # 66% of nominal
                log.info(f"Battery imbalance warning: {imbalance_percent:.0f}% difference - reducing charge to {charge_current:.0f}A")
            elif imbalance_percent >= self.imbalance_ok_threshold:
                # Minor imbalance: OK (0) but reduce charge slightly
                alarm_level = 0
                charge_current = self.nominal_charge_current * 0.85  # 85% of nominal
                log.debug(f"Minor battery imbalance: {imbalance_percent:.0f}% difference - reducing charge to {charge_current:.0f}A")
            else:
                # Well balanced: OK (0) + full charge current
                alarm_level = 0
                charge_current = self.nominal_charge_current
                log.debug(f"Batteries balanced: {imbalance_percent:.0f}% difference - full charge current {charge_current:.0f}A")
            
            # If any BMS reports internal cell issues, escalate to alarm
            if bms_has_cell_alarm:
                alarm_level = max(alarm_level, 2)  # Escalate to Alarm
                charge_current = min(charge_current, self.reduced_charge_current)  # Reduce charge
                log.warning("BMS cell alarm detected - escalating to ALARM status")
            
            # Update D-Bus paths
            self.dbusservice['/Dc/0/Voltage'] = aggregated_voltage
            self.dbusservice['/Dc/0/Current'] = aggregated_current
            self.dbusservice['/Dc/0/Power'] = aggregated_voltage * aggregated_current
            if aggregated_temp is not None:
                self.dbusservice['/Dc/0/Temperature'] = aggregated_temp
            self.dbusservice['/Soc'] = aggregated_soc
            
            # Update charge current dynamically
            self.dbusservice['/Info/MaxChargeCurrent'] = charge_current
            
            # Update alarm
            self.dbusservice['/Alarms/CellImbalance'] = alarm_level
            
            # Log summary (formatted SOC percentages)
            soc_strings = [f"{s:.0f}%" for s in socs]
            log.info(f"SOCs: {soc_strings} -> Using lowest: {aggregated_soc:.0f}% (range: {imbalance_percent:.0f}%)")
            
        except Exception as e:
            log.error(f"Error in update loop: {e}")
            log.error(traceback.format_exc())
        
        return True  # Continue timer

if __name__ == "__main__":
    try:
        aggregator = BMSAggregator()
        mainloop = GLib.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        log.info("Shutting down BMS Aggregator")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        log.error(traceback.format_exc())
