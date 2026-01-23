# Configuration Guide

Detailed configuration options for the Battery Aggregator service.

## Table of Contents
- [Basic Configuration](#basic-configuration)
- [BMS Service Configuration](#bms-service-configuration)
- [Charge Current Limits](#charge-current-limits)
- [Imbalance Thresholds](#imbalance-thresholds)
- [Device Instance](#device-instance)
- [Battery Specifications](#battery-specifications)
- [Advanced Options](#advanced-options)

## Basic Configuration

### File Location
Configuration is stored in `/data/bms_aggregator/bms_aggregator.py` on the Cerbo GX.

After making changes, restart the service:
```bash
svc -t /service/bms-aggregator
```

## BMS Service Configuration

### Finding Your BMS Services

List available battery services:
```bash
dbus -y com.victronenergy.system /AvailableBatteryServices GetValue
```

### Configure Service Names

**Location**: Lines 31-35

```python
self.bms_services = [
    'com.victronenergy.battery.canopen_bms_node1',
    'com.victronenergy.battery.canopen_bms_node2',
    'com.victronenergy.battery.canopen_bms_node3'
]
```

**Examples for different BMS types:**

**SuperB Epsilon via CANopen:**
```python
self.bms_services = [
    'com.victronenergy.battery.canopen_bms_node1',
    'com.victronenergy.battery.canopen_bms_node2',
    'com.victronenergy.battery.canopen_bms_node3'
]
```

**Pylontech batteries:**
```python
self.bms_services = [
    'com.victronenergy.battery.socketcan_can0_di512_uc1234',
    'com.victronenergy.battery.socketcan_can0_di513_uc1235',
    'com.victronenergy.battery.socketcan_can0_di514_uc1236'
]
```

**REC BMS:**
```python
self.bms_services = [
    'com.victronenergy.battery.ttyUSB0',
    'com.victronenergy.battery.ttyUSB1'
]
```

## Charge Current Limits

### Nominal Charge Current

**Location**: Line 68

Maximum charge current when batteries are balanced.

```python
self.nominal_charge_current = 150.0  # Amps
```

**How to calculate:**
- Single battery max charge: 50A
- Number of batteries: 3
- Total: 3 × 50A = 150A

**Common configurations:**
- 2× 50A batteries: `100.0`
- 3× 50A batteries: `150.0`
- 4× 100A batteries: `400.0`

### Reduced Charge Current

**Location**: Line 69

Minimum charge current during severe imbalance.

```python
self.reduced_charge_current = 50.0  # Amps
```

**Recommendations:**
- Conservative: 1× single battery rating (50A)
- Moderate: 1.5× single battery rating (75A)
- Aggressive: 2× single battery rating (100A)

## Imbalance Thresholds

### SOC Difference Thresholds

**Location**: Lines 179-200 in `update()` method

```python
if soc_diff > 15:
    # Critical: 33% charge current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.reduced_charge_current
elif soc_diff > 10:
    # Moderate: 66% charge current  
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.66
elif soc_diff > 5:
    # Minor: 85% charge current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.85
```

### Customizing Thresholds

**Conservative** (slower charging, more protection):
```python
if soc_diff > 10:      # was 15
    # Alarm, 33% current
elif soc_diff > 5:     # was 10
    # Warning, 50% current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.50
elif soc_diff > 3:     # was 5
    # OK, 75% current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.75
```

**Aggressive** (faster charging, less protection):
```python
if soc_diff > 20:      # was 15
    # Alarm, 50% current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.50
elif soc_diff > 15:    # was 10
    # Warning, 75% current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.75
elif soc_diff > 10:    # was 5
    # OK, 90% current
    self.dbusservice['/Info/MaxChargeCurrent'] = self.nominal_charge_current * 0.90
```

## Device Instance

### Setting Device Instance

**Location**: Line 28

```python
self.device_instance = 280
```

The device instance must be unique. Check used instances:
```bash
dbus | grep /DeviceInstance
```

**Common available instances**: 280-299, 100-199

### Service Name Pattern

**Location**: Line 29

```python
self.servicename = 'com.victronenergy.battery.socketcan_can0_di280_uc1537'
```

The service name should match the pattern `com.victronenergy.battery.*_di<instance>_*`

## Battery Specifications

### Total Capacity

**Location**: Line 51

```python
self.dbusservice.add_path('/Capacity', 450.0, writeable=False)  # Ah
```

**Calculation**: Single battery Ah × Number of batteries
- Example: 150Ah × 3 = 450Ah

### Maximum Charge Voltage

**Location**: Line 67

```python
self.dbusservice.add_path('/Info/MaxChargeVoltage', 14.2, writeable=False)  # Volts
```

**Common values:**
- **LiFePO4 12V**: 14.2V - 14.6V
- **LiFePO4 24V**: 28.4V - 29.2V
- **LiFePO4 48V**: 56.8V - 58.4V
- **Lead Acid 12V**: 14.4V - 14.7V

### Maximum Discharge Current

**Location**: Line 70

```python
self.dbusservice.add_path('/Info/MaxDischargeCurrent', 150.0, writeable=False)  # Amps
```

Should match or exceed nominal charge current.

### Battery Low Voltage

**Location**: Line 71

```python
self.dbusservice.add_path('/Info/BatteryLowVoltage', 11.5, writeable=False)  # Volts
```

**Common values:**
- **LiFePO4 12V**: 11.0V - 11.5V
- **LiFePO4 24V**: 22.0V - 23.0V
- **LiFePO4 48V**: 44.0V - 46.0V

## Advanced Options

### Update Interval

**Location**: Line 103

```python
GLib.timeout_add(2000, self.update)  # milliseconds
```

**Recommendations:**
- Fast: `1000` (1 second) - more CPU usage
- Normal: `2000` (2 seconds) - balanced
- Slow: `5000` (5 seconds) - less CPU usage

### Logging Level

**Location**: Line 21

```python
logging.basicConfig(level=logging.INFO)
```

**Options:**
- `logging.DEBUG` - Verbose, all details
- `logging.INFO` - Normal, important events
- `logging.WARNING` - Quiet, warnings and errors only
- `logging.ERROR` - Silent, errors only

### Custom Name

**Location**: Line 40

```python
self.dbusservice.add_path('/ProductName', 'BMS Aggregator')
self.dbusservice.add_path('/CustomName', 'BMS Aggregator', writeable=True)
```

Change to identify your system:
```python
self.dbusservice.add_path('/ProductName', 'Battery Bank 1')
self.dbusservice.add_path('/CustomName', 'House Batteries', writeable=True)
```

## Testing Configuration Changes

### 1. Make Backup
```bash
cp /data/bms_aggregator/bms_aggregator.py /data/bms_aggregator/bms_aggregator.py.backup
```

### 2. Edit Configuration
```bash
vi /data/bms_aggregator/bms_aggregator.py
```

### 3. Restart Service
```bash
svc -t /service/bms-aggregator
sleep 3
```

### 4. Check for Errors
```bash
tail -20 /var/log/bms-aggregator/current
```

Look for:
- `BMS Aggregator Service Starting`
- `registered ourselves on D-Bus`
- No ERROR messages

### 5. Verify Values
```bash
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Soc GetValue
dbus -y com.victronenergy.battery.socketcan_can0_di280_uc1537 /Info/MaxChargeCurrent GetValue
```

### 6. Restore if Broken
```bash
cp /data/bms_aggregator/bms_aggregator.py.backup /data/bms_aggregator/bms_aggregator.py
svc -t /service/bms-aggregator
```

## Example Configurations

### Configuration 1: Conservative 12V LiFePO4 (2 batteries)
```python
# Lines 28-29
self.device_instance = 280
self.servicename = 'com.victronenergy.battery.socketcan_can0_di280_uc1537'

# Lines 31-34
self.bms_services = [
    'com.victronenergy.battery.canopen_bms_node1',
    'com.victronenergy.battery.canopen_bms_node2'
]

# Line 51
self.dbusservice.add_path('/Capacity', 300.0, writeable=False)  # 2× 150Ah

# Line 67
self.dbusservice.add_path('/Info/MaxChargeVoltage', 14.2, writeable=False)

# Lines 68-69
self.nominal_charge_current = 100.0  # 2× 50A
self.reduced_charge_current = 50.0
```

### Configuration 2: Aggressive 24V LiFePO4 (4 batteries)
```python
self.device_instance = 285
self.servicename = 'com.victronenergy.battery.socketcan_can0_di285_uc1537'

self.bms_services = [
    'com.victronenergy.battery.socketcan_can0_di512_uc1234',
    'com.victronenergy.battery.socketcan_can0_di513_uc1235',
    'com.victronenergy.battery.socketcan_can0_di514_uc1236',
    'com.victronenergy.battery.socketcan_can0_di515_uc1237'
]

self.dbusservice.add_path('/Capacity', 800.0, writeable=False)  # 4× 200Ah
self.dbusservice.add_path('/Info/MaxChargeVoltage', 28.8, writeable=False)  # 24V

self.nominal_charge_current = 400.0  # 4× 100A
self.reduced_charge_current = 100.0  # More aggressive
```

## Troubleshooting Configuration

### Changes Not Taking Effect
```bash
# Verify service restarted
svstat /service/bms-aggregator

# Check for Python syntax errors
python3 /data/bms_aggregator/bms_aggregator.py
```

### BMS Services Not Found
```bash
# List all battery services
dbus | grep battery

# Test individual service
dbus -y com.victronenergy.battery.canopen_bms_node1 /Soc GetValue
```

### Wrong Values Reported
```bash
# Check what aggregator is reading
tail -f /var/log/bms-aggregator/current | grep SOC

# Compare to source
dbus -y com.victronenergy.battery.canopen_bms_node1 /Soc GetValue
```

## See Also

- [INSTALL.md](INSTALL.md) - Installation instructions
- [README.md](README.md) - Features and usage
- [Victron D-Bus API](https://github.com/victronenergy/venus/wiki/dbus-api) - Official documentation

## Version History

### v1.1.0 Changes
- Added configuration file support (`config.ini`)
- Increased default warning threshold from 10% to 15%
- Increased default alarm threshold from 15% to 20%
- Made all parameters configurable without code modification
- Added debug logging option

### Rationale for Increased Thresholds
If your battery bank has batteries with different charge/discharge characteristics (e.g., different internal resistance, age, or chemistry variations), the SOC imbalance will persist or even increase during charging. In such cases, the original 10% warning threshold would trigger constantly. The new 15% warning and 20% alarm thresholds provide protection while avoiding nuisance alarms for batteries that naturally operate at different SOC levels.

To use the old v1.0.0 thresholds, set:
```ini
[ImbalanceThresholds]
imbalance_warning_threshold = 10.0
imbalance_alarm_threshold = 15.0
```

